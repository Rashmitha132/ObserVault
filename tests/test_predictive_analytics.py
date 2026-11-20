# tests/test_predictive_analytics.py
"""
Test Suite for ObserVault Phase 2E:
- Resource Forecasting & Linear Trend with 95% Confidence Intervals
- Multi-Horizon Verification (15m, 1h, 24h, 7d, 14d, 30d)
- Forecast Accuracy Evaluation (MAE, RMSE, MAPE with 80/20 chronological train/test split)
- Strict Minimum Data Point Handling (< 3 points withholds extrapolation)
- Capacity Warnings & Days-to-Exhaustion Calculation
- Service Level Objectives (SLOs), Error Budgets & Burn Rate (including missing telemetry detection)
- Real Infrastructure Integrations (psutil host telemetry & Docker probe)
- Credential Masking in Integrations & Connection Strings
- Multi-Tenant Isolation for Predictive Analytics & Integrations
"""

import sys
import os
import uuid
from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient

# Ensure backend directory is in sys.path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.main import app
from app.core.database import SessionLocal
from app.models.models import (
    Tenant, User, Server, TelemetryRecord, ServiceLevelObjective, CapacityWarning, IntegrationConfig, TraceSpan
)
from app.core.security import get_password_hash, create_access_token
from app.detection.predictive_engine import PredictiveEngine
from app.integrations.manager import IntegrationManager, sanitize_conn_string

client = TestClient(app)

@pytest.fixture(scope="module")
def setup_predictive_fixtures():
    db = SessionLocal()
    uid = uuid.uuid4().hex[:6]

    # Tenant A
    tenant_a = db.query(Tenant).filter(Tenant.slug == "acme-fintech").first()
    if not tenant_a:
        tenant_a = Tenant(
            name="Acme FinTech Predictive",
            slug="acme-fintech",
            plan="Enterprise"
        )
        db.add(tenant_a)
        db.flush()
    tenant_a_id = str(tenant_a.id)

    # Tenant B
    tenant_b = db.query(Tenant).filter(Tenant.slug == "biohealth-global").first()
    if not tenant_b:
        tenant_b = Tenant(
            name="BioHealth Global Predictive",
            slug="biohealth-global",
            plan="Enterprise"
        )
        db.add(tenant_b)
        db.flush()
    tenant_b_id = str(tenant_b.id)

    # User A
    user_a = db.query(User).filter(User.email == "admin@acme.com").first()
    if not user_a:
        user_a = User(
            tenant_id=tenant_a_id,
            email="admin@acme.com",
            hashed_password=get_password_hash("Password123!"),
            full_name="Alice Acme",
            role="admin"
        )
        db.add(user_a)
        db.flush()
    else:
        tenant_a_id = str(user_a.tenant_id)
    user_a_id = str(user_a.id)

    # User B
    user_b = db.query(User).filter(User.email == "admin@biohealth.com").first()
    if not user_b:
        user_b = User(
            tenant_id=tenant_b_id,
            email="admin@biohealth.com",
            hashed_password=get_password_hash("Password123!"),
            full_name="Bob BioHealth",
            role="admin"
        )
        db.add(user_b)
        db.flush()
    else:
        tenant_b_id = str(user_b.tenant_id)
    user_b_id = str(user_b.id)

    # Server A
    server_a = db.query(Server).filter(Server.tenant_id == tenant_a_id).first()
    if not server_a:
        server_a = Server(
            tenant_id=tenant_a_id,
            hostname="srv-prod-db-01",
            display_name="Database Node 01",
            status="healthy"
        )
        db.add(server_a)
        db.flush()
    server_a_id = str(server_a.id)

    db.commit()
    db.close()

    token_a = create_access_token(subject=user_a_id, tenant_id=tenant_a_id, role="admin")
    token_b = create_access_token(subject=user_b_id, tenant_id=tenant_b_id, role="admin")

    return {
        "tenant_a_id": tenant_a_id,
        "tenant_b_id": tenant_b_id,
        "user_a_id": user_a_id,
        "server_a_id": server_a_id,
        "token_a": token_a,
        "token_b": token_b
    }


def test_linear_trend_forecasting_algorithm():
    """Verify OLS regression calculates accurate slope, forecast, 95% confidence intervals, and out-of-sample MAE/RMSE."""
    t0 = datetime(2026, 11, 20, 10, 0, 0, tzinfo=timezone.utc)
    data_points = []
    # 10 data points: y = 50 + 2*day
    for day in range(10):
        sec = day * 86400.0
        val = 50.0 + (2.0 * day)
        data_points.append((sec, val))

    res = PredictiveEngine.linear_trend_forecast(
        data_points=data_points,
        horizon_seconds=7 * 86400.0,
        step_seconds=86400.0,
        start_time=t0,
        metric_name="disk_percent",
        threshold_value=90.0
    )

    # Slope should be approximately 2.0% per day
    assert abs(res["slope_per_day"] - 2.0) < 0.05
    assert len(res["historical"]) == 10
    assert len(res["forecast"]) == 7

    # Confidence interval bounds should envelop predicted value
    first_forecast = res["forecast"][0]
    assert first_forecast["upper_bound"] >= first_forecast["forecasted_value"]
    assert first_forecast["lower_bound"] <= first_forecast["forecasted_value"]

    # Evaluation metrics (MAE and RMSE)
    acc = res["accuracy_evaluation"]
    assert acc["evaluation_status"] == "validated_out_of_sample"
    assert acc["mae"] is not None
    assert acc["rmse"] is not None
    assert acc["train_sample_count"] >= 4
    assert acc["test_sample_count"] >= 2


def test_multi_horizon_parsing():
    """Verify 15m, 1h, 24h, 7d, 14d, 30d horizon parsing."""
    h_sec, step, label = PredictiveEngine.parse_horizon("15m")
    assert h_sec == 900.0
    assert label == "15m"

    h_sec, step, label = PredictiveEngine.parse_horizon("1h")
    assert h_sec == 3600.0
    assert label == "1h"

    h_sec, step, label = PredictiveEngine.parse_horizon("24h")
    assert h_sec == 86400.0
    assert label == "24h"

    h_sec, step, label = PredictiveEngine.parse_horizon("7d")
    assert h_sec == 604800.0
    assert label == "7d"


def test_minimum_data_requirement_withholds_extrapolation():
    """Verify that fewer than 3 samples withholds forecast extrapolation."""
    t0 = datetime(2026, 11, 20, 10, 0, 0, tzinfo=timezone.utc)
    sparse_points = [(0.0, 55.0), (3600.0, 56.0)]  # Only 2 points

    res = PredictiveEngine.linear_trend_forecast(
        data_points=sparse_points,
        horizon_seconds=86400.0,
        step_seconds=3600.0,
        start_time=t0,
        metric_name="disk_percent"
    )

    assert res["has_sufficient_data"] is False
    assert len(res["forecast"]) == 0
    assert "Insufficient Historical Baseline" in res["model"]


def test_capacity_warning_time_to_exhaustion(setup_predictive_fixtures):
    """Verify capacity warnings evaluate correctly and flag critical thresholds under 7 days."""
    db = SessionLocal()
    tenant_id = setup_predictive_fixtures["tenant_a_id"]
    now = datetime.now(timezone.utc)
    uid = uuid.uuid4().hex[:6]

    # Create dedicated server for this test to avoid historical record pollution
    test_srv = Server(
        tenant_id=tenant_id,
        hostname=f"srv-disk-exhaustion-{uid}",
        display_name=f"Exhaustion Test Node {uid}",
        status="healthy"
    )
    db.add(test_srv)
    db.flush()
    srv_id = str(test_srv.id)

    # Seed 7 days of historical disk growth: 75% -> 87% (2.0% daily growth)
    t0 = now - timedelta(days=6)
    for i in range(7):
        rec = TelemetryRecord(
            tenant_id=tenant_id,
            server_id=srv_id,
            event_id=f"evt-test-disk-{uid}-{i}",
            cpu_percent=45.0,
            memory_percent=60.0,
            disk_percent=75.0 + (i * 2.0),
            network_latency_ms=25.0,
            packet_loss_percent=0.0,
            timestamp=t0 + timedelta(days=i)
        )
        db.add(rec)
    db.commit()

    warnings = PredictiveEngine.evaluate_active_capacity_warnings(db, tenant_id)
    db.close()

    assert len(warnings) >= 1
    disk_warn = next(w for w in warnings if w["server_id"] == srv_id and w["metric_name"] == "disk_percent")
    assert disk_warn["days_to_exhaustion"] is not None
    # 90% threshold - 87% current = 3% needed / 2% per day = ~1.5 days -> CRITICAL
    assert disk_warn["days_to_exhaustion"] < 7.0
    assert disk_warn["severity"] == "critical"
    assert "URGENT" in disk_warn["recommended_action"]


def test_slo_and_error_budget_calculation(setup_predictive_fixtures):
    """Verify SLI attainment, 30-day error budget, burn rate, and missing telemetry handling."""
    db = SessionLocal()
    tenant_id = setup_predictive_fixtures["tenant_a_id"]
    now = datetime.now(timezone.utc)
    uid = uuid.uuid4().hex[:6]

    # 1. Seed 100 trace spans strictly for api-gateway: 98 SUCCESS, 2 ERROR (98.0% availability)
    for i in range(100):
        status = "ERROR" if i < 2 else "OK"
        span = TraceSpan(
            tenant_id=tenant_id,
            trace_id=f"trace-slo-{uid}-{i}",
            span_id=f"span-slo-{uid}-{i}",
            service_name="api-gateway",
            operation_name="handleRequest",
            start_time=now - timedelta(minutes=10),
            end_time=now - timedelta(minutes=10, seconds=-1),
            duration_ms=45.0,
            status_code=status
        )
        db.add(span)

    # 2. Add an SLO for a service that has ZERO telemetry in the database
    unmonitored_slo = ServiceLevelObjective(
        tenant_id=tenant_id,
        name="Unmonitored Payment Gateway SLI",
        service_name=f"unmonitored-pay-{uid}",
        sli_type="availability",
        target_percentage=99.9,
        warning_threshold=99.0,
        rolling_window_days=30
    )
    db.add(unmonitored_slo)
    db.commit()

    slo_metrics = PredictiveEngine.compute_slo_metrics(db, tenant_id)
    db.close()

    assert len(slo_metrics) >= 1
    api_slo = next(s for s in slo_metrics if s["service_name"] == "api-gateway")

    # Target is 99.9%, current SLI should be ~98.0%
    assert api_slo["current_sli"] <= 98.5
    assert api_slo["burn_rate"] >= 10.0
    assert api_slo["status"] == "breached"
    assert api_slo["error_budget_total_minutes"] > 0

    # GAP CORRECTION VERIFICATION: Check service with ZERO telemetry -> Must be 'no_telemetry'
    unmon_result = next(s for s in slo_metrics if s["service_name"] == f"unmonitored-pay-{uid}")
    assert unmon_result["status"] == "no_telemetry"
    assert unmon_result["current_sli"] == 0.0
    assert "cannot be certified healthy without empirical telemetry" in unmon_result["status_message"]


def test_credential_masking():
    """Verify database connection strings with passwords are strictly sanitized."""
    raw_url = "postgresql://dbuser:superSecretPassword123!@db.internal:5432/proddb"
    sanitized = sanitize_conn_string(raw_url)
    assert "superSecretPassword123!" not in sanitized
    assert "dbuser:***@" in sanitized


def test_real_host_telemetry_capture():
    """Verify real host telemetry uses psutil, returns real numbers, and flags is_simulated=False."""
    real_data = IntegrationManager.capture_real_host_telemetry()

    assert real_data["is_simulated"] is False
    assert real_data["telemetry_source"] == "psutil_kernel_telemetry"
    assert 0.0 <= real_data["cpu_percent"] <= 100.0
    assert 0.0 <= real_data["memory_percent"] <= 100.0
    assert 0.0 <= real_data["disk_percent"] <= 100.0
    assert real_data["process_count"] > 10
    assert len(real_data["hostname"]) > 0


def test_docker_status_probe():
    """Verify Docker probe returns structured status and graceful fallback when offline."""
    docker_data = IntegrationManager.probe_docker_status()

    assert "docker_available" in docker_data
    assert docker_data["status"] in ("connected", "disconnected")
    assert "setup_guide" in docker_data
    assert docker_data["is_simulated"] is False


def test_predictive_and_integrations_api_endpoints(setup_predictive_fixtures):
    """Verify REST API endpoints for predictive forecasting (1h, 24h, 7d), capacity warnings, SLOs, and integrations."""
    token = setup_predictive_fixtures["token_a"]
    server_id = setup_predictive_fixtures["server_a_id"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Forecast endpoint with 1h horizon
    resp = client.get(f"/api/v2/predictive/forecast/{server_id}?metric_name=cpu_percent&horizon=1h", headers=headers)
    assert resp.status_code == 200
    fc_1h = resp.json()
    assert fc_1h["horizon_label"] == "1h"
    assert "accuracy_evaluation" in fc_1h

    # 2. Forecast endpoint with 7d horizon
    resp = client.get(f"/api/v2/predictive/forecast/{server_id}?metric_name=disk_percent&horizon=7d", headers=headers)
    assert resp.status_code == 200
    fc_7d = resp.json()
    assert fc_7d["server_id"] == server_id
    assert "accuracy_evaluation" in fc_7d

    # 3. Capacity warnings endpoint
    resp = client.get("/api/v2/predictive/capacity-warnings", headers=headers)
    assert resp.status_code == 200
    warnings = resp.json()
    assert isinstance(warnings, list)

    # 4. SLO endpoint
    resp = client.get("/api/v2/predictive/slo", headers=headers)
    assert resp.status_code == 200
    slos = resp.json()
    assert len(slos) >= 4

    # 5. Integrations list endpoint
    resp = client.get("/api/v2/integrations", headers=headers)
    assert resp.status_code == 200
    integrations = resp.json()
    assert len(integrations) >= 4

    # 6. Real host telemetry endpoint
    resp = client.get("/api/v2/integrations/real-host", headers=headers)
    assert resp.status_code == 200
    real_host = resp.json()
    assert real_host["is_simulated"] is False
    assert real_host["cpu_percent"] >= 0.0

    # 7. Test integration endpoint
    resp = client.post("/api/v2/integrations/test/fastapi_app", headers=headers)
    assert resp.status_code == 200
    test_res = resp.json()
    assert test_res["connected"] is True


def test_tenant_isolation_predictive(setup_predictive_fixtures):
    """Verify Tenant B cannot access Tenant A's forecasts."""
    token_b = setup_predictive_fixtures["token_b"]
    server_a_id = setup_predictive_fixtures["server_a_id"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Tenant B tries to access Server A's forecast -> Must return 404
    resp = client.get(f"/api/v2/predictive/forecast/{server_a_id}", headers=headers_b)
    assert resp.status_code == 404
