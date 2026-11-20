# backend/app/api/security_events.py
from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.models import Server, Alert, TelemetryRecord, User
from app.api.deps import get_current_user

router = APIRouter()

@router.get("")
def get_security_events(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns privacy-preserving security event metadata.
    Zero passwords, zero tokens, zero raw credentials ever exposed.
    Only aggregated statistical metrics (counts, rates, timestamps, severities).
    """
    tenant_id = current_user.tenant_id

    # Find servers with recorded failed login attempts
    servers = db.query(Server).filter(Server.tenant_id == tenant_id).all()
    server_auth_summary = []
    total_failed_logins = 0

    for s in servers:
        total_failed_logins += s.last_failed_logins
        if s.last_failed_logins > 0:
            server_auth_summary.append({
                "server_id": s.id,
                "hostname": s.hostname,
                "display_name": s.display_name,
                "failed_attempts": s.last_failed_logins,
                "security_status": "investigating" if s.last_failed_logins >= 3 else "normal"
            })

    # Auth event timeline
    records = db.query(TelemetryRecord).filter(
        TelemetryRecord.tenant_id == tenant_id,
        TelemetryRecord.failed_login_count > 0
    ).order_by(TelemetryRecord.timestamp.desc()).limit(20).all()

    auth_timeline = [
        {
            "event_id": r.event_id,
            "timestamp": r.timestamp.isoformat(),
            "server_id": r.server_id,
            "failed_attempts": r.failed_login_count,
            "privacy_guarantee": "Credentials sanitized locally; only count metadata transmitted"
        }
        for r in records
    ]

    # Security alerts
    security_alerts = db.query(Alert).filter(
        Alert.tenant_id == tenant_id,
        Alert.alert_type == "auth_spike"
    ).order_by(Alert.created_at.desc()).limit(10).all()

    return {
        "summary": {
            "total_failed_logins_recorded": total_failed_logins,
            "servers_with_auth_failures": len(server_auth_summary),
            "privacy_assurance": "Zero passwords, hashes, or auth tokens are captured or stored in ObserVault cloud."
        },
        "servers": server_auth_summary,
        "timeline": auth_timeline,
        "alerts": [
            {
                "id": a.id,
                "server_id": a.server_id,
                "title": a.title,
                "severity": a.severity,
                "observed_count": int(a.observed_value),
                "threshold": int(a.threshold_value),
                "status": a.status,
                "created_at": a.created_at.isoformat()
            }
            for a in security_alerts
        ]
    }
