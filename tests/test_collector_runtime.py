# tests/test_collector_runtime.py
"""
ObserVault Collector Runtime Automated Test Suite:
Validates:
1. Continuous heartbeat signaling keeps collector online.
2. Telemetry ingestion of authentic psutil hardware metrics.
3. Offline SQLite buffering and retry/drain upon reconnection.
4. Device status transition to 'offline' when heartbeat timeout (>60s) is exceeded,
   and dynamic recovery back to 'online' upon receiving fresh heartbeat.
5. Collector runtime daemon lifecycle and PID management.
"""

import os
import sys
import uuid
import json
import time
from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient

backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)
if root_path not in sys.path:
    sys.path.insert(0, root_path)

from app.main import app
from app.core.database import SessionLocal
from app.models.models import (
    Tenant, User, Collector, Server, TelemetryRecord
)
from app.core.security import get_password_hash, create_access_token, hash_token, generate_collector_key
from app.core.config import settings as backend_settings
from collector.platform_adapter import get_platform_adapter
from collector.privacy.sanitiser import LocalPrivacySanitiser
from collector.buffer.sqlite_buffer import SQLiteBuffer
from collector.transport.secure_sender import SecureSender
from collector.config.settings import settings as collector_settings

client = TestClient(app)


@pytest.fixture(scope="module")
def runtime_setup():
    db = SessionLocal()
    uid = uuid.uuid4().hex[:8]

    tenant = db.query(Tenant).filter(Tenant.slug == "runtime-org").first()
    if not tenant:
        tenant = Tenant(name="Runtime Test Org", slug=f"runtime-{uid}", plan="Enterprise")
        db.add(tenant)
        db.flush()

    user = User(
        tenant_id=tenant.id,
        email=f"admin-runtime-{uid}@org.com",
        hashed_password=get_password_hash("SecretPass123!"),
        full_name="Runtime Test Admin",
        role="admin",
        is_active=True
    )
    db.add(user)
    db.flush()

    raw_op_key = generate_collector_key()
    op_key_hash = hash_token(raw_op_key)

    collector_id = f"col-rt-{uid}"
    hostname = f"host-{uid}"
    collector = Collector(
        id=collector_id,
        tenant_id=tenant.id,
        token_hash=op_key_hash,
        name=f"Runtime-Test-Host-{uid}",
        hostname=hostname,
        ip_address="127.0.0.1",
        version="1.0.0",
        os_type="windows",
        os_version="Windows 11 Test",
        status="online",
        enrollment_status="active",
        is_revoked=False,
        collection_interval=5,
        last_heartbeat=datetime.now(timezone.utc),
        last_successful_transmission=datetime.now(timezone.utc)
    )
    db.add(collector)
    db.flush()

    server = Server(
        id=str(uuid.uuid4()),
        tenant_id=tenant.id,
        collector_id=collector.id,
        hostname=hostname,
        display_name=f"Runtime-Test-Host-{uid}",
        ip_address="127.0.0.1",
        os_info="Windows 11 Test",
        status="healthy",
        service_status="up",
        last_seen=datetime.now(timezone.utc)
    )
    db.add(server)
    db.commit()

    tenant_id = str(tenant.id)
    user_id = str(user.id)
    user_role = user.role
    server_id = str(server.id)

    token = create_access_token(
        subject=user_id, tenant_id=tenant_id, role=user_role
    )
    db.close()

    yield {
        "tenant_id": tenant_id,
        "collector_id": collector_id,
        "hostname": hostname,
        "server_id": server_id,
        "collector_key": raw_op_key,
        "auth_headers": {"Authorization": f"Bearer {token}"},
        "collector_headers": {"X-Collector-Key": raw_op_key}
    }


def test_continuous_heartbeats(runtime_setup):
    """Verify consecutive heartbeats refresh last_heartbeat timestamp and keep status online."""
    headers = runtime_setup["collector_headers"]
    cid = runtime_setup["collector_id"]
    hostname = runtime_setup["hostname"]

    # Send first heartbeat
    r1 = client.post(
        "/api/v1/heartbeat",
        headers=headers,
        json={
            "collector_id": cid,
            "hostname": hostname,
            "status": "online",
            "version": "1.0.0",
            "collection_interval": 5,
            "buffered_records_count": 0,
            "failed_transmissions_count": 0
        }
    )
    assert r1.status_code == 200
    data1 = r1.json()
    assert data1["status"] == "acknowledged"
    assert data1["collector_id"] == cid

    # Send second heartbeat
    r2 = client.post(
        "/api/v1/heartbeat",
        headers=headers,
        json={
            "collector_id": cid,
            "hostname": hostname,
            "status": "online",
            "version": "1.0.0",
            "collection_interval": 5,
            "buffered_records_count": 2,
            "failed_transmissions_count": 0
        }
    )
    assert r2.status_code == 200
    data2 = r2.json()
    assert data2["status"] == "acknowledged"

    # Verify device status via API
    r_stats = client.get("/api/v1/collectors", headers=runtime_setup["auth_headers"])
    assert r_stats.status_code == 200
    collectors = r_stats.json()
    matched = [c for c in collectors if c["id"] == cid]
    assert len(matched) == 1
    assert matched[0]["status"] == "online"


def test_telemetry_ingestion_authentic_metrics(runtime_setup):
    """Verify authentic hardware metrics from platform adapter are ingested and stored."""
    adapter = get_platform_adapter()
    raw_metric = adapter.get_system_metrics()

    # Must be real hardware metrics, not fabricated
    assert raw_metric["is_simulated"] is False
    assert 0.0 <= raw_metric["cpu_percent"] <= 100.0
    assert 0.0 <= raw_metric["memory_percent"] <= 100.0
    assert 0.0 <= raw_metric["disk_percent"] <= 100.0

    raw_metric.update({
        "event_id": f"evt-{uuid.uuid4().hex[:8]}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "network_latency_ms": 1.45,
        "packet_loss_percent": 0.0,
        "network_status": "connected",
        "failed_login_count": 0,
        "service_status": "up"
    })

    clean_record, _ = LocalPrivacySanitiser.sanitise_and_transform(raw_metric)
    clean_record["server_id"] = runtime_setup["server_id"]
    clean_record["hostname"] = runtime_setup["hostname"]
    clean_record["collector_id"] = runtime_setup["collector_id"]
    clean_record["collector_version"] = "1.0.0"

    # Ingest payload through the backend
    headers = runtime_setup["collector_headers"]
    cid = runtime_setup["collector_id"]
    batch_payload = {
        "batch_id": f"batch-{uuid.uuid4().hex[:8]}",
        "collector_id": cid,
        "records": [clean_record]
    }
    r = client.post(
        "/api/v1/telemetry",
        headers=headers,
        json=batch_payload
    )
    assert r.status_code == 200
    res = r.json()
    assert res["status"] == "success"
    assert res["records_ingested"] >= 1

    # Verify record was stored in database
    db = SessionLocal()
    rec = db.query(TelemetryRecord).filter(
        TelemetryRecord.server_id == runtime_setup["server_id"]
    ).order_by(TelemetryRecord.timestamp.desc()).first()
    db.close()

    assert rec is not None
    assert rec.is_simulated is False
    assert rec.cpu_percent == raw_metric["cpu_percent"]
    assert rec.memory_percent == raw_metric["memory_percent"]


def test_offline_buffering_and_reconnection(runtime_setup, tmp_path):
    """
    Verify that when network is down, records buffer into local SQLiteBuffer,
    and upon reconnection, they are drained and transmitted cleanly.
    """
    test_db = str(tmp_path / "test_buffer.db")
    buf = SQLiteBuffer(db_path=test_db)

    # Simulate 3 metrics captured during network outage
    event_ids = []
    for i in range(3):
        eid = f"evt-{uuid.uuid4().hex[:8]}"
        event_ids.append(eid)
        buf.enqueue(eid, {
            "event_id": eid,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "server_id": runtime_setup["server_id"],
            "hostname": runtime_setup["hostname"],
            "collector_id": runtime_setup["collector_id"],
            "collector_version": "1.0.0",
            "cpu_percent": 30.0 + i,
            "memory_percent": 60.0,
            "disk_percent": 45.0,
            "network_latency_ms": 1.2,
            "packet_loss_percent": 0.0,
            "network_status": "connected",
            "failed_login_count": 0,
            "service_status": "up",
            "is_simulated": False
        })

    stats = buf.get_stats()
    assert stats["pending"] == 3

    # Simulate reconnection: pop records and transmit
    pending = buf.get_pending(limit=10)
    assert len(pending) == 3
    batch = [item["payload"] for item in pending]

    headers = runtime_setup["collector_headers"]
    cid = runtime_setup["collector_id"]
    r = client.post(
        "/api/v1/telemetry",
        headers=headers,
        json={
            "batch_id": f"batch-{uuid.uuid4().hex[:8]}",
            "collector_id": cid,
            "records": batch
        }
    )
    assert r.status_code == 200
    assert r.json()["records_ingested"] == 3

    # Mark delivered in buffer
    delivered_ids = [item["event_id"] for item in pending]
    buf.mark_delivered(delivered_ids)

    # Buffer pending should now be 0
    assert buf.get_stats()["pending"] == 0


def test_device_status_transition_on_timeout(runtime_setup):
    """
    Verify dynamic status evaluation:
    - Device transitions to 'offline' when last_heartbeat is older than 60s
    - Device transitions back to 'online' as soon as fresh heartbeat arrives
    """
    cid = runtime_setup["collector_id"]
    db = SessionLocal()
    col = db.query(Collector).filter(Collector.id == cid).first()

    # Manually age the heartbeat to 90 seconds ago (> 60s HEARTBEAT_TIMEOUT_SECONDS)
    aged_time = datetime.now(timezone.utc) - timedelta(seconds=90)
    col.last_heartbeat = aged_time
    db.commit()
    db.close()

    # Query device status - must compute as offline
    r = client.get("/api/v1/collectors", headers=runtime_setup["auth_headers"])
    assert r.status_code == 200
    matched = [c for c in r.json() if c["id"] == cid][0]
    assert matched["status"] == "offline"

    # Send a new heartbeat to revive device
    r_hb = client.post(
        "/api/v1/heartbeat",
        headers=runtime_setup["collector_headers"],
        json={
            "collector_id": cid,
            "hostname": runtime_setup["hostname"],
            "status": "online",
            "version": "1.0.0",
            "collection_interval": 5,
            "buffered_records_count": 0,
            "failed_transmissions_count": 0
        }
    )
    assert r_hb.status_code == 200

    # Query device status again - must now compute as online
    r2 = client.get("/api/v1/collectors", headers=runtime_setup["auth_headers"])
    assert r2.status_code == 200
    matched2 = [c for c in r2.json() if c["id"] == cid][0]
    assert matched2["status"] == "online"


def test_runtime_pid_and_status():
    """Verify runtime PID management logic."""
    from collector.runtime import get_runtime_dir, is_pid_running, get_running_pid

    # Current test runner PID is running
    current_pid = os.getpid()
    assert is_pid_running(current_pid) is True
    # Bogus negative or ultra-high PID is not running
    assert is_pid_running(9999999) is False
    assert is_pid_running(-1) is False

    runtime_dir = get_runtime_dir()
    assert runtime_dir.exists()
