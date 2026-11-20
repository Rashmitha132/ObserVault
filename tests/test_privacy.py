# tests/test_privacy.py
import pytest
import sys
import os
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from collector.privacy.sanitiser import LocalPrivacySanitiser
from collector.privacy.allowlist import APPROVED_OUTBOUND_KEYS

def test_sensitive_fields_stripped_locally():
    raw_event = {
        "event_id": "test-sec-99",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": "failed_login",
        "failed_attempt_count": 5,
        "username": "admin_root",
        "password": "ClearTextPassword456!",
        "auth_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.payload.sig",
        "api_key": "sk_live_very_secret_key_777",
        "ip_address": "10.0.0.99",
        "raw_payload": "{\"cmd\": \"drop database\"}",
        "cpu_percent": 88.0,
        "memory_percent": 72.0,
        "disk_percent": 50.0,
        "network_latency_ms": 30.0,
        "packet_loss_percent": 0.0
    }

    outbound, summary = LocalPrivacySanitiser.sanitise_and_transform(raw_event)

    # Assert none of the sensitive keys exist in outbound record
    assert "password" not in outbound
    assert "username" not in outbound
    assert "auth_token" not in outbound
    assert "api_key" not in outbound
    assert "raw_payload" not in outbound
    assert "ip_address" not in outbound

    # Assert outbound keys are subset of APPROVED_OUTBOUND_KEYS
    for key in outbound.keys():
        assert key in APPROVED_OUTBOUND_KEYS, f"Unexpected key '{key}' found in outbound metadata!"

    # Assert summary accurately captured privacy metrics
    assert summary["fields_rejected"] >= 6
    assert summary["sensitive_data_stripped"] is True
    assert outbound["failed_login_count"] == 5

def test_backend_pydantic_rejects_unapproved_fields():
    from app.schemas.schemas import OutboundTelemetryRecord
    from pydantic import ValidationError

    # Attempt to construct outbound record containing a forbidden field
    dirty_payload = {
        "event_id": "evt-123",
        "timestamp": datetime.now(timezone.utc),
        "server_id": "srv-1",
        "hostname": "host-1",
        "collector_id": "col-1",
        "collector_version": "1.0.0",
        "cpu_percent": 50.0,
        "memory_percent": 60.0,
        "disk_percent": 70.0,
        "network_latency_ms": 20.0,
        "packet_loss_percent": 0.0,
        "network_status": "connected",
        "failed_login_count": 0,
        "service_status": "up",
        "is_simulated": False,
        "password": "AttemptedLeakPassword!" # FORBIDDEN EXTRA FIELD
    }

    with pytest.raises(ValidationError) as exc_info:
        OutboundTelemetryRecord(**dirty_payload)

    errors = exc_info.value.errors()
    assert any(e["type"] == "extra_forbidden" and "password" in str(e["loc"]) for e in errors)
