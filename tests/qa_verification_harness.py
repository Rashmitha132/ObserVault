import sys
import os
import time
import json
import uuid
import datetime
from datetime import datetime, timezone, timedelta

# Setup paths dynamically
obs_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
backend_path = os.path.join(obs_path, "backend")
sys.path.insert(0, obs_path)
sys.path.insert(0, backend_path)
os.chdir(obs_path)

from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.models.models import (
    Tenant, User, Collector, Server, DeviceEnrollmentToken, DeviceAuditLog, 
    TelemetryRecord, Alert, Incident, Recommendation, CapacityWarning
)
from app.core.security import get_password_hash, create_access_token, hash_token
from app.detection.predictive_engine import PredictiveEngine
from app.detection.anomaly_engine import run_anomaly_detection
from app.correlation.incident_correlator import run_incident_correlation
from app.correlation.rca_engine import RootCauseAnalysisEngine
from app.recommendations.advisor import generate_recommendations
from collector.platform_adapter import WindowsAdapter, LinuxAdapter, get_platform_adapter
from collector.privacy.sanitiser import LocalPrivacySanitiser
from collector.buffer.sqlite_buffer import SQLiteBuffer

client = TestClient(app)
results = {}

print("=================================================================")
print("  OBSERVAULT INDEPENDENT QA ENGINEERING VERIFICATION HARNESS")
print("=================================================================")

# --- MODULE 1: WINDOWS DEVICE ONBOARDING ---
print("\n--- MODULE 1: WINDOWS DEVICE ONBOARDING ---")
m1_results = {}
db = SessionLocal()
try:
    tenant = db.query(Tenant).filter(Tenant.slug == "acme-fintech").first()
    admin_user = db.query(User).filter(User.tenant_id == tenant.id, User.role == "admin").first()
    admin_token = create_access_token(subject=str(admin_user.id), tenant_id=str(tenant.id), role="admin")
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Test 1.1: Register new Windows device
    t0 = time.time()
    r = client.post("/api/v1/collectors/register", headers=headers, json={
        "device_name": "QA-Win11-Host-01", "os_type": "windows", "environment": "staging"
    })
    m1_results["register_device"] = {"status_code": r.status_code, "latency_ms": round((time.time()-t0)*1000, 2), "data": r.json()}
    enroll_token = r.json().get("enrollment_token")
    
    # Test 1.2: Valid Enrollment
    t0 = time.time()
    r_enroll = client.post("/api/v1/collectors/enroll", json={
        "enrollment_token": enroll_token,
        "hostname": "QA-WIN11-TESTBED",
        "os_type": "windows",
        "os_version": "Windows 11 Enterprise (Build 22631)",
        "collector_version": "1.0.0",
        "ip_address": "192.168.10.45",
        "machine_guid": "QA-GUID-9988-7766"
    })
    m1_results["valid_enrollment"] = {"status_code": r_enroll.status_code, "latency_ms": round((time.time()-t0)*1000, 2), "data": r_enroll.json()}
    col_key = r_enroll.json().get("collector_key")
    col_id = r_enroll.json().get("collector_id")

    # Test 1.3: Token Reuse (Replay)
    r_reuse = client.post("/api/v1/collectors/enroll", json={
        "enrollment_token": enroll_token,
        "hostname": "QA-WIN11-REPLAY",
        "os_type": "windows",
        "os_version": "Windows 11 Enterprise",
        "collector_version": "1.0.0",
        "ip_address": "192.168.10.46",
        "machine_guid": "QA-GUID-REPLAY"
    })
    m1_results["token_reuse"] = {"status_code": r_reuse.status_code, "rejected": r_reuse.status_code in [400, 403, 404, 410]}

    # Test 1.4: Invalid Token
    r_invalid = client.post("/api/v1/collectors/enroll", json={
        "enrollment_token": "ov_enroll_invalid_fake_token_12345",
        "hostname": "QA-WIN11-FAKE",
        "os_type": "windows",
        "os_version": "Windows 11",
        "collector_version": "1.0.0",
        "ip_address": "192.168.10.47",
        "machine_guid": "QA-GUID-FAKE"
    })
    m1_results["invalid_token"] = {"status_code": r_invalid.status_code, "rejected": r_invalid.status_code in [400, 401, 403, 404]}

    # Test 1.5: Device Revocation
    r_revoke = client.post(f"/api/v1/collectors/{col_id}/revoke", headers=headers, json={"reason": "QA security audit test"})
    m1_results["revoke_device"] = {"status_code": r_revoke.status_code, "data": r_revoke.json()}

    # Test 1.6: Revoked device attempts heartbeat
    r_hb_revoked = client.post("/api/v1/heartbeat", headers={"X-Collector-Key": col_key}, json={
        "collector_id": col_id, "hostname": "QA-WIN11-TESTBED", "status": "online",
        "version": "1.0.0", "collection_interval": 15, "buffered_records_count": 0, "failed_transmissions_count": 0
    })
    m1_results["revoked_heartbeat_blocked"] = {"status_code": r_hb_revoked.status_code, "blocked": r_hb_revoked.status_code == 403}

    print(f"Module 1 Results: {json.dumps(m1_results, indent=2)}")
finally:
    db.close()

# --- MODULE 2: CONTINUOUS HEARTBEAT & REAL TELEMETRY ---
print("\n--- MODULE 2: CONTINUOUS HEARTBEAT & TELEMETRY ---")
m2_results = {}
db = SessionLocal()
try:
    tenant = db.query(Tenant).filter(Tenant.slug == "acme-fintech").first()
    # Create active collector for Module 2
    r_reg2 = client.post("/api/v1/collectors/register", headers=headers, json={
        "device_name": "QA-Heartbeat-Device", "os_type": "windows", "environment": "production"
    })
    tok2 = r_reg2.json()["enrollment_token"]
    r_en2 = client.post("/api/v1/collectors/enroll", json={
        "enrollment_token": tok2, "hostname": "QA-HB-NODE", "os_type": "windows",
        "os_version": "Windows 11 Pro", "collector_version": "1.0.0", "ip_address": "10.0.1.55", "machine_guid": "GUID-HB-TEST"
    })
    col2_key = r_en2.json()["collector_key"]
    col2_id = r_en2.json()["collector_id"]
    srv2_id = r_en2.json()["server_id"]

    # Test 2.1: Live heartbeat transmission
    t0 = time.time()
    r_hb1 = client.post("/api/v1/heartbeat", headers={"X-Collector-Key": col2_key}, json={
        "collector_id": col2_id, "hostname": "QA-HB-NODE", "status": "online",
        "version": "1.0.0", "collection_interval": 15, "buffered_records_count": 0, "failed_transmissions_count": 0
    })
    m2_results["heartbeat_15s"] = {"status_code": r_hb1.status_code, "latency_ms": round((time.time()-t0)*1000, 2), "data": r_hb1.json()}

    # Test 2.2: Live psutil physical metrics capture (distinguish real vs simulated)
    adapter = WindowsAdapter()
    real_metrics = adapter.get_system_metrics()
    m2_results["real_windows_metrics"] = {
        "is_simulated": real_metrics["is_simulated"],
        "cpu_percent": real_metrics["cpu_percent"],
        "memory_percent": real_metrics["memory_percent"],
        "disk_percent": real_metrics["disk_percent"],
        "is_real_values": (real_metrics["is_simulated"] is False and 0.0 <= real_metrics["cpu_percent"] <= 100.0)
    }

    # Test 2.3: Ingest real telemetry record
    real_event = {
        "event_id": f"evt-qa-{uuid.uuid4().hex[:8]}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "server_id": srv2_id,
        "hostname": "QA-HB-NODE",
        "collector_id": col2_id,
        "collector_version": "1.0.0",
        "cpu_percent": real_metrics["cpu_percent"],
        "memory_percent": real_metrics["memory_percent"],
        "disk_percent": real_metrics["disk_percent"],
        "network_latency_ms": 18.2,
        "packet_loss_percent": 0.0,
        "network_status": "connected",
        "failed_login_count": 0,
        "service_status": "up",
        "is_simulated": False
    }
    telemetry_payload = {
        "batch_id": f"batch-{uuid.uuid4().hex[:8]}",
        "collector_id": col2_id,
        "records": [real_event]
    }
    r_ingest = client.post("/api/v1/telemetry", headers={"X-Collector-Key": col2_key}, json=telemetry_payload)
    m2_results["telemetry_ingestion"] = {"status_code": r_ingest.status_code, "data": r_ingest.json()}

    # Test 2.4: Dynamic Online -> Offline detection
    c_rec = db.query(Collector).filter(Collector.id == col2_id).first()
    # Simulate past heartbeat (> 60s ago)
    c_rec.last_heartbeat = datetime.now(timezone.utc) - timedelta(seconds=120)
    db.commit()
    r_list = client.get("/api/v1/collectors", headers=headers)
    target_c = next((item for item in r_list.json() if item["id"] == col2_id), None)
    m2_results["offline_transition"] = {"status_after_timeout": target_c.get("status") if target_c else None}

    # Recover to online with fresh heartbeat
    client.post("/api/v1/heartbeat", headers={"X-Collector-Key": col2_key}, json={
        "collector_id": col2_id, "hostname": "QA-HB-NODE", "status": "online",
        "version": "1.0.0", "collection_interval": 15, "buffered_records_count": 0, "failed_transmissions_count": 0
    })
    r_list2 = client.get("/api/v1/collectors", headers=headers)
    target_c2 = next((item for item in r_list2.json() if item["id"] == col2_id), None)
    m2_results["online_recovery"] = {"status_after_recovery": target_c2.get("status") if target_c2 else None}

    # Test 2.5: SQLite Buffer enqueue/dequeue (offline survivability)
    test_db_path = os.path.join(obs_path, "collector", f"qa_test_buffer_{uuid.uuid4().hex[:6]}.db")
    buf = SQLiteBuffer(test_db_path)
    buf.enqueue("buf-001", {"event_id": "buf-001", "cpu": 55.0})
    buf.enqueue("buf-002", {"event_id": "buf-002", "cpu": 65.0})
    b_stats = buf.get_stats()
    records = buf.get_pending(limit=10)
    buf.mark_delivered(["buf-001", "buf-002"])
    b_stats_after = buf.get_stats()
    m2_results["sqlite_buffer"] = {
        "pending_before": b_stats["pending"],
        "retrieved_batch_len": len(records),
        "pending_after": b_stats_after["pending"],
        "delivered_after": b_stats_after["delivered"],
        "buffer_survived": (b_stats["pending"] == 2 and b_stats_after["pending"] == 0)
    }

    print(f"Module 2 Results: {json.dumps(m2_results, indent=2)}")
finally:
    db.close()

# --- MODULE 3: LINUX COMPATIBILITY ---
print("\n--- MODULE 3: LINUX COMPATIBILITY ---")
m3_results = {}
linux_adapter = LinuxAdapter()
m3_results["os_name"] = linux_adapter.get_os_name()
m3_results["os_version"] = linux_adapter.get_os_version()
m3_results["hostname"] = linux_adapter.get_hostname()
m3_results["config_path"] = linux_adapter.get_default_config_path()
linux_metrics = linux_adapter.get_system_metrics()
m3_results["metrics"] = linux_metrics
m3_results["schema_compatible_with_windows"] = set(linux_metrics.keys()) == set(real_metrics.keys())
print(f"Module 3 Results: {json.dumps(m3_results, indent=2)}")

# --- MODULE 4: PREDICTIVE ANALYTICS & ANOMALY DETECTION ---
print("\n--- MODULE 4: PREDICTIVE ANALYTICS & ANOMALY DETECTION ---")
m4_results = {}
db = SessionLocal()
try:
    tenant = db.query(Tenant).filter(Tenant.slug == "acme-fintech").first()
    srv = db.query(Server).filter(Server.tenant_id == tenant.id).first()
    col = db.query(Collector).filter(Collector.tenant_id == tenant.id).first()

    # Test linear_trend_forecast across horizons
    now = datetime.now(timezone.utc)
    t0 = now - timedelta(days=7)
    # Seed synthetic points (x_seconds, y_val)
    pts = [(i * 3600.0, 45.0 + (i * 0.2)) for i in range(168)] # 7 days of hourly points
    horizons = [
        ("15m", 900.0, 60.0),
        ("1h", 3600.0, 300.0),
        ("24h", 86400.0, 3600.0),
        ("7d", 604800.0, 43200.0),
        ("14d", 1209600.0, 86400.0),
        ("30d", 2592000.0, 86400.0)
    ]
    horizon_checks = {}
    for label, h_sec, s_sec in horizons:
        res = PredictiveEngine.linear_trend_forecast(
            data_points=pts, horizon_seconds=h_sec, step_seconds=s_sec,
            start_time=t0, metric_name="disk_percent", threshold_value=90.0
        )
        eval_acc = res.get("accuracy_evaluation", {})
        horizon_checks[label] = {
            "forecast_points": len(res.get("forecast", [])),
            "has_sufficient_data": res.get("has_sufficient_data"),
            "mae": eval_acc.get("mae"),
            "rmse": eval_acc.get("rmse"),
            "mape": eval_acc.get("mape_percent"),
            "days_to_threshold": res.get("days_to_threshold")
        }
    m4_results["horizons"] = horizon_checks

    # Insufficient data test (< 3 points)
    res_sparse = PredictiveEngine.linear_trend_forecast(
        data_points=pts[:2], horizon_seconds=3600.0, step_seconds=300.0,
        start_time=t0, metric_name="disk_percent"
    )
    m4_results["insufficient_data"] = {
        "has_sufficient_data": res_sparse.get("has_sufficient_data"),
        "forecast_empty": len(res_sparse.get("forecast", [])) == 0,
        "model": res_sparse.get("model")
    }

    # Capacity warning evaluation
    warnings = PredictiveEngine.evaluate_active_capacity_warnings(db, tenant.id)
    m4_results["capacity_warnings"] = {"active_warnings_count": len(warnings)}

    # Anomaly detection test
    norm_rec = TelemetryRecord(
        tenant_id=tenant.id, collector_id=col.id, server_id=srv.id,
        event_id=f"evt-norm-{uuid.uuid4().hex[:6]}", cpu_percent=35.0, memory_percent=50.0,
        disk_percent=45.0, network_latency_ms=20.0, packet_loss_percent=0.0, is_simulated=True,
        raw_metadata_json="{}"
    )
    alerts_norm = run_anomaly_detection(db, norm_rec, tenant, srv)

    spike_rec = TelemetryRecord(
        tenant_id=tenant.id, collector_id=col.id, server_id=srv.id,
        event_id=f"evt-spike-{uuid.uuid4().hex[:6]}", cpu_percent=98.5, memory_percent=94.0,
        disk_percent=91.0, network_latency_ms=250.0, packet_loss_percent=5.0, is_simulated=True,
        raw_metadata_json="{}"
    )
    alerts_spike = run_anomaly_detection(db, spike_rec, tenant, srv)
    alert_types = [a.alert_type for a in alerts_spike]

    m4_results["anomaly_detection"] = {
        "normal_alerts_count": len(alerts_norm),
        "spike_alerts_count": len(alerts_spike),
        "detected_alert_types": alert_types,
        "false_positive_on_normal": len(alerts_norm) > 0
    }
finally:
    db.close()

print(f"Module 4 Results: {json.dumps(m4_results, indent=2)}")

# --- MODULE 5: LLM ASSISTANT & ADVISORY ---
print("\n--- MODULE 5: LLM ASSISTANT & ADVISORY ---")
m5_results = {}
db = SessionLocal()
try:
    tenant = db.query(Tenant).filter(Tenant.slug == "acme-fintech").first()
    inc = db.query(Incident).filter(Incident.tenant_id == tenant.id).first()
    if inc:
        rca = RootCauseAnalysisEngine.analyze_incident(db, tenant.id, inc.id)
        m5_results["rca_advisory"] = {
            "incident_id": inc.id,
            "has_primary_hypothesis": rca.get("primary_root_cause_hypothesis") is not None,
            "primary_suspect": rca.get("primary_root_cause_hypothesis", {}).get("name"),
            "confidence_percent": rca.get("primary_root_cause_hypothesis", {}).get("confidence_percent"),
            "supporting_evidence_count": len(rca.get("primary_root_cause_hypothesis", {}).get("supporting_evidence", []))
        }
    recs = generate_recommendations(db, tenant)
    m5_results["recommendations"] = {
        "recommendations_count": len(recs),
        "human_approval_enforced": all(r.human_approval_required is True for r in recs) if recs else True
    }
    m5_results["llm_status"] = "PENDING_DEVELOPER_IMPLEMENTATION (Rule-based Advisor & RCA Engine active; conversational LLM endpoint pending)"
finally:
    db.close()
print(f"Module 5 Results: {json.dumps(m5_results, indent=2)}")

# --- MODULE 6: SECURITY TESTING ---
print("\n--- MODULE 6: SECURITY TESTING ---")
m6_results = {}
# 6.1: Unauthorized request (no token)
r_no_auth = client.get("/api/v1/infrastructure")
m6_results["unauthorized_401"] = (r_no_auth.status_code == 401)

# 6.2: Invalid JWT
r_bad_jwt = client.get("/api/v1/infrastructure", headers={"Authorization": "Bearer invalid_signature_token"})
m6_results["invalid_jwt_401"] = (r_bad_jwt.status_code == 401)

# 6.3: Cross-tenant isolation
db = SessionLocal()
try:
    tenant_b = db.query(Tenant).filter(Tenant.slug != "acme-fintech").first()
    if tenant_b:
        user_b = db.query(User).filter(User.tenant_id == tenant_b.id).first()
        token_b = create_access_token(subject=str(user_b.id), tenant_id=str(tenant_b.id), role="admin")
        r_tenant_b = client.get("/api/v1/collectors", headers={"Authorization": f"Bearer {token_b}"})
        tenant_b_col_ids = [c["id"] for c in r_tenant_b.json()]
        tenant_a_cols = db.query(Collector).filter(Collector.tenant_id != tenant_b.id).all()
        leaked = any(c.id in tenant_b_col_ids for c in tenant_a_cols)
        m6_results["cross_tenant_isolation"] = {"leaked": leaked, "tenant_b_col_count": len(tenant_b_col_ids)}
finally:
    db.close()

# 6.4: Privacy Allowlist Sanitization
dirty_event = {
    "event_id": "sec-test-01", "timestamp": now.isoformat(),
    "server_id": "srv-01", "hostname": "host-01", "collector_id": "col-01", "collector_version": "1.0",
    "cpu_percent": 25.0, "memory_percent": 45.0, "disk_percent": 30.0,
    "network_latency_ms": 15.0, "packet_loss_percent": 0.0, "network_status": "connected",
    "failed_login_count": 0, "service_status": "up",
    "plaintext_password": "AdminSuperSecretPassword!",
    "api_key": "sk_live_998877665544332211",
    "jwt_token": "Bearer eyJhbGciOi...",
    "sql_query": "SELECT * FROM users WHERE ssn='123-45-6789'"
}
sanitized, audit = LocalPrivacySanitiser.sanitise_and_transform(dirty_event)
secrets_purged = (
    "plaintext_password" not in sanitized and
    "api_key" not in sanitized and
    "jwt_token" not in sanitized and
    "sql_query" not in sanitized and
    audit["sensitive_data_stripped"] is True
)
m6_results["privacy_sanitization"] = {"secrets_purged": secrets_purged, "rejected_fields": audit["rejected_field_names"]}

# 6.5: Backend Pydantic extra='forbid'
r_forbidden = client.post("/api/v1/telemetry", headers={"X-Collector-Key": "fake_key"}, json={
    **dirty_event, "forbidden_extra_field": "exploit"
})
m6_results["pydantic_extra_forbid"] = {
    "status_code": r_forbidden.status_code,
    "rejected": r_forbidden.status_code == 422
}

# 6.6: SQL Injection resistance
r_sqli = client.get("/api/v1/incidents?status_filter=' OR '1'='1", headers=headers)
m6_results["sqli_protection"] = {"status_code": r_sqli.status_code, "safe": r_sqli.status_code in [200, 422, 400]}

print(f"Module 6 Results: {json.dumps(m6_results, indent=2)}")

# --- MODULE 7: PERFORMANCE & REGRESSION TESTING ---
print("\n--- MODULE 7: PERFORMANCE & REGRESSION TESTING ---")
m7_results = {}

# 7.1: Concurrency benchmark: 50 telemetry requests
t_start = time.time()
latencies = []
for i in range(50):
    t_req = time.time()
    r = client.post("/api/v1/telemetry", headers={"X-Collector-Key": col2_key}, json={
        "batch_id": f"perf-batch-{i}",
        "collector_id": col2_id,
        "records": [{
            "event_id": f"perf-{uuid.uuid4().hex[:6]}-{i}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "server_id": srv2_id,
            "hostname": "QA-HB-NODE",
            "collector_id": col2_id,
            "collector_version": "1.0.0",
            "cpu_percent": 40.0 + (i % 20),
            "memory_percent": 60.0,
            "disk_percent": 50.0,
            "network_latency_ms": 15.0,
            "packet_loss_percent": 0.0,
            "network_status": "connected",
            "failed_login_count": 0,
            "service_status": "up",
            "is_simulated": True
        }]
    })
    latencies.append((time.time() - t_req) * 1000)

total_duration = time.time() - t_start
m7_results["load_test"] = {
    "total_requests": 50,
    "total_duration_sec": round(total_duration, 2),
    "requests_per_sec": round(50 / total_duration, 1),
    "avg_latency_ms": round(sum(latencies) / len(latencies), 2),
    "min_latency_ms": round(min(latencies), 2),
    "max_latency_ms": round(max(latencies), 2),
    "p95_latency_ms": round(sorted(latencies)[int(len(latencies)*0.95)], 2)
}

# 7.2: API Latency across core endpoints
endpoints = [
    ("/api/v1/dashboard/summary", "GET"),
    ("/api/v1/infrastructure", "GET"),
    ("/api/v1/alerts", "GET"),
    ("/api/v1/incidents", "GET"),
    ("/api/v1/collectors", "GET"),
    ("/api/v2/predictive/capacity-warnings", "GET")
]
api_latencies = {}
for ep, method in endpoints:
    t0 = time.time()
    resp = client.get(ep, headers=headers)
    api_latencies[ep] = {"status_code": resp.status_code, "latency_ms": round((time.time() - t0)*1000, 2)}
m7_results["api_latencies"] = api_latencies

print(f"Module 7 Results: {json.dumps(m7_results, indent=2)}")
print("\n=================================================================")
print("  QA HARNESS EXECUTION COMPLETE - ALL DATA CAPTURED")
print("=================================================================")
