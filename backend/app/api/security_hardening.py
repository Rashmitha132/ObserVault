# backend/app/api/security_hardening.py
"""
ObserVault Security Hardening & Certificate Management Endpoints.
Provides certificate issuance, expiration tracking, audit logging, and automated privacy testing.
"""

from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.certificates import cert_manager
from app.core.rbac import RequirePermissions, Permission
from app.models.models import User, Collector, Tenant, EgressAudit

router = APIRouter(prefix="/security-hardening", tags=["Security Hardening"])

class IssueCertRequest(BaseModel):
    collector_id: str
    validity_days: int = 90

class RevokeCertRequest(BaseModel):
    serial_number: str

# In-memory security audit log for replay and auth breaches
SECURITY_AUDIT_EVENTS = []

def record_security_event(event_type: str, severity: str, details: str, client_ip: str = "127.0.0.1"):
    SECURITY_AUDIT_EVENTS.insert(0, {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "severity": severity,
        "details": details,
        "client_ip": client_ip
    })
    # Cap to last 500 events
    if len(SECURITY_AUDIT_EVENTS) > 500:
        SECURITY_AUDIT_EVENTS.pop()

@router.get("/certificates", response_model=List[Dict[str, Any]])
def list_certificates(
    current_user: User = Depends(RequirePermissions([Permission.SECURITY_VIEW])),
    db: Session = Depends(get_db)
):
    """
    Returns the list of issued collector certificates and expiration health metrics for the tenant.
    """
    collectors = db.query(Collector).filter(Collector.tenant_id == current_user.tenant_id).all()
    results = []
    
    for col in collectors:
        # Check if cert exists in cert_manager directory
        cert_file = cert_manager.certs_dir / f"collector-{col.id}.crt"
        if cert_file.exists():
            valid, err, meta = cert_manager.verify_collector_certificate(cert_file.read_text())
            results.append({
                "collector_id": col.id,
                "collector_name": col.name,
                "hostname": col.hostname,
                "has_certificate": True,
                "status": "valid" if valid else ("revoked" if "revoked" in (err or "") else "expired"),
                "error": err,
                "metadata": meta
            })
        else:
            # Generate demonstration certificate for existing collector
            cert_data = cert_manager.issue_collector_certificate(col.id, current_user.tenant_id, col.hostname)
            # Write to disk
            cert_file.write_text(cert_data["certificate_pem"])
            valid, err, meta = cert_manager.verify_collector_certificate(cert_data["certificate_pem"])
            results.append({
                "collector_id": col.id,
                "collector_name": col.name,
                "hostname": col.hostname,
                "has_certificate": True,
                "status": "valid",
                "error": None,
                "metadata": meta
            })

    return results

@router.post("/certificates/issue", response_model=Dict[str, Any])
def issue_certificate(
    req: IssueCertRequest,
    current_user: User = Depends(RequirePermissions([Permission.SECURITY_MANAGE])),
    db: Session = Depends(get_db)
):
    """
    Issues a new X.509 client certificate for an on-premises collector node.
    """
    col = db.query(Collector).filter(
        Collector.id == req.collector_id,
        Collector.tenant_id == current_user.tenant_id
    ).first()

    if not col:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collector not found in current organization"
        )

    cert_data = cert_manager.issue_collector_certificate(
        collector_id=col.id,
        tenant_id=current_user.tenant_id,
        hostname=col.hostname,
        validity_days=req.validity_days
    )

    cert_file = cert_manager.certs_dir / f"collector-{col.id}.crt"
    cert_file.write_text(cert_data["certificate_pem"])

    record_security_event(
        event_type="CERTIFICATE_ISSUED",
        severity="low",
        details=f"X.509 certificate issued for {col.name} ({col.id}). Serial: {cert_data['serial_number']}"
    )

    return cert_data

@router.post("/certificates/revoke", response_model=Dict[str, Any])
def revoke_certificate(
    req: RevokeCertRequest,
    current_user: User = Depends(RequirePermissions([Permission.SECURITY_MANAGE]))
):
    """
    Revokes a compromised or decommissioned collector certificate by serial number.
    """
    try:
        serial_int = int(req.serial_number)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid serial number format")

    cert_manager.revoke_certificate(serial_int)
    record_security_event(
        event_type="CERTIFICATE_REVOKED",
        severity="high",
        details=f"Serial {req.serial_number} revoked by user {current_user.email}"
    )
    return {"status": "success", "serial_number": req.serial_number, "is_revoked": True}

@router.get("/audit", response_model=List[Dict[str, Any]])
def get_security_audit_log(
    current_user: User = Depends(RequirePermissions([Permission.SECURITY_VIEW]))
):
    """
    Returns security events: mTLS handshake evaluations, signature checks, and replay defense logs.
    """
    return SECURITY_AUDIT_EVENTS

@router.get("/privacy-tests", response_model=Dict[str, Any])
def run_privacy_verification_suite(
    current_user: User = Depends(RequirePermissions([Permission.PRIVACY_AUDIT]))
):
    """
    Executes automated privacy attack tests and certifies that sensitive artifacts
    (passwords, tokens, keys, PII, SQL params) are pruned locally.
    """
    from collector.privacy.sanitiser import LocalPrivacySanitiser

    test_payloads = [
        {"name": "Hardcoded DB Password", "input": {"db_password": "super_secret_password_123", "cpu_percent": 45.0}},
        {"name": "Bearer Auth Token", "input": {"authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.abc", "memory_percent": 60.0}},
        {"name": "AWS API Secret Key", "input": {"aws_secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"}},
        {"name": "Plaintext Credit Card", "input": {"credit_card_number": "4111-2222-3333-4444", "disk_percent": 75.0}},
        {"name": "Raw SQL Query Body", "input": {"sql_query": "SELECT * FROM users WHERE ssn='123-45-6789'"}}
    ]

    results = []
    total_leaked = 0

    for test in test_payloads:
        outbound, summary = LocalPrivacySanitiser.sanitise_and_transform(test["input"])
        leaked_keys = [k for k in test["input"] if k in outbound]
        if leaked_keys:
            total_leaked += len(leaked_keys)
        results.append({
            "test_name": test["name"],
            "keys_tested": list(test["input"].keys()),
            "keys_purged": summary["rejected_keys"],
            "leaked_keys": leaked_keys,
            "passed": len(leaked_keys) == 0
        })

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_tests_executed": len(test_payloads),
        "total_leaks_detected": total_leaked,
        "certified_zero_leak": total_leaked == 0,
        "test_results": results
    }
