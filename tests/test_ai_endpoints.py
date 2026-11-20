# tests/test_ai_endpoints.py
"""
ObserVault AI Intelligence API Test Suite (Phase 3).
Validates:
1. Authentication requirement (401 on missing or invalid JWT).
2. Tenant isolation (404 on cross-tenant incident or server access).
3. Missing Groq API key handling (503 Service Unavailable).
4. Incident explanation endpoint (/api/v1/ai/incidents/{id}/explain).
5. Root cause explanation endpoint (/api/v1/ai/incidents/{id}/rca).
6. Predictive analysis endpoint (/api/v1/ai/servers/{id}/predictive-analysis).
7. SRE Copilot chat endpoint (/api/v1/ai/copilot/chat).
8. Remediation plan endpoint (/api/v1/ai/incidents/{id}/remediation-plan).
9. Groq timeout (504) and rate-limiting (429) mapping.
10. Human authorization enforcement on remediation (no automated execution).
"""

import os
import sys
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch, MagicMock
import pytest

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal, Base, engine
from app.models.models import (
    Tenant, User, Server, Collector, Alert, Incident,
    MLAnomaly, ServiceNode, ServiceDependency, TelemetryRecord, TraceSpan
)
from app.core.security import create_access_token, get_password_hash
from app.ai.groq_client import (
    GroqCompletionResult,
    GroqAuthenticationError,
    GroqRateLimitError,
    GroqTimeoutError
)

client = TestClient(app)


@pytest.fixture(scope="module")
def setup_ai_test_fixtures():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    uid = uuid.uuid4().hex[:8]

    try:
        # Tenant A (Primary)
        tenant_a = Tenant(name=f"Alpha Corp {uid}", slug=f"alpha-corp-{uid}", plan="Enterprise")
        db.add(tenant_a)
        db.flush()

        user_a = User(
            email=f"sre@{uid}.alpha.io",
            full_name="Alpha SRE Lead",
            role="admin",
            tenant_id=tenant_a.id,
            hashed_password=get_password_hash("AlphaPass2026!"),
            is_active=True
        )
        db.add(user_a)
        db.flush()

        server_a = Server(
            id=str(uuid.uuid4()),
            tenant_id=tenant_a.id,
            hostname=f"db-primary-{uid}.internal",
            display_name="Database Primary Cluster",
            status="degraded"
        )
        db.add(server_a)
        db.flush()

        # Telemetry record for Server A
        telem_a = TelemetryRecord(
            id=str(uuid.uuid4()),
            tenant_id=tenant_a.id,
            server_id=server_a.id,
            event_id=f"evt-{uid}-001",
            cpu_percent=88.5,
            memory_percent=92.1,
            disk_percent=89.4,
            network_latency_ms=45.2,
            packet_loss_percent=0.1,
            failed_login_count=0,
            is_simulated=False
        )
        db.add(telem_a)
        db.flush()

        incident_a = Incident(
            id=str(uuid.uuid4()),
            tenant_id=tenant_a.id,
            incident_code=f"INC-{uid.upper()[:4]}",
            title="Database Connection Pool Starvation & WAL Saturation",
            severity="critical",
            status="active",
            confidence_score=0.91,
            possible_cause=f"WAL lock contention on {server_a.hostname}",
            evidence_summary="Cascading timeouts across downstream API gateway callers."
        )
        db.add(incident_a)
        db.flush()

        alert_a = Alert(
            id=str(uuid.uuid4()),
            tenant_id=tenant_a.id,
            server_id=server_a.id,
            alert_type="high_disk",
            severity="critical",
            title="Disk saturation > 85%",
            description="WAL volume approaching physical limit.",
            metric_name="disk_percent",
            observed_value=89.4,
            threshold_value=85.0,
            status="active"
        )
        db.add(alert_a)
        db.flush()
        incident_a.alerts.append(alert_a)

        # Service Nodes & Dependencies for RCA
        svc_db = ServiceNode(tenant_id=tenant_a.id, name="postgres-core", service_type="database")
        svc_api = ServiceNode(tenant_id=tenant_a.id, name="api-gateway", service_type="api_gateway")
        db.add_all([svc_db, svc_api])
        db.flush()

        dep = ServiceDependency(tenant_id=tenant_a.id, caller_service_name="api-gateway", callee_service_name="postgres-core")
        db.add(dep)

        # Trace spans for Tenant A (including error span to test copilot context building)
        span_a = TraceSpan(
            id=str(uuid.uuid4()),
            tenant_id=tenant_a.id,
            trace_id=f"trc-{uid}",
            span_id=f"spn-{uid}",
            service_name="postgres-core",
            operation_name="EXECUTE sql.query",
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc),
            duration_ms=620.0,
            status_code="ERROR",
            status_message="Lock wait timeout exceeded"
        )
        db.add(span_a)

        # Tenant B (Adversary / Cross-Tenant)
        tenant_b = Tenant(name=f"Beta Corp {uid}", slug=f"beta-corp-{uid}", plan="Standard")
        db.add(tenant_b)
        db.flush()

        user_b = User(
            email=f"adversary@{uid}.beta.io",
            full_name="Beta User",
            role="operator",
            tenant_id=tenant_b.id,
            hashed_password=get_password_hash("BetaPass2026!"),
            is_active=True
        )
        db.add(user_b)
        db.flush()

        server_b = Server(
            id=str(uuid.uuid4()),
            tenant_id=tenant_b.id,
            hostname=f"beta-host-{uid}.internal",
            display_name="Beta Host",
            status="healthy"
        )
        db.add(server_b)
        db.commit()

        token_a = create_access_token(user_a.id, tenant_a.id, user_a.role)
        token_b = create_access_token(user_b.id, tenant_b.id, user_b.role)

        data = {
            "token_a": token_a,
            "token_b": token_b,
            "tenant_a_id": tenant_a.id,
            "tenant_b_id": tenant_b.id,
            "incident_a_id": incident_a.id,
            "server_a_id": server_a.id,
            "server_b_id": server_b.id
        }
    finally:
        db.close()

    yield data


# ==============================================================================
# 1. AUTHENTICATION TESTS
# ==============================================================================

def test_ai_endpoints_require_authentication(setup_ai_test_fixtures):
    """Verify that all AI endpoints reject requests without a valid Bearer token."""
    inc_id = setup_ai_test_fixtures["incident_a_id"]
    srv_id = setup_ai_test_fixtures["server_a_id"]

    endpoints = [
        f"/api/v1/ai/incidents/{inc_id}/explain",
        f"/api/v1/ai/incidents/{inc_id}/rca",
        f"/api/v1/ai/servers/{srv_id}/predictive-analysis",
        "/api/v1/ai/copilot/chat",
        f"/api/v1/ai/incidents/{inc_id}/remediation-plan"
    ]

    for ep in endpoints:
        res = client.post(ep, json={"message": "ping"} if "copilot" in ep else {})
        assert res.status_code == 401, f"Endpoint {ep} allowed unauthenticated access"


# ==============================================================================
# 2. TENANT ISOLATION TESTS
# ==============================================================================

def test_cross_tenant_access_blocked(setup_ai_test_fixtures):
    """Verify Tenant B cannot trigger AI explanations for Tenant A's incidents or servers."""
    token_b = setup_ai_test_fixtures["token_b"]
    inc_a_id = setup_ai_test_fixtures["incident_a_id"]
    srv_a_id = setup_ai_test_fixtures["server_a_id"]
    headers = {"Authorization": f"Bearer {token_b}"}

    # Tenant B tries to explain Tenant A's incident
    res = client.post(f"/api/v1/ai/incidents/{inc_a_id}/explain", headers=headers)
    assert res.status_code == 404

    # Tenant B tries to run AI RCA on Tenant A's incident
    res = client.post(f"/api/v1/ai/incidents/{inc_a_id}/rca", headers=headers)
    assert res.status_code == 404

    # Tenant B tries to run AI predictive analysis on Tenant A's server
    res = client.post(f"/api/v1/ai/servers/{srv_a_id}/predictive-analysis", headers=headers)
    assert res.status_code == 404

    # Tenant B tries to generate remediation plan for Tenant A's incident
    res = client.post(f"/api/v1/ai/incidents/{inc_a_id}/remediation-plan", headers=headers)
    assert res.status_code == 404


def test_invalid_resource_ids(setup_ai_test_fixtures):
    """Verify 404 when querying non-existent UUIDs."""
    token_a = setup_ai_test_fixtures["token_a"]
    headers = {"Authorization": f"Bearer {token_a}"}
    fake_id = str(uuid.uuid4())

    res = client.post(f"/api/v1/ai/incidents/{fake_id}/explain", headers=headers)
    assert res.status_code == 404


# ==============================================================================
# 3. SUCCESSFUL MOCKED AI ENDPOINTS
# ==============================================================================

def test_explain_incident_success(setup_ai_test_fixtures):
    """Verify /api/v1/ai/incidents/{id}/explain returns structured grounded explanation."""
    token_a = setup_ai_test_fixtures["token_a"]
    inc_id = setup_ai_test_fixtures["incident_a_id"]
    headers = {"Authorization": f"Bearer {token_a}"}

    mock_text = """### 1. CONFIRMED FACTS
- Disk utilization reached 89.4% exceeding the 85.0% threshold.
- Alert high_disk active on Database Primary Cluster.

### 2. CAUSAL HYPOTHESIS
- WAL archiving congestion is the primary suspect for disk space saturation.

### 3. IMPACT ASSESSMENT
- Downstream API gateway requests are stalling due to connection backpressure.

### 4. RECOMMENDED NEXT STEPS
- Check PostgreSQL pg_stat_activity for long-running idle transactions.
- Inspect disk write throughput using iostat."""

    mock_result = GroqCompletionResult(
        content=mock_text,
        model="openai/gpt-oss-120b",
        prompt_tokens=250,
        completion_tokens=150,
        total_tokens=400,
        latency_ms=145.2
    )

    with patch("app.api.ai.get_groq_client") as mock_get_client:
        mock_instance = MagicMock()
        mock_instance.chat_completion = AsyncMock(return_value=mock_result)
        mock_get_client.return_value = mock_instance

        res = client.post(f"/api/v1/ai/incidents/{inc_id}/explain", headers=headers)
        assert res.status_code == 200
        body = res.json()

        assert body["incident_id"] == inc_id
        assert body["model_used"] == "openai/gpt-oss-120b"
        assert len(body["confirmed_facts"]) >= 1
        assert len(body["causal_hypotheses"]) >= 1
        assert len(body["investigation_suggestions"]) >= 1
        assert "CONFIRMED FACTS" in body["raw_narrative"]
        assert body["tokens_used"] == 400
        assert body["latency_ms"] == 145.2


def test_rca_explanation_success(setup_ai_test_fixtures):
    """Verify /api/v1/ai/incidents/{id}/rca interprets multi-signal causal ranking."""
    token_a = setup_ai_test_fixtures["token_a"]
    inc_id = setup_ai_test_fixtures["incident_a_id"]
    headers = {"Authorization": f"Bearer {token_a}"}

    mock_text = """### 1. PRIMARY CAUSAL HYPOTHESIS
postgres-core is identified with a 91% heuristic root-cause score based on temporal sequence.

### 2. EVIDENCE CHRONOLOGY
Disk saturation preceded gateway caller timeouts by 45 seconds.

### 3. ALTERNATIVE HYPOTHESES EVALUATED
api-gateway was evaluated but ruled out as an effect rather than cause."""

    mock_result = GroqCompletionResult(
        content=mock_text,
        model="openai/gpt-oss-120b",
        prompt_tokens=300,
        completion_tokens=120,
        total_tokens=420,
        latency_ms=132.0
    )

    with patch("app.api.ai.get_groq_client") as mock_get_client:
        mock_instance = MagicMock()
        mock_instance.chat_completion = AsyncMock(return_value=mock_result)
        mock_get_client.return_value = mock_instance

        res = client.post(f"/api/v1/ai/incidents/{inc_id}/rca", headers=headers)
        assert res.status_code == 200
        body = res.json()

        assert body["incident_id"] == inc_id
        assert body["score_type"] == "heuristic_ranking_score"
        assert body["primary_root_cause"] is not None
        assert isinstance(body["root_cause_score"], float)
        assert len(body["evidence_limitations"]) >= 1


def test_predictive_analysis_success(setup_ai_test_fixtures):
    """Verify /api/v1/ai/servers/{id}/predictive-analysis interprets capacity trajectory."""
    token_a = setup_ai_test_fixtures["token_a"]
    srv_id = setup_ai_test_fixtures["server_a_id"]
    headers = {"Authorization": f"Bearer {token_a}"}

    mock_text = """### 1. HISTORICAL BASELINE & CURRENT STATUS
Disk utilization is at 89.4% with positive velocity.

### 2. PROJECTED VELOCITY & THRESHOLD BREACH TIMELINE
At current write rates, the 90% threshold will be breached within 4.2 days.

### 3. CONFIDENCE BOUNDS & UNCERTAINTY
95% confidence intervals indicate breach between 3.8 and 4.9 days."""

    mock_result = GroqCompletionResult(
        content=mock_text,
        model="openai/gpt-oss-120b",
        prompt_tokens=220,
        completion_tokens=140,
        total_tokens=360,
        latency_ms=120.5
    )

    with patch("app.api.ai.get_groq_client") as mock_get_client:
        mock_instance = MagicMock()
        mock_instance.chat_completion = AsyncMock(return_value=mock_result)
        mock_get_client.return_value = mock_instance

        res = client.post(
            f"/api/v1/ai/servers/{srv_id}/predictive-analysis",
            headers=headers,
            json={"metric_name": "disk_percent", "horizon": "7d"}
        )
        if res.status_code != 200:
            print("PREDICTIVE ERROR:", res.status_code, res.text)
        assert res.status_code == 200
        body = res.json()

        assert body["server_id"] == srv_id
        assert body["metric_name"] == "disk_percent"
        assert body["horizon"] == "7d"
        assert isinstance(body["current_value"], float) and body["current_value"] > 0
        assert len(body["capacity_risks"]) >= 1
        assert "95%" in body["confidence_assessment"]


def test_copilot_chat_success(setup_ai_test_fixtures):
    """Verify /api/v1/ai/copilot/chat answers queries grounded in tenant telemetry."""
    token_a = setup_ai_test_fixtures["token_a"]
    headers = {"Authorization": f"Bearer {token_a}"}

    mock_text = "Database Primary Cluster (db-primary) is experiencing 89.4% disk saturation tied to active incident INC."

    mock_result = GroqCompletionResult(
        content=mock_text,
        model="openai/gpt-oss-120b",
        prompt_tokens=180,
        completion_tokens=60,
        total_tokens=240,
        latency_ms=95.0
    )

    with patch("app.api.ai.get_groq_client") as mock_get_client:
        mock_instance = MagicMock()
        mock_instance.chat_completion = AsyncMock(return_value=mock_result)
        mock_get_client.return_value = mock_instance

        # Test valid query
        res = client.post(
            "/api/v1/ai/copilot/chat",
            headers=headers,
            json={"message": "What is the health of our database nodes?"}
        )
        if res.status_code != 200:
            print("COPILOT ERROR:", res.status_code, res.text)
        assert res.status_code == 200
        body = res.json()

        assert "Database Primary Cluster" in body["answer"]
        assert body["telemetry_status"] == "AVAILABLE"

        # Verify Issue 2: Cites evidence contains clean domain badges and NO raw UUID dumps
        cites = body.get("cites_evidence", [])
        assert isinstance(cites, list)
        assert any("Cluster Telemetry" in c for c in cites)
        assert not any("Incident ID:" in c for c in cites)  # No raw UUID dumps!
        assert not any("Incident: INC-" in c for c in cites)  # Clean high-level domain labels instead of code dumps

        # Test empty query rejected
        bad_res = client.post(
            "/api/v1/ai/copilot/chat",
            headers=headers,
            json={"message": "   "}
        )
        assert bad_res.status_code == 400


def test_remediation_plan_requires_human_approval(setup_ai_test_fixtures):
    """Verify /api/v1/ai/incidents/{id}/remediation-plan enforces human approval."""
    token_a = setup_ai_test_fixtures["token_a"]
    inc_id = setup_ai_test_fixtures["incident_a_id"]
    headers = {"Authorization": f"Bearer {token_a}"}

    mock_text = """### 1. REMEDIATION STRATEGY OVERVIEW
Target WAL log clearing on postgres-core.

### 2. PRIORITIZED ACTION STEPS (HUMAN APPROVAL REQUIRED)
1. Check IOPS latency (LOW risk).
2. Purge unindexed WAL archives (MEDIUM risk)."""

    mock_result = GroqCompletionResult(
        content=mock_text,
        model="openai/gpt-oss-120b",
        prompt_tokens=280,
        completion_tokens=90,
        total_tokens=370,
        latency_ms=110.0
    )

    with patch("app.api.ai.get_groq_client") as mock_get_client:
        mock_instance = MagicMock()
        mock_instance.chat_completion = AsyncMock(return_value=mock_result)
        mock_get_client.return_value = mock_instance

        res = client.post(f"/api/v1/ai/incidents/{inc_id}/remediation-plan", headers=headers)
        assert res.status_code == 200
        body = res.json()

        # Strict safety requirements
        assert body["human_approval_required"] is True
        assert body["automated_execution_allowed"] is False
        assert len(body["prioritized_steps"]) >= 1

        for step in body["prioritized_steps"]:
            assert step["requires_human_approval"] is True
            assert step["risk_level"] in ("low", "medium", "high")
            assert step["rollback_procedure"] is not None


# ==============================================================================
# 4. ERROR MAPPING TESTS (KEY MISSING, RATE LIMIT, TIMEOUT)
# ==============================================================================

def test_missing_groq_api_key_returns_503(setup_ai_test_fixtures):
    """Verify missing Groq API key returns clean 503 error."""
    token_a = setup_ai_test_fixtures["token_a"]
    inc_id = setup_ai_test_fixtures["incident_a_id"]
    headers = {"Authorization": f"Bearer {token_a}"}

    with patch("app.api.ai.get_groq_client") as mock_get_client:
        mock_instance = MagicMock()
        mock_instance.chat_completion = AsyncMock(
            side_effect=GroqAuthenticationError("GROQ_API_KEY is not configured or is a placeholder.")
        )
        mock_get_client.return_value = mock_instance

        res = client.post(f"/api/v1/ai/incidents/{inc_id}/explain", headers=headers)
        assert res.status_code == 503
        assert "GROQ_API_KEY" in res.json()["detail"]


def test_groq_rate_limit_returns_429(setup_ai_test_fixtures):
    """Verify Groq rate limit returns 429 Too Many Requests."""
    token_a = setup_ai_test_fixtures["token_a"]
    inc_id = setup_ai_test_fixtures["incident_a_id"]
    headers = {"Authorization": f"Bearer {token_a}"}

    with patch("app.api.ai.get_groq_client") as mock_get_client:
        mock_instance = MagicMock()
        mock_instance.chat_completion = AsyncMock(
            side_effect=GroqRateLimitError("Rate limit reached: 30 RPM.")
        )
        mock_get_client.return_value = mock_instance

        res = client.post(f"/api/v1/ai/incidents/{inc_id}/rca", headers=headers)
        assert res.status_code == 429
        assert "rate limit" in res.json()["detail"].lower()


def test_groq_timeout_returns_504(setup_ai_test_fixtures):
    """Verify Groq timeout returns 504 Gateway Timeout."""
    token_a = setup_ai_test_fixtures["token_a"]
    inc_id = setup_ai_test_fixtures["incident_a_id"]
    headers = {"Authorization": f"Bearer {token_a}"}

    with patch("app.api.ai.get_groq_client") as mock_get_client:
        mock_instance = MagicMock()
        mock_instance.chat_completion = AsyncMock(
            side_effect=GroqTimeoutError("Inference timed out after 15.0 seconds.")
        )
        mock_get_client.return_value = mock_instance

        res = client.post(f"/api/v1/ai/incidents/{inc_id}/explain", headers=headers)
        assert res.status_code == 504
        assert "timed out" in res.json()["detail"].lower()
