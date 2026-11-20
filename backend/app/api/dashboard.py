# backend/app/api/dashboard.py
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.database import get_db
from app.core.config import settings
from app.models.models import (
    User, Server, Alert, Incident, Collector, TelemetryRecord, EgressAudit
)
from app.api.deps import get_current_user

router = APIRouter()

# OV-BUG-004 Fix: Support /overview, /summary, and root /dashboard with or without trailing slash
@router.get("/overview")
@router.get("/summary")
@router.get("")
@router.get("/")
def get_dashboard_overview(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    tenant_id = current_user.tenant_id
    now = datetime.now(timezone.utc)
    heartbeat_cutoff = now - timedelta(seconds=settings.HEARTBEAT_TIMEOUT_SECONDS)

    # 1. Monitored Servers summary
    servers = db.query(Server).filter(Server.tenant_id == tenant_id).all()
    total_servers = len(servers)
    
    # Mark servers offline if last_seen > 90 seconds
    healthy_servers = 0
    warning_servers = 0
    critical_servers = 0
    offline_servers = 0

    for s in servers:
        # Check if collector or server is offline
        if s.last_seen and (now - s.last_seen.replace(tzinfo=timezone.utc if s.last_seen.tzinfo is None else None)).total_seconds() > 90:
            s.status = "offline"
            offline_servers += 1
        elif s.status == "critical":
            critical_servers += 1
        elif s.status == "warning":
            warning_servers += 1
        else:
            healthy_servers += 1

    # 2. Collectors summary
    collectors = db.query(Collector).filter(Collector.tenant_id == tenant_id).all()
    online_collectors = 0
    offline_collectors = 0
    total_buffered_records = 0

    for c in collectors:
        last_hb = c.last_heartbeat.replace(tzinfo=timezone.utc if c.last_heartbeat.tzinfo is None else None)
        if last_hb < heartbeat_cutoff:
            c.status = "offline"
            offline_collectors += 1
        else:
            c.status = "online"
            online_collectors += 1
        total_buffered_records += (c.buffered_records_count or 0)

    # 3. Alerts and Incidents
    active_alerts_count = db.query(Alert).filter(
        Alert.tenant_id == tenant_id,
        Alert.status == "active"
    ).count()

    critical_alerts_count = db.query(Alert).filter(
        Alert.tenant_id == tenant_id,
        Alert.status == "active",
        Alert.severity == "critical"
    ).count()

    active_incidents_count = db.query(Incident).filter(
        Incident.tenant_id == tenant_id,
        Incident.status.in_(["open", "investigating"])
    ).count()

    # 4. Privacy & Egress Counters
    egress_records = db.query(EgressAudit).filter(EgressAudit.tenant_id == tenant_id).all()
    total_processed_locally = sum(e.total_processed for e in egress_records)
    total_approved = sum(e.approved_count for e in egress_records)
    total_rejected_fields = sum(e.rejected_fields_count for e in egress_records)
    
    last_audit = db.query(EgressAudit).filter(
        EgressAudit.tenant_id == tenant_id
    ).order_by(EgressAudit.timestamp.desc()).first()

    # 5. System Trends (last 20 telemetry records)
    recent_telemetry = db.query(TelemetryRecord).filter(
        TelemetryRecord.tenant_id == tenant_id
    ).order_by(TelemetryRecord.timestamp.desc()).limit(20).all()

    # Format telemetry time series in chronological order
    trend_points = []
    for r in reversed(recent_telemetry):
        trend_points.append({
            "time": r.timestamp.strftime("%H:%M:%S"),
            "cpu": round(r.cpu_percent, 1),
            "memory": round(r.memory_percent, 1),
            "latency": round(r.network_latency_ms, 1),
            "packet_loss": round(r.packet_loss_percent, 1),
            "failed_logins": r.failed_login_count
        })

    # 6. Recent Alerts & Incidents lists
    recent_alerts = db.query(Alert).filter(
        Alert.tenant_id == tenant_id
    ).order_by(Alert.created_at.desc()).limit(5).all()

    recent_incidents = db.query(Incident).filter(
        Incident.tenant_id == tenant_id
    ).order_by(Incident.created_at.desc()).limit(5).all()

    return {
        "infrastructure": {
            "total_servers": total_servers,
            "healthy": healthy_servers,
            "warning": warning_servers,
            "critical": critical_servers,
            "offline": offline_servers
        },
        "collectors": {
            "total": len(collectors),
            "online": online_collectors,
            "offline": offline_collectors,
            "buffered_records": total_buffered_records
        },
        "alerts": {
            "active_total": active_alerts_count,
            "critical": critical_alerts_count
        },
        "incidents": {
            "active_total": active_incidents_count
        },
        "privacy": {
            "records_processed_locally": total_processed_locally,
            "records_approved_outbound": total_approved,
            "sensitive_fields_rejected": total_rejected_fields,
            "currently_buffered": total_buffered_records,
            "last_transmission": last_audit.timestamp.isoformat() if last_audit else None
        },
        "trends": trend_points,
        "recent_alerts": [
            {
                "id": a.id,
                "title": a.title,
                "severity": a.severity,
                "metric_name": a.metric_name,
                "observed_value": a.observed_value,
                "threshold_value": a.threshold_value,
                "status": a.status,
                "created_at": a.created_at.isoformat()
            } for a in recent_alerts
        ],
        "recent_incidents": [
            {
                "id": i.id,
                "code": i.incident_code,
                "title": i.title,
                "severity": i.severity,
                "status": i.status,
                "confidence_score": i.confidence_score,
                "created_at": i.created_at.isoformat()
            } for i in recent_incidents
        ]
    }
