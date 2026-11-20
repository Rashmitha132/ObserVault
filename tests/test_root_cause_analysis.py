# tests/test_root_cause_analysis.py
"""
Test Suite for ObserVault Phase 2D:
Intelligent Root Cause Analysis (RCA), Multi-Signal Correlation,
Temporal Precedence, Dependency-Based Blast Radius, Candidate Ranking,
Resilience to Missing Telemetry, Unrelated Event Rejection, and Tenant Isolation.
"""

import os
import sys
import uuid
import pytest
from datetime import datetime, timezone, timedelta

# Add backend directory to module search path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal, Base, engine
from app.models.models import (
    Tenant, User, Server, Collector, Alert, Incident,
    MLAnomaly, TraceSpan, ServiceNode, ServiceDependency
)
from app.correlation.rca_engine import RootCauseAnalysisEngine
from app.core.security import create_access_token

client = TestClient(app)

@pytest.fixture(scope="module")
def setup_rca_fixtures():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # 1. Tenants
    tenant_a = db.query(Tenant).filter((Tenant.name == "Acme FinTech") | (Tenant.slug == "acme-fintech")).first()
    if not tenant_a:
        tenant_a = Tenant(name="Acme FinTech", slug="acme-fintech", plan="Enterprise")
        db.add(tenant_a)
        db.commit()
        db.refresh(tenant_a)

    tenant_b = db.query(Tenant).filter(Tenant.slug == "biohealth-global").first()
    if not tenant_b:
        tenant_b = Tenant(name="BioHealth Global", slug="biohealth-global", plan="Standard")
        db.add(tenant_b)
        db.commit()
        db.refresh(tenant_b)

    # 2. Users
    user_a = db.query(User).filter((User.tenant_id == tenant_a.id) | (User.email == "admin@acme.com")).first()
    if not user_a:
        from app.core.security import get_password_hash
        user_a = User(
            tenant_id=tenant_a.id,
            email="admin@acme.com",
            hashed_password=get_password_hash("Password123!"),
            full_name="Acme Admin",
            role="admin"
        )
        db.add(user_a)
        db.commit()
        db.refresh(user_a)

    user_b = db.query(User).filter((User.tenant_id == tenant_b.id) | (User.email == "admin@biohealth.com")).first()
    if not user_b:
        from app.core.security import get_password_hash
        user_b = User(
            tenant_id=tenant_b.id,
            email="admin@biohealth.com",
            hashed_password=get_password_hash("Password123!"),
            full_name="BioHealth Admin",
            role="admin"
        )
        db.add(user_b)
        db.commit()
        db.refresh(user_b)

    # 3. Servers for Tenant A
    db_server = db.query(Server).filter(Server.tenant_id == tenant_a.id, Server.hostname == "srv-prod-db-01").first()
    if not db_server:
        db_server = Server(
            tenant_id=tenant_a.id,
            hostname="srv-prod-db-01",
            display_name="Primary Postgres Database Node",
            ip_address="192.168.1.50",
            status="critical"
        )
        db.add(db_server)
        db.commit()
        db.refresh(db_server)

    api_server = db.query(Server).filter(Server.tenant_id == tenant_a.id, Server.hostname == "srv-prod-api-01").first()
    if not api_server:
        api_server = Server(
            tenant_id=tenant_a.id,
            hostname="srv-prod-api-01",
            display_name="API Gateway Host",
            ip_address="192.168.1.10",
            status="warning"
        )
        db.add(api_server)
        db.commit()
        db.refresh(api_server)

    unrelated_server = db.query(Server).filter(Server.tenant_id == tenant_a.id, Server.hostname == "srv-auth-cluster-01").first()
    if not unrelated_server:
        unrelated_server = Server(
            tenant_id=tenant_a.id,
            hostname="srv-auth-cluster-01",
            display_name="Auth SSO Cluster",
            ip_address="192.168.1.80",
            status="healthy"
        )
        db.add(unrelated_server)
        db.commit()
        db.refresh(unrelated_server)

    # 4. Service Topology for Tenant A: api-gateway -> order-service -> postgres-db
    svc_names = ["api-gateway", "order-service", "postgres-db"]
    for s_name in svc_names:
        s_obj = db.query(ServiceNode).filter(ServiceNode.tenant_id == tenant_a.id, ServiceNode.name == s_name).first()
        if not s_obj:
            s_obj = ServiceNode(
                tenant_id=tenant_a.id,
                name=s_name,
                service_type="database" if "db" in s_name else ("api_gateway" if "gateway" in s_name else "app_service"),
                health_status="healthy"
            )
            db.add(s_obj)
    db.commit()

    # Dependencies: api-gateway -> order-service, order-service -> postgres-db
    deps = [
        ("api-gateway", "order-service"),
        ("order-service", "postgres-db")
    ]
    for caller, callee in deps:
        d_obj = db.query(ServiceDependency).filter(
            ServiceDependency.tenant_id == tenant_a.id,
            ServiceDependency.caller_service_name == caller,
            ServiceDependency.callee_service_name == callee
        ).first()
        if not d_obj:
            d_obj = ServiceDependency(
                tenant_id=tenant_a.id,
                caller_service_name=caller,
                callee_service_name=callee,
                call_count=100
            )
            db.add(d_obj)
    db.commit()

    # Capture IDs before closing
    t_a_id = str(user_a.tenant_id)
    t_b_id = str(user_b.tenant_id)
    u_a_id = str(user_a.id)
    u_b_id = str(user_b.id)
    db_srv_id = str(db_server.id)
    api_srv_id = str(api_server.id)
    unrel_srv_id = str(unrelated_server.id)

    db.close()
    return {
        "tenant_a_id": t_a_id,
        "tenant_b_id": t_b_id,
        "user_a_id": u_a_id,
        "user_b_id": u_b_id,
        "db_server_id": db_srv_id,
        "api_server_id": api_srv_id,
        "unrelated_server_id": unrel_srv_id
    }

def test_multi_signal_correlation_and_ranking(setup_rca_fixtures):
    """
    Simulates a cascading microservice failure:
    1. T=0: postgres-db experiences high CPU (96%) and ML Isolation Forest outlier (0.91)
    2. T=+20s: order-service experiences trace failures calling postgres-db
    3. T=+40s: api-gateway experiences 504 gateway timeout
    Verifies RCA engine ranks postgres-db #1 (Primary Hypothesis) based on temporal and topological precedence.
    """
    db = SessionLocal()
    tenant_id = setup_rca_fixtures["tenant_a_id"]
    now = datetime.now(timezone.utc)

    # 1. Create Alerts
    db_alert = Alert(
        tenant_id=tenant_id,
        server_id=setup_rca_fixtures["db_server_id"],
        alert_type="high_cpu",
        severity="critical",
        title="High CPU Saturation on Database",
        description="CPU utilisation reached 96.5% on primary database node.",
        metric_name="cpu_percent",
        observed_value=96.5,
        threshold_value=90.0,
        status="active",
        created_at=now - timedelta(seconds=120)
    )
    api_alert = Alert(
        tenant_id=tenant_id,
        server_id=setup_rca_fixtures["api_server_id"],
        alert_type="high_latency",
        severity="high",
        title="High Request Latency on Gateway",
        description="Request latency rose to 420ms across ingress routes.",
        metric_name="network_latency_ms",
        observed_value=420.0,
        threshold_value=120.0,
        status="active",
        created_at=now - timedelta(seconds=80)
    )
    db.add(db_alert)
    db.add(api_alert)
    db.commit()

    # 2. Create ML Anomaly on DB
    ml_anom = MLAnomaly(
        tenant_id=tenant_id,
        server_id=setup_rca_fixtures["db_server_id"],
        algorithm="isolation_forest",
        metric_name="multivariate_vector",
        observed_value=0.91,
        expected_baseline=0.35,
        deviation=0.56,
        anomaly_score=0.91,
        severity="critical",
        explanation="Multi-metric Isolation Forest outlier in high-dimensional space.",
        created_at=now - timedelta(seconds=115)
    )
    db.add(ml_anom)

    # 3. Create Trace Spans: Trace showing order-service failure calling postgres-db
    uid = uuid.uuid4().hex[:6]
    trace_id = f"trace-rca-cascade-{uid}"
    root_span = TraceSpan(
        tenant_id=tenant_id,
        trace_id=trace_id,
        span_id=f"span-gw-{uid}",
        service_name="api-gateway",
        operation_name="POST /api/checkout",
        start_time=now - timedelta(seconds=85),
        end_time=now - timedelta(seconds=82),
        duration_ms=3000.0,
        status_code="ERROR",
        status_message="504 Gateway Timeout"
    )
    child_span = TraceSpan(
        tenant_id=tenant_id,
        trace_id=trace_id,
        span_id=f"span-order-{uid}",
        parent_span_id=f"span-gw-{uid}",
        service_name="order-service",
        operation_name="processOrder",
        start_time=now - timedelta(seconds=85),
        end_time=now - timedelta(seconds=82),
        duration_ms=2900.0,
        status_code="ERROR",
        status_message="Database query timed out after 2500ms"
    )
    db_span = TraceSpan(
        tenant_id=tenant_id,
        trace_id=trace_id,
        span_id=f"span-db-{uid}",
        parent_span_id=f"span-order-{uid}",
        service_name="postgres-db",
        operation_name="SELECT * FROM orders",
        start_time=now - timedelta(seconds=110),
        end_time=now - timedelta(seconds=107),
        duration_ms=2800.0,
        status_code="ERROR",
        status_message="connection lock acquisition timeout"
    )
    db.add(root_span)
    db.add(child_span)
    db.add(db_span)

    # 4. Create Incident
    incident = Incident(
        tenant_id=tenant_id,
        incident_code=f"INC-RCA-TEST-{uid.upper()}",
        title="Cascading Checkout Failure Across Order Pipeline",
        severity="critical",
        status="open",
        primary_server_id=setup_rca_fixtures["db_server_id"],
        possible_cause="Underlying database lock contention degrading upstream order processing.",
        confidence_score=0.92,
        evidence_summary="Database saturation observed prior to gateway 504 timeouts.",
        created_at=now - timedelta(seconds=70)
    )
    db.add(incident)
    db.flush()
    incident.alerts = [db_alert, api_alert]
    db.commit()
    inc_id = str(incident.id)
    db.close()

    # Run RCA Analysis
    db = SessionLocal()
    analysis = RootCauseAnalysisEngine.analyze_incident(db, tenant_id, inc_id)
    db.close()

    assert "primary_root_cause_hypothesis" in analysis
    primary = analysis["primary_root_cause_hypothesis"]
    assert primary is not None
    # DB server or postgres-db must be ranked #1
    assert "db" in primary["name"].lower() or "postgres" in primary["name"].lower()
    assert primary["is_primary_hypothesis"] is True
    assert primary["rank"] == 1
    assert primary["root_cause_score"] >= 0.70

    # Verify ranked candidates order
    ranked = analysis["ranked_candidates"]
    assert len(ranked) >= 2
    # Verify api-gateway is ranked lower than the root database
    comp_names = [c["name"].lower() for c in ranked]
    db_idx = next(i for i, name in enumerate(comp_names) if "db" in name)
    gw_idx = next((i for i, name in enumerate(comp_names) if "gateway" in name or "api-01" in name), 999)
    assert db_idx < gw_idx

    # Check blast radius
    blast = analysis["blast_radius"]
    assert blast["total_services_impacted"] >= 1
    assert "causal_link_summary" in blast

    # Check suggested investigation steps
    steps = analysis["suggested_investigation_steps"]
    assert len(steps) >= 2
    assert any("pg_stat_activity" in s.get("command_hint", "") or "lock" in s["title"].lower() or "database" in s["title"].lower() for s in steps)

def test_timestamp_ordering_precedence():
    """Verify earlier anomaly timestamps receive higher temporal scores."""
    t0 = datetime(2026, 11, 20, 10, 0, 0, tzinfo=timezone.utc)
    t1 = datetime(2026, 11, 20, 10, 0, 45, tzinfo=timezone.utc)

    component_signals = {
        "comp-early": {
            "name": "comp-early",
            "type": "database",
            "first_seen": t0,
            "alerts": [],
            "ml_anomalies": [],
            "trace_errors": [],
            "network_events": [],
            "security_events": [],
            "signal_categories": {"infrastructure_alert", "trace_error"},
            "max_severity": "critical"
        },
        "comp-late": {
            "name": "comp-late",
            "type": "microservice",
            "first_seen": t1,
            "alerts": [],
            "ml_anomalies": [],
            "trace_errors": [],
            "network_events": [],
            "security_events": [],
            "signal_categories": {"trace_error"},
            "max_severity": "high"
        }
    }

    ranked = RootCauseAnalysisEngine._rank_candidates(
        component_signals=component_signals,
        dependencies=[],
        earliest_time=t0,
        latest_time=t1
    )

    assert ranked[0]["name"] == "comp-early"
    assert ranked[0]["root_cause_score"] > ranked[1]["root_cause_score"]
    assert ranked[0]["rank"] == 1
    assert ranked[1]["rank"] == 2

def test_unrelated_event_rejection_and_simultaneous_incidents(setup_rca_fixtures):
    """
    Verifies that simultaneous incidents on completely independent components
    (e.g. Auth cluster vs Database) do not cross-pollute each other's RCA candidates.
    """
    db = SessionLocal()
    tenant_id = setup_rca_fixtures["tenant_a_id"]
    now = datetime.now(timezone.utc)

    # Incident A on Database
    uid_sim = uuid.uuid4().hex[:6].upper()
    inc_db = Incident(
        tenant_id=tenant_id,
        incident_code=f"INC-RCA-DB-{uid_sim}",
        title="Isolated Database Outage",
        severity="high",
        status="open",
        primary_server_id=setup_rca_fixtures["db_server_id"],
        possible_cause="Single node disk space warning.",
        confidence_score=0.85,
        evidence_summary="Disk utilisation threshold warning on DB.",
        created_at=now
    )
    # Incident B on Auth Cluster
    inc_auth = Incident(
        tenant_id=tenant_id,
        incident_code=f"INC-RCA-AUTH-{uid_sim}",
        title="Isolated Security Alert on Auth SSO",
        severity="high",
        status="open",
        primary_server_id=setup_rca_fixtures["unrelated_server_id"],
        possible_cause="Authentication rate breach.",
        confidence_score=0.88,
        evidence_summary="Multiple failed logins on SSO.",
        created_at=now
    )
    db.add(inc_db)
    db.add(inc_auth)
    db.commit()

    db_inc_id = str(inc_db.id)
    auth_inc_id = str(inc_auth.id)
    db.close()

    db = SessionLocal()
    analysis_db = RootCauseAnalysisEngine.analyze_incident(db, tenant_id, db_inc_id)
    analysis_auth = RootCauseAnalysisEngine.analyze_incident(db, tenant_id, auth_inc_id)
    db.close()

    # DB analysis should have DB as top candidate, not auth cluster
    assert "db" in analysis_db["primary_root_cause_hypothesis"]["name"].lower()
    # Auth analysis should have auth cluster, not DB
    assert "auth" in analysis_auth["primary_root_cause_hypothesis"]["name"].lower()

def test_missing_telemetry_resilience(setup_rca_fixtures):
    """
    Verifies that when traces or ML anomalies are completely missing (e.g. legacy server or trace drops),
    the RCA engine computes sound candidates from surviving signals without throwing exceptions.
    """
    db = SessionLocal()
    tenant_id = setup_rca_fixtures["tenant_a_id"]
    now = datetime.now(timezone.utc)

    bare_incident = Incident(
        tenant_id=tenant_id,
        incident_code=f"INC-RCA-BARE-{uuid.uuid4().hex[:6].upper()}",
        title="Incident with Sparse Telemetry",
        severity="medium",
        status="open",
        primary_server_id=setup_rca_fixtures["api_server_id"],
        possible_cause="Sparse single alert telemetry.",
        confidence_score=0.75,
        evidence_summary="Minimal alert without distributed trace linkage.",
        created_at=now
    )
    db.add(bare_incident)
    db.commit()
    inc_id = str(bare_incident.id)
    db.close()

    db = SessionLocal()
    analysis = RootCauseAnalysisEngine.analyze_incident(db, tenant_id, inc_id)
    db.close()

    assert analysis["incident_id"] == inc_id
    assert analysis["primary_root_cause_hypothesis"] is not None
    assert len(analysis["suggested_investigation_steps"]) >= 1
    assert "disclaimer" in analysis

def test_tenant_isolation_rca(setup_rca_fixtures):
    """
    Verifies Tenant B user cannot access Tenant A's incident RCA.
    """
    tenant_a_id = setup_rca_fixtures["tenant_a_id"]
    user_b_id = setup_rca_fixtures["user_b_id"]
    tenant_b_id = setup_rca_fixtures["tenant_b_id"]

    db = SessionLocal()
    inc_a = db.query(Incident).filter(Incident.tenant_id == tenant_a_id).first()
    inc_a_id = str(inc_a.id)
    db.close()

    # User B requests Incident A
    token_b = create_access_token(subject=user_b_id, tenant_id=tenant_b_id, role="admin")
    resp = client.get(f"/api/v2/rca/incidents/{inc_a_id}", headers={"Authorization": f"Bearer {token_b}"})
    assert resp.status_code == 404

def test_rca_api_endpoints(setup_rca_fixtures):
    """
    Verifies REST API endpoints:
    - GET /api/v2/rca/incidents
    - GET /api/v2/rca/incidents/{incident_id}
    - GET /api/v2/rca/blast-radius/{component_name}
    """
    tenant_a_id = setup_rca_fixtures["tenant_a_id"]
    user_a_id = setup_rca_fixtures["user_a_id"]

    token_a = create_access_token(subject=user_a_id, tenant_id=tenant_a_id, role="admin")
    headers = {"Authorization": f"Bearer {token_a}"}

    # 1. List RCA incidents
    resp_list = client.get("/api/v2/rca/incidents", headers=headers)
    assert resp_list.status_code == 200
    incidents_data = resp_list.json()
    assert len(incidents_data) >= 1
    first_inc = incidents_data[0]
    assert "primary_suspect" in first_inc
    assert "root_cause_confidence" in first_inc

    # 2. Detail RCA incident
    inc_id = first_inc["incident_id"]
    resp_detail = client.get(f"/api/v2/rca/incidents/{inc_id}", headers=headers)
    assert resp_detail.status_code == 200
    detail = resp_detail.json()
    assert detail["incident_id"] == inc_id
    assert "primary_root_cause_hypothesis" in detail
    assert "ranked_candidates" in detail
    assert "incident_timeline" in detail
    assert "blast_radius" in detail
    assert "suggested_investigation_steps" in detail

    # 3. Dedicated Blast Radius endpoint
    resp_blast = client.get("/api/v2/rca/blast-radius/postgres-db", headers=headers)
    assert resp_blast.status_code == 200
    blast_data = resp_blast.json()
    assert blast_data["originating_suspect"] == "postgres-db"
    assert "directly_affected_services" in blast_data
    assert "order-service" in blast_data["directly_affected_services"]

def test_leaf_dependency_without_evidence_is_not_root_cause(setup_rca_fixtures):
    """
    Validates User Review Feedback:
    1. A leaf dependency (e.g. database) must NOT be crowned root cause without actual telemetry evidence.
       If order-service has an unhandled crash/alert while postgres-db is nominal, order-service must be ranked #1.
    2. Diagnostic commands must NOT display raw query text or unstripped URLs.
    3. Score is explicitly labeled as a heuristic root-cause score, not a probability.
    """
    db = SessionLocal()
    tenant_id = setup_rca_fixtures["tenant_a_id"]
    now = datetime.now(timezone.utc)
    uid = uuid.uuid4().hex[:6].upper()

    # 1. Alert strictly on order-service / api host, with ZERO alerts on database
    app_alert = Alert(
        tenant_id=tenant_id,
        server_id=setup_rca_fixtures["api_server_id"],
        alert_type="high_cpu",
        severity="critical",
        title="App Runtime Crash on Order Service",
        description="Unhandled exception in order-service worker thread.",
        metric_name="cpu_percent",
        observed_value=98.0,
        threshold_value=90.0,
        status="active",
        created_at=now - timedelta(seconds=60)
    )
    db.add(app_alert)

    # 2. Trace error strictly on order-service internal operation (DB is completely normal/absent)
    trace_id = f"trace-order-fault-{uid}"
    app_span = TraceSpan(
        tenant_id=tenant_id,
        trace_id=trace_id,
        span_id=f"span-app-{uid}",
        service_name="order-service",
        operation_name="processPaymentToken",
        start_time=now - timedelta(seconds=60),
        end_time=now - timedelta(seconds=58),
        duration_ms=1800.0,
        status_code="ERROR",
        status_message="NullPointerException in payment handler"
    )
    db.add(app_span)

    # 3. Incident
    incident = Incident(
        tenant_id=tenant_id,
        incident_code=f"INC-RCA-APP-{uid}",
        title="Application-Level Fault on Order Processing",
        severity="critical",
        status="open",
        primary_server_id=setup_rca_fixtures["api_server_id"],
        possible_cause="Application worker thread crash.",
        confidence_score=0.88,
        evidence_summary="Order-service threw NullPointerException; database is healthy.",
        created_at=now - timedelta(seconds=55)
    )
    db.add(incident)
    db.flush()
    incident.alerts = [app_alert]
    db.commit()

    inc_id = str(incident.id)
    db.close()

    db = SessionLocal()
    analysis = RootCauseAnalysisEngine.analyze_incident(db, tenant_id, inc_id)
    db.close()

    # Verify order-service is top candidate, NOT postgres-db!
    top = analysis["primary_root_cause_hypothesis"]
    assert "order" in top["name"].lower() or "api" in top["name"].lower()
    assert "postgres" not in top["name"].lower()

    # Verify score labeling (heuristic root-cause score, not probability)
    assert "root_cause_score" in top
    assert "score_label" in top
    assert "Root-Cause Score" in top["score_label"]
    assert "NOT a statistical probability" in top["ranking_rationale"]

    # Verify privacy safeguards on diagnostic commands: ZERO raw SQL query text
    steps = analysis["suggested_investigation_steps"]
    for step in steps:
        cmd = step.get("command_hint", "")
        assert "query," not in cmd
        assert "privacy_safeguard" in step
