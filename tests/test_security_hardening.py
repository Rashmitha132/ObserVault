# tests/test_security_hardening.py
"""
Test Suite for ObserVault Phase 2A: Security Hardening & Cryptographic Integrity.
Validates RBAC, HMAC-SHA256 signed batches, anti-replay nonces, mTLS certificates,
and extended privacy leakage tests.
"""

import time
import json
import secrets
import sys
import os
from datetime import datetime, timezone, timedelta

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, root_dir)
sys.path.insert(0, os.path.join(root_dir, "backend"))

from app.core.rbac import (
    Role, Permission, has_permission, resolve_role, ROLE_PERMISSIONS
)
from app.core.crypto import TelemetrySigner, nonce_cache
from app.core.certificates import cert_manager
from collector.privacy.sanitiser import LocalPrivacySanitiser

def test_rbac_permissions():
    """Validates permission matrices for all 4 roles."""
    # Org admin has all permissions
    for p in Permission:
        assert has_permission(Role.ORG_ADMIN, p) is True

    # Read-only viewer can view but not manage
    assert has_permission(Role.READ_ONLY_VIEWER, Permission.INFRA_VIEW) is True
    assert has_permission(Role.READ_ONLY_VIEWER, Permission.INFRA_MANAGE) is False
    assert has_permission(Role.READ_ONLY_VIEWER, Permission.INCIDENTS_RESOLVE) is False

    # Security analyst can manage security and audit privacy
    assert has_permission(Role.SECURITY_ANALYST, Permission.SECURITY_MANAGE) is True
    assert has_permission(Role.SECURITY_ANALYST, Permission.PRIVACY_AUDIT) is True
    assert has_permission(Role.SECURITY_ANALYST, Permission.INFRA_MANAGE) is False

    # DevOps engineer can manage infra and resolve incidents
    assert has_permission(Role.DEVOPS_ENGINEER, Permission.INFRA_MANAGE) is True
    assert has_permission(Role.DEVOPS_ENGINEER, Permission.INCIDENTS_RESOLVE) is True
    assert has_permission(Role.DEVOPS_ENGINEER, Permission.PRIVACY_AUDIT) is False

    # Legacy role backward compatibility
    assert has_permission("admin", Permission.USERS_MANAGE) is True
    assert has_permission("engineer", Permission.INFRA_MANAGE) is True

def test_crypto_batch_signing_and_verification():
    """Tests HMAC-SHA256 signature generation and validation."""
    secret_key = "test-secret-key-12345"
    collector_id = "col-edge-01"
    now_str = datetime.now(timezone.utc).isoformat()
    nonce = f"test-nonce-{secrets.token_hex(8)}"
    payload = {
        "batch_id": "batch-101",
        "collector_id": collector_id,
        "records": [{"cpu_percent": 88.5, "memory_percent": 72.0}]
    }

    sig = TelemetrySigner.sign_batch(secret_key, collector_id, now_str, nonce, payload)
    assert len(sig) == 64  # SHA256 hex string

    # Verify signature
    valid, err = TelemetrySigner.verify_batch(secret_key, collector_id, now_str, nonce, sig, payload)
    assert valid is True
    assert err is None

def test_crypto_tamper_detection():
    """Modifying payload in transit invalidates the cryptographic signature."""
    secret_key = "test-secret-key-12345"
    collector_id = "col-edge-01"
    now_str = datetime.now(timezone.utc).isoformat()
    nonce = f"test-nonce-{secrets.token_hex(8)}"
    payload = {"records": [{"cpu_percent": 50.0}]}

    sig = TelemetrySigner.sign_batch(secret_key, collector_id, now_str, nonce, payload)

    # Tampered payload (e.g. adversary altered CPU metric to hide a breach)
    tampered_payload = {"records": [{"cpu_percent": 99.9}]}
    valid, err = TelemetrySigner.verify_batch(secret_key, collector_id, now_str, nonce, sig, tampered_payload)
    assert valid is False
    assert "mismatch" in err.lower()

def test_crypto_replay_attack_rejection():
    """Resending a previously accepted nonce triggers replay defense."""
    secret_key = "test-secret-key-12345"
    collector_id = "col-edge-01"
    now_str = datetime.now(timezone.utc).isoformat()
    replay_nonce = f"replay-nonce-{secrets.token_hex(8)}"
    payload = {"records": [{"cpu_percent": 25.0}]}

    sig = TelemetrySigner.sign_batch(secret_key, collector_id, now_str, replay_nonce, payload)

    # First transmission: Accepted
    valid, _ = TelemetrySigner.verify_batch(secret_key, collector_id, now_str, replay_nonce, sig, payload)
    assert valid is True

    # Replay attempt: Rejected
    replayed_valid, err = TelemetrySigner.verify_batch(secret_key, collector_id, now_str, replay_nonce, sig, payload)
    assert replayed_valid is False
    assert "replay attack detected" in err.lower()

def test_crypto_timestamp_skew_rejection():
    """Timestamps outside the 5-minute allowable drift are rejected."""
    secret_key = "test-secret-key-12345"
    collector_id = "col-edge-01"
    old_ts = (datetime.now(timezone.utc) - timedelta(minutes=15)).isoformat()
    nonce = f"skew-nonce-{secrets.token_hex(8)}"
    payload = {"records": []}

    sig = TelemetrySigner.sign_batch(secret_key, collector_id, old_ts, nonce, payload)
    valid, err = TelemetrySigner.verify_batch(secret_key, collector_id, old_ts, nonce, sig, payload)
    assert valid is False
    assert "drift exceeds" in err.lower()

def test_mtls_certificate_lifecycle():
    """Validates X.509 Root CA and collector certificate issuance and revocation."""
    cert_data = cert_manager.issue_collector_certificate(
        collector_id="col-sec-test-01",
        tenant_id="tenant-acme-1",
        hostname="node-auth-01.internal",
        validity_days=30
    )
    assert "BEGIN CERTIFICATE" in cert_data["certificate_pem"]
    assert "BEGIN RSA PRIVATE KEY" in cert_data["private_key_pem"]
    assert cert_data["subject_cn"] == "collector-col-sec-test-01"

    # Verify certificate against CA
    is_valid, err, meta = cert_manager.verify_collector_certificate(cert_data["certificate_pem"])
    assert is_valid is True
    assert err is None
    assert meta["common_name"] == "collector-col-sec-test-01"
    assert meta["days_remaining"] >= 29

    # Test revocation
    serial = int(cert_data["serial_number"])
    cert_manager.revoke_certificate(serial)
    assert cert_manager.is_revoked(serial) is True

    revoked_valid, rev_err, _ = cert_manager.verify_collector_certificate(cert_data["certificate_pem"])
    assert revoked_valid is False
    assert "revoked" in rev_err.lower()

def test_extended_privacy_verification():
    """Verifies that nested and attack-injected credentials never leak into egress records."""
    malicious_payload = {
        "event_id": "test-leak-evt-01",
        "cpu_percent": 55.0,
        "memory_percent": 60.0,
        "disk_percent": 70.0,
        "network_latency_ms": 12.0,
        "packet_loss_percent": 0.0,
        # Injected sensitive keys:
        "bearer_token": "eyJhbGciOiJIUzI1NiJ9.attack_vector_token",
        "aws_secret_key": "AKIAIOSFODNN7EXAMPLE",
        "password_hash": "$6$salt$hashedpassword",
        "raw_syslog_payload": "May 10 12:00:00 sshd: Failed password for root from 1.2.3.4",
        "ssn": "000-12-3456",
        "database_url": "postgresql://root:SuperSecret123@db.prod.internal:5432/finance"
    }

    outbound, summary = LocalPrivacySanitiser.sanitise_and_transform(malicious_payload)

    # Assure all sensitive keys were pruned
    for sensitive_key in ["bearer_token", "aws_secret_key", "password_hash", "raw_syslog_payload", "ssn", "database_url"]:
        assert sensitive_key not in outbound
        assert sensitive_key in summary["rejected_field_names"]

    assert summary["sensitive_data_stripped"] is True
    assert outbound["cpu_percent"] == 55.0
