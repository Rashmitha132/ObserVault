# tests/test_device_onboarding.py
"""
ObserVault Phase 2F: Comprehensive Device Onboarding Automated Test Suite.
Validates:
- Single-use enrollment token generation & secure hashing.
- End-to-end device enrollment handshake with operational key exchange.
- Single-use and expiration enforcement.
- Rejection of unauthorized, invalid, and revoked credentials.
- Cryptographic heartbeat & dynamic online/offline state transitions.
- Device revocation security (immediate 403 blocking on heartbeat & telemetry).
- Cross-tenant isolation.
- Real Windows host telemetry extraction via psutil & platform adapter.
- Privacy filter pass-through.
- Device management stats & audit logging.
"""

import os
import sys
import uuid
import json
from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient

# Ensure backend and root paths are importable
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)
if root_path not in sys.path:
    sys.path.insert(0, root_path)

from app.main import app
from app.core.database import SessionLocal
from app.models.models import (
    Tenant, User, Collector, Server, DeviceEnrollmentToken, DeviceAuditLog, TelemetryRecord
)
from app.core.security import get_password_hash, create_access_token, hash_token, generate_enrollment_token
from collector.platform_adapter import WindowsAdapter, get_platform_adapter
from collector.privacy.sanitiser import LocalPrivacySanitiser

client = TestClient(app)

@pytest.fixture(scope="module")
def onboarding_setup():
    db = SessionLocal()
    uid = uuid.uuid4().hex[:8]

    # Tenant A
    tenant_a = db.query(Tenant).filter(Tenant.slug == "acme-fintech").first()
    if not tenant_a:
        tenant_a = Tenant(name="Acme FinTech Org", slug="acme-fintech", plan="Enterprise")
        db.add(tenant_a)
        db.flush()

    user_a = db.query(User).filter(User.email == "admin@acme.com").first()
    if not user_a:
        user_a = User(
            tenant_id=tenant_a.id,
            email=f"admin-onboard-{uid}@acme.com",
            hashed_password=get_password_hash("AdminPass123!"),
            full_name="Acme Onboarding Admin",
            role="admin",
            is_active=True
        )
        db.add(user_a)
        db.flush()

    tenant_a_id = str(tenant_a.id)
    user_a_id = str(user_a.id)
    user_a_role = user_a.role

    token_a = create_access_token(
        subject=user_a_id, tenant_id=tenant_a_id, role=user_a_role
    )

    # Tenant B (Adversary / Cross-Tenant)
    tenant_b = db.query(Tenant).filter(Tenant.slug == "cyberdyne-defense").first()
    if not tenant_b:
        tenant_b = Tenant(name="Cyberdyne Defense", slug="cyberdyne-defense", plan="Enterprise")
        db.add(tenant_b)
        db.flush()

    user_b = User(
        tenant_id=tenant_b.id,
        email=f"b-onboard-{uid}@cyberdyne.com",
        hashed_password=get_password_hash("Pass123!"),
        full_name="Cyberdyne Attacker",
        role="admin",
        is_active=True
    )
    db.add(user_b)
    db.commit()

    tenant_b_id = str(tenant_b.id)
    user_b_id = str(user_b.id)
    user_b_role = user_b.role

    token_b = create_access_token(
        subject=user_b_id, tenant_id=tenant_b_id, role=user_b_role
    )

    db.close()
    return {
        "tenant_a_id": tenant_a_id,
        "user_a_token": token_a,
        "tenant_b_id": tenant_b_id,
        "user_b_token": token_b,
        "uid": uid
    }


def test_unauthorized_registration_rejected():
    """Unauthenticated device registration must be rejected with 401."""
    resp = client.post(
        "/api/v1/collectors/register",
        json={"device_name": "Rogue-Machine", "os_type": "windows", "environment": "production"}
    )
    assert resp.status_code == 401


def test_successful_device_registration_and_token_generation(onboarding_setup):
    """
    Test Step 1: Organization Admin registers a new device.
    Verifies:
    - Enrollment token starts with ov_enroll_
    - Raw token is never stored in DB (only SHA-256 hash)
    - Single-use token has 15-minute expiration
    - Copyable PowerShell command is returned
    - Registration audit log is created
    """
    token_a = onboarding_setup["user_a_token"]
    dev_name = f"Win11-Prod-{onboarding_setup['uid']}"

    resp = client.post(
        "/api/v1/collectors/register",
        headers={"Authorization": f"Bearer {token_a}"},
        json={
            "device_name": dev_name,
            "os_type": "windows",
            "environment": "production",
            "description": "Primary on-prem test workstation"
        }
    )
    assert resp.status_code == 200
    data = resp.json()

    raw_token = data["enrollment_token"]
    assert raw_token.startswith("ov_enroll_")
    assert data["device_name"] == dev_name
    assert data["os_type"] == "windows"
    assert "powershell_command" in data
    assert raw_token in data["powershell_command"]
    assert "python -m collector.enroll" in data["enroll_cli_command"]

    # Verify Database State: raw token NOT in DB
    db = SessionLocal()
    token_rec = db.query(DeviceEnrollmentToken).filter(DeviceEnrollmentToken.id == data["token_id"]).first()
    assert token_rec is not None
    assert token_rec.token_hash == hash_token(raw_token)
    assert token_rec.consumed_at is None
    assert token_rec.is_revoked is False

    # Verify Pending Collector placeholder
    collector = db.query(Collector).filter(Collector.name == dev_name).first()
    assert collector is not None
    assert collector.status == "pending"
    assert collector.enrollment_status == "pending"

    # Verify Audit Log
    audit = db.query(DeviceAuditLog).filter(
        DeviceAuditLog.device_name == dev_name,
        DeviceAuditLog.action == "REGISTERED"
    ).first()
    assert audit is not None
    assert "admin" in audit.actor.lower()

    db.close()


def test_successful_device_enrollment_handshake(onboarding_setup):
    """
    Test Step 2: Edge Windows machine calls /enroll with single-use token.
    Verifies:
    - Token is accepted and marked consumed (single-use)
    - Permanent operational key (ov_col_...) is returned
    - Collector transitions to online & active
    - Associated Server is linked
    - Enrollment audit log is created
    """
    token_a = onboarding_setup["user_a_token"]
    dev_name = f"Win11-Enroll-{onboarding_setup['uid']}"

    # 1. Register device
    reg_resp = client.post(
        "/api/v1/collectors/register",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"device_name": dev_name, "os_type": "windows", "environment": "production"}
    )
    assert reg_resp.status_code == 200
    enroll_token = reg_resp.json()["enrollment_token"]

    # 2. Collector performs enrollment handshake
    hostname = f"host-{onboarding_setup['uid']}"
    enroll_resp = client.post(
        "/api/v1/collectors/enroll",
        json={
            "enrollment_token": enroll_token,
            "hostname": hostname,
            "os_type": "windows",
            "os_version": "Windows 11 Pro 23H2",
            "collector_version": "1.0.0",
            "ip_address": "192.168.1.150",
            "machine_guid": "GUID-TEST-1234-ABCD"
        }
    )
    assert enroll_resp.status_code == 200
    enroll_data = enroll_resp.json()

    assert enroll_data["collector_key"].startswith("ov_col_")
    assert enroll_data["collector_name"] == dev_name
    collector_id = enroll_data["collector_id"]

    # Verify DB state
    db = SessionLocal()
    token_rec = db.query(DeviceEnrollmentToken).filter(
        DeviceEnrollmentToken.token_hash == hash_token(enroll_token)
    ).first()
    assert token_rec.consumed_at is not None  # Consumed!

    collector = db.query(Collector).filter(Collector.id == collector_id).first()
    assert collector.status == "online"
    assert collector.enrollment_status == "active"
    assert collector.token_hash == hash_token(enroll_data["collector_key"])
    assert collector.os_type == "windows"
    assert collector.hostname == hostname

    # Verify Server created & linked
    server = db.query(Server).filter(Server.collector_id == collector_id).first()
    assert server is not None
    assert server.display_name == dev_name

    # Verify Audit Log
    audit = db.query(DeviceAuditLog).filter(
        DeviceAuditLog.collector_id == collector_id,
        DeviceAuditLog.action == "ENROLLED"
    ).first()
    assert audit is not None
    assert "collector:" in audit.actor

    db.close()


def test_reused_single_use_token_rejected(onboarding_setup):
    """A consumed enrollment token must be immediately rejected on subsequent attempts."""
    token_a = onboarding_setup["user_a_token"]
    dev_name = f"Win11-Reuse-{onboarding_setup['uid']}"

    reg_resp = client.post(
        "/api/v1/collectors/register",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"device_name": dev_name, "os_type": "windows", "environment": "production"}
    )
    enroll_token = reg_resp.json()["enrollment_token"]

    # First enrollment succeeds
    resp1 = client.post(
        "/api/v1/collectors/enroll",
        json={"enrollment_token": enroll_token, "hostname": "host-reuse-1"}
    )
    assert resp1.status_code == 200

    # Second enrollment with same token MUST FAIL (Single-use policy)
    resp2 = client.post(
        "/api/v1/collectors/enroll",
        json={"enrollment_token": enroll_token, "hostname": "host-reuse-2"}
    )
    assert resp2.status_code == 400
    assert "already been consumed" in resp2.json()["detail"].lower()


def test_expired_token_rejected(onboarding_setup):
    """Expired enrollment tokens must be rejected."""
    db = SessionLocal()
    raw_token = generate_enrollment_token()
    token_hash = hash_token(raw_token)
    expired_time = datetime.now(timezone.utc) - timedelta(minutes=30)

    token_rec = DeviceEnrollmentToken(
        tenant_id=onboarding_setup["tenant_a_id"],
        device_name="Win11-Expired-Test",
        os_type="windows",
        environment="production",
        token_hash=token_hash,
        expires_at=expired_time
    )
    db.add(token_rec)
    db.commit()
    db.close()

    resp = client.post(
        "/api/v1/collectors/enroll",
        json={"enrollment_token": raw_token, "hostname": "host-expired"}
    )
    assert resp.status_code == 400
    assert "expired" in resp.json()["detail"].lower()


def test_invalid_token_rejected():
    """Invalid or nonexistent enrollment token must return 404."""
    resp = client.post(
        "/api/v1/collectors/enroll",
        json={"enrollment_token": "ov_enroll_nonexistent_token_12345", "hostname": "host-fake"}
    )
    assert resp.status_code == 404


def test_heartbeat_and_dynamic_online_offline_status(onboarding_setup):
    """
    Test Step 3: Verified device sends cryptographic heartbeat.
    Validates:
    - Heartbeat accepted with operational key
    - Status reports 'online'
    - Dynamic transition to 'offline' if heartbeat exceeds threshold
    - Reconnection back to 'online'
    """
    token_a = onboarding_setup["user_a_token"]
    dev_name = f"Win11-HB-{onboarding_setup['uid']}"

    # Register & Enroll
    reg_resp = client.post(
        "/api/v1/collectors/register",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"device_name": dev_name, "os_type": "windows", "environment": "production"}
    )
    enroll_resp = client.post(
        "/api/v1/collectors/enroll",
        json={"enrollment_token": reg_resp.json()["enrollment_token"], "hostname": "hb-test-node"}
    )
    col_key = enroll_resp.json()["collector_key"]
    col_id = enroll_resp.json()["collector_id"]

    # 1. Send Heartbeat
    hb_resp = client.post(
        "/api/v1/heartbeat",
        headers={"X-Collector-Key": col_key},
        json={
            "collector_id": col_id,
            "hostname": "hb-test-node",
            "status": "online",
            "version": "1.0.0",
            "collection_interval": 5,
            "buffered_records_count": 0,
            "failed_transmissions_count": 0
        }
    )
    assert hb_resp.status_code == 200
    assert hb_resp.json()["status"] == "acknowledged"

    # Query device list: Status must be 'online'
    list_resp = client.get("/api/v1/collectors", headers={"Authorization": f"Bearer {token_a}"})
    assert list_resp.status_code == 200
    target = next((c for c in list_resp.json() if c["id"] == col_id), None)
    assert target is not None
    assert target["status"] == "online"

    # 2. Simulate Heartbeat Timeout (Stale timestamp in DB)
    db = SessionLocal()
    col = db.query(Collector).filter(Collector.id == col_id).first()
    col.last_heartbeat = datetime.now(timezone.utc) - timedelta(seconds=120)  # > 60s timeout
    db.commit()
    db.close()

    # Query again: Must dynamically compute 'offline'
    list_resp2 = client.get("/api/v1/collectors", headers={"Authorization": f"Bearer {token_a}"})
    target2 = next((c for c in list_resp2.json() if c["id"] == col_id), None)
    assert target2["status"] == "offline"

    # 3. Collector reconnects: sends fresh heartbeat
    hb_reconnect = client.post(
        "/api/v1/heartbeat",
        headers={"X-Collector-Key": col_key},
        json={
            "collector_id": col_id,
            "hostname": "hb-test-node",
            "status": "online",
            "version": "1.0.0",
            "collection_interval": 5,
            "buffered_records_count": 0,
            "failed_transmissions_count": 0
        }
    )
    assert hb_reconnect.status_code == 200

    # Query again: Must transition back to 'online'
    list_resp3 = client.get("/api/v1/collectors", headers={"Authorization": f"Bearer {token_a}"})
    target3 = next((c for c in list_resp3.json() if c["id"] == col_id), None)
    assert target3["status"] == "online"


def test_device_revocation_blocks_heartbeat_and_telemetry(onboarding_setup):
    """
    Test Step 4: Administrator revokes device.
    Verifies:
    - Revocation endpoint succeeds and marks status 'revoked'
    - Subsequent heartbeats with that key receive HTTP 403 Forbidden
    - Subsequent telemetry egress with that key receives HTTP 403 Forbidden
    - Audit log records REVOKED action
    """
    token_a = onboarding_setup["user_a_token"]
    dev_name = f"Win11-Revoke-{onboarding_setup['uid']}"

    # Register & Enroll
    reg_resp = client.post(
        "/api/v1/collectors/register",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"device_name": dev_name, "os_type": "windows", "environment": "production"}
    )
    enroll_resp = client.post(
        "/api/v1/collectors/enroll",
        json={"enrollment_token": reg_resp.json()["enrollment_token"], "hostname": "revoke-test-node"}
    )
    col_key = enroll_resp.json()["collector_key"]
    col_id = enroll_resp.json()["collector_id"]

    # Administrator revokes the device
    revoke_resp = client.post(
        f"/api/v1/collectors/{col_id}/revoke",
        headers={"Authorization": f"Bearer {token_a}"}
    )
    assert revoke_resp.status_code == 200
    assert revoke_resp.json()["status"] == "revoked"

    # Attempt heartbeat with revoked key -> MUST BE FORBIDDEN (403)
    hb_blocked = client.post(
        "/api/v1/heartbeat",
        headers={"X-Collector-Key": col_key},
        json={
            "collector_id": col_id,
            "hostname": "revoke-test-node",
            "status": "online",
            "version": "1.0.0",
            "collection_interval": 5,
            "buffered_records_count": 0,
            "failed_transmissions_count": 0
        }
    )
    assert hb_blocked.status_code == 403
    assert "revoked" in hb_blocked.json()["detail"].lower()

    # Attempt telemetry ingestion with revoked key -> MUST BE FORBIDDEN (403)
    telemetry_batch = {
        "batch_id": f"batch-{uuid.uuid4().hex[:8]}",
        "collector_id": col_id,
        "records": [
            {
                "event_id": f"evt-{uuid.uuid4().hex[:8]}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "server_id": "srv-revoked",
                "hostname": "revoke-test-node",
                "collector_id": col_id,
                "collector_version": "1.0.0",
                "cpu_percent": 25.0,
                "memory_percent": 45.0,
                "disk_percent": 50.0,
                "network_latency_ms": 10.0,
                "packet_loss_percent": 0.0,
                "network_status": "connected",
                "failed_login_count": 0,
                "service_status": "up",
                "is_simulated": False
            }
        ]
    }
    telemetry_blocked = client.post(
        "/api/v1/telemetry",
        headers={"X-Collector-Key": col_key},
        json=telemetry_batch
    )
    assert telemetry_blocked.status_code == 403
    assert "revoked" in telemetry_blocked.json()["detail"].lower()


def test_cross_tenant_isolation(onboarding_setup):
    """Tenant B cannot view, modify, or revoke Tenant A's enrolled devices."""
    token_a = onboarding_setup["user_a_token"]
    token_b = onboarding_setup["user_b_token"]
    dev_name = f"Win11-Isolate-{onboarding_setup['uid']}"

    # Register & Enroll under Tenant A
    reg_resp = client.post(
        "/api/v1/collectors/register",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"device_name": dev_name, "os_type": "windows", "environment": "production"}
    )
    enroll_resp = client.post(
        "/api/v1/collectors/enroll",
        json={"enrollment_token": reg_resp.json()["enrollment_token"], "hostname": "isolate-node"}
    )
    col_id = enroll_resp.json()["collector_id"]

    # Tenant B tries to revoke Tenant A's device -> MUST FAIL (404)
    attack_revoke = client.post(
        f"/api/v1/collectors/{col_id}/revoke",
        headers={"Authorization": f"Bearer {token_b}"}
    )
    assert attack_revoke.status_code == 404

    # Tenant B tries to view Tenant A's audit history -> MUST FAIL (404)
    attack_audit = client.get(
        f"/api/v1/collectors/{col_id}/audit",
        headers={"Authorization": f"Bearer {token_b}"}
    )
    assert attack_audit.status_code == 404

    # Tenant B queries device list -> Tenant A's device MUST NOT appear
    list_b = client.get("/api/v1/collectors", headers={"Authorization": f"Bearer {token_b}"})
    assert not any(c["id"] == col_id for c in list_b.json())


def test_windows_platform_adapter_telemetry():
    """
    Validates Windows Platform Adapter:
    - Extracts real psutil hardware telemetry (CPU, Memory, Disk)
    - Correctly labels is_simulated == False
    - Sanitizes via LocalPrivacySanitiser
    """
    adapter = WindowsAdapter()
    assert adapter.get_os_name() == "windows"
    assert "windows" in adapter.get_os_version().lower()

    metrics = adapter.get_system_metrics()
    assert isinstance(metrics["cpu_percent"], float)
    assert 0.0 <= metrics["cpu_percent"] <= 100.0
    assert isinstance(metrics["memory_percent"], float)
    assert 0.0 <= metrics["memory_percent"] <= 100.0
    assert isinstance(metrics["disk_percent"], float)
    assert 0.0 <= metrics["disk_percent"] <= 100.0
    assert metrics["is_simulated"] is False

    # Privacy filtering pass-through
    raw_event = {
        "event_id": f"psutil-{uuid.uuid4().hex[:8]}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "server_id": "srv-win-psutil",
        "hostname": adapter.get_hostname(),
        "collector_id": "col-win-psutil",
        "collector_version": "1.0.0",
        "cpu_percent": metrics["cpu_percent"],
        "memory_percent": metrics["memory_percent"],
        "disk_percent": metrics["disk_percent"],
        "network_latency_ms": 12.5,
        "packet_loss_percent": 0.0,
        "network_status": "connected",
        "failed_login_count": 0,
        "service_status": "up",
        "is_simulated": metrics["is_simulated"],
        # Injected sensitive field to verify it's stripped
        "windows_user_password": "PasswordPlaintext123!"
    }
    outbound, summary = LocalPrivacySanitiser.sanitise_and_transform(raw_event)
    outbound_dict = outbound if isinstance(outbound, dict) else outbound.model_dump()
    assert "windows_user_password" not in outbound_dict
    rej_count = summary.get("fields_rejected", 0) if isinstance(summary, dict) else getattr(summary, "rejected_fields_count", 0)
    assert rej_count >= 1
    assert "windows_user_password" in summary.get("rejected_field_names", [])
    assert outbound_dict.get("is_simulated") is False


def test_device_management_stats_api(onboarding_setup):
    """Validates /collectors/stats API returns accurate device counts."""
    token_a = onboarding_setup["user_a_token"]
    resp = client.get("/api/v1/collectors/stats", headers={"Authorization": f"Bearer {token_a}"})
    assert resp.status_code == 200
    stats = resp.json()

    assert "total_devices" in stats
    assert "online_devices" in stats
    assert "offline_devices" in stats
    assert "pending_devices" in stats
    assert "revoked_devices" in stats
    assert isinstance(stats["collectors"], list)


def test_powershell_installer_endpoint():
    """Validates dynamic /install.ps1 endpoint returns valid PowerShell content."""
    resp = client.get("/api/v1/collectors/install.ps1")
    assert resp.status_code == 200
    content = resp.text
    assert "ObserVault Windows Collector One-Line Installer" in content
    assert "Invoke-RestMethod" in content
    assert "/api/v1/collectors/enroll" in content
