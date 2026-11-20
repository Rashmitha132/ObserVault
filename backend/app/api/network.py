# backend/app/api/network.py
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.models import Server, TelemetryRecord, Alert, User
from app.api.deps import get_current_user

router = APIRouter()

@router.get("")
def get_network_observability(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    tenant_id = current_user.tenant_id

    # Get servers with network telemetry
    servers = db.query(Server).filter(Server.tenant_id == tenant_id).all()

    server_network_stats = []
    for s in servers:
        server_network_stats.append({
            "id": s.id,
            "hostname": s.hostname,
            "display_name": s.display_name,
            "ip_address": s.ip_address,
            "latency_ms": round(s.last_latency, 1),
            "packet_loss_percent": round(s.last_packet_loss, 1),
            "status": "degraded" if (s.last_latency > 120 or s.last_packet_loss > 5) else "optimal",
            "is_simulated": s.is_simulated
        })

    # Recent network latency time series (chronological)
    recent_records = db.query(TelemetryRecord).filter(
        TelemetryRecord.tenant_id == tenant_id
    ).order_by(TelemetryRecord.timestamp.desc()).limit(25).all()

    network_trends = [
        {
            "time": r.timestamp.strftime("%H:%M:%S"),
            "latency_ms": round(r.network_latency_ms, 1),
            "packet_loss_percent": round(r.packet_loss_percent, 1),
            "server": r.server_id
        }
        for r in reversed(recent_records)
    ]

    # Active network alerts
    network_alerts = db.query(Alert).filter(
        Alert.tenant_id == tenant_id,
        Alert.alert_type.in_(["high_latency", "packet_loss"]),
        Alert.status == "active"
    ).all()

    return {
        "servers": server_network_stats,
        "trends": network_trends,
        "active_anomalies": [
            {
                "id": a.id,
                "server_id": a.server_id,
                "title": a.title,
                "severity": a.severity,
                "metric_name": a.metric_name,
                "observed_value": a.observed_value,
                "threshold_value": a.threshold_value,
                "created_at": a.created_at.isoformat()
            }
            for a in network_alerts
        ]
    }
