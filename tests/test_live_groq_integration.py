# tests/test_live_groq_integration.py
"""
Live Groq API Integration Test Suite (Phase 4).
Tests the real, unmocked Groq API across all 5 AI workflows:
1. POST /api/v1/ai/copilot/chat (SRE Copilot chat)
2. POST /api/v1/ai/incidents/{incident_id}/explain (Incident explanation)
3. POST /api/v1/ai/incidents/{incident_id}/rca-explanation (AI Root Cause Analysis)
4. POST /api/v1/ai/servers/{server_id}/predictive-analysis (Predictive capacity forecast)
5. POST /api/v1/ai/incidents/{incident_id}/remediation-plan (Human-in-the-loop remediation)

Skipped automatically if no valid GROQ_API_KEY is configured.
"""

import os
import sys
import uuid
import pytest
from datetime import datetime, timezone

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.core.database import SessionLocal, Base, engine
from app.models.models import (
    Tenant, User, Server, Alert, Incident,
    MLAnomaly, ServiceNode, ServiceDependency, TelemetryRecord, TraceSpan
)
from app.core.security import create_access_token, get_password_hash
from app.ai.groq_client import get_groq_client

client = TestClient(app)

GROQ_AVAILABLE = get_groq_client().is_available()


@pytest.fixture(scope="module")
def live_fixtures():
    if not GROQ_AVAILABLE:
        pytest.skip("Groq API key not configured or is placeholder; skipping live tests.")

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    uid = uuid.uuid4().hex[:8]

    try:
        tenant = Tenant(
            name=f"LiveGroqTenant_{uid}",
            slug=f"live-groq-{uid}",
            plan="Enterprise"
        )
        db.add(tenant)
        db.flush()

        user = User(
            email=f"live_sre_{uid}@observault.io",
            full_name="Live SRE Engineer",
            role="admin",
            tenant_id=tenant.id,
            hashed_password=get_password_hash("SecretPass123!"),
            is_active=True
        )
        db.add(user)
        db.flush()

        server = Server(
            id=str(uuid.uuid4()),
            tenant_id=tenant.id,
            hostname=f"prod-api-worker-{uid}.internal",
            display_name="Production API Worker",
            status="critical",
            last_cpu=94.5,
            last_memory=88.2,
            last_disk=76.0,
            last_seen=datetime.now(timezone.utc)
        )
        db.add(server)
        db.flush()

        incident = Incident(
            id=str(uuid.uuid4()),
            tenant_id=tenant.id,
            incident_code=f"INC-LIVE-{uid[:4].upper()}",
            title="Sustained API Worker CPU Saturation and Elevated Response Time",
            severity="critical",
            status="investigating",
            primary_server_id=server.id,
            possible_cause="Worker CPU breached 90% threshold for > 10 minutes.",
            evidence_summary="Worker CPU breached 90% threshold for > 10 minutes with concurrent thread pool exhaustion.",
            confidence_score=0.92,
            created_at=datetime.now(timezone.utc)
        )
        db.add(incident)
        db.flush()

        alert = Alert(
            id=str(uuid.uuid4()),
            tenant_id=tenant.id,
            server_id=server.id,
            alert_type="high_cpu",
            severity="critical",
            title="CPU Usage > 90%",
            description="Production worker CPU peaked at 94.5%",
            metric_name="cpu_percent",
            observed_value=94.5,
            threshold_value=90.0,
            status="active"
        )
        db.add(alert)
        db.flush()
        incident.alerts.append(alert)

        # Telemetry record
        telemetry = TelemetryRecord(
            id=str(uuid.uuid4()),
            tenant_id=tenant.id,
            server_id=server.id,
            event_id=f"evt-live-{uid}",
            cpu_percent=94.5,
            memory_percent=88.2,
            disk_percent=76.0,
            network_latency_ms=120.4,
            packet_loss_percent=0.2,
            failed_login_count=0,
            service_status="degraded",
            timestamp=datetime.now(timezone.utc)
        )
        db.add(telemetry)

        # Service topology node
        svc = ServiceNode(
            tenant_id=tenant.id,
            name="api-worker-cluster",
            service_type="worker_service"
        )
        db.add(svc)

        db.commit()

        token = create_access_token(user.id, tenant.id, user.role)
        headers = {"Authorization": f"Bearer {token}"}

        yield {
            "tenant": tenant,
            "user": user,
            "server": server,
            "incident": incident,
            "alert": alert,
            "headers": headers
        }

    finally:
        db.close()


@pytest.mark.skipif(not GROQ_AVAILABLE, reason="Live Groq API key required")
def test_live_workflow_1_copilot_chat(live_fixtures):
    """Workflow 1: Test live Copilot chat infrastructure health analysis."""
    headers = live_fixtures["headers"]
    payload = {
        "message": "Analyze cluster health and list any active incidents.",
        "incident_limit": 5,
        "incident_offset": 0
    }
    response = client.post("/api/v1/ai/copilot/chat", json=payload, headers=headers)
    assert response.status_code == 200, f"Copilot chat failed: {response.text}"
    data = response.json()
    assert "answer" in data
    assert len(data["answer"]) > 0
    assert "cites_evidence" in data
    assert "model_used" in data
    print(f"\n[Workflow 1 - Live Copilot]: {data['answer'][:120]}... (Model: {data['model_used']})")


@pytest.mark.skipif(not GROQ_AVAILABLE, reason="Live Groq API key required")
def test_live_workflow_2_incident_explain(live_fixtures):
    """Workflow 2: Test live incident explanation."""
    headers = live_fixtures["headers"]
    incident_id = live_fixtures["incident"].id
    response = client.post(f"/api/v1/ai/incidents/{incident_id}/explain", headers=headers)
    assert response.status_code == 200, f"Incident explain failed: {response.text}"
    data = response.json()
    assert "raw_narrative" in data or "confirmed_facts" in data
    assert data["incident_id"] == incident_id
    assert "model_used" in data
    print(f"\n[Workflow 2 - Live Explain]: {data.get('raw_narrative', '')[:120]}...")


@pytest.mark.skipif(not GROQ_AVAILABLE, reason="Live Groq API key required")
def test_live_workflow_3_ai_rca_explanation(live_fixtures):
    """Workflow 3: Test live AI RCA explanation."""
    headers = live_fixtures["headers"]
    incident_id = live_fixtures["incident"].id
    response = client.post(f"/api/v1/ai/incidents/{incident_id}/rca-explanation", headers=headers)
    assert response.status_code == 200, f"AI RCA failed: {response.text}"
    data = response.json()
    assert "explanation" in data or "raw_narrative" in data
    assert data["incident_id"] == incident_id
    assert "model_used" in data
    print(f"\n[Workflow 3 - Live RCA]: Root Cause Analysis generated successfully.")


@pytest.mark.skipif(not GROQ_AVAILABLE, reason="Live Groq API key required")
def test_live_workflow_4_predictive_analysis(live_fixtures):
    """Workflow 4: Test live AI predictive capacity analysis."""
    headers = live_fixtures["headers"]
    server_id = live_fixtures["server"].id
    response = client.post(f"/api/v1/ai/servers/{server_id}/predictive-analysis", headers=headers)
    assert response.status_code == 200, f"Predictive analysis failed: {response.text}"
    data = response.json()
    assert "trend_interpretation" in data or "raw_narrative" in data
    assert data["server_id"] == server_id
    assert "model_used" in data
    print(f"\n[Workflow 4 - Live Predictive]: Predictive capacity analysis generated.")


@pytest.mark.skipif(not GROQ_AVAILABLE, reason="Live Groq API key required")
def test_live_workflow_5_remediation_plan(live_fixtures):
    """Workflow 5: Test live AI remediation plan with human authorization requirements."""
    headers = live_fixtures["headers"]
    incident_id = live_fixtures["incident"].id
    response = client.post(f"/api/v1/ai/incidents/{incident_id}/remediation-plan", headers=headers)
    assert response.status_code == 200, f"Remediation plan failed: {response.text}"
    data = response.json()
    assert "strategy_overview" in data or "prioritized_steps" in data
    assert data["human_approval_required"] is True
    assert data["automated_execution_allowed"] is False
    assert "model_used" in data
    print(f"\n[Workflow 5 - Live Remediation]: Generated strategy with human approval enforcement.")
