# backend/app/api/infrastructure.py
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.models import Server, TelemetryRecord, User
from app.schemas.schemas import ServerOut
from app.api.deps import get_current_user

router = APIRouter()

@router.get("", response_model=List[ServerOut])
def list_servers(
    status: Optional[str] = Query(None, description="Filter by status: healthy, warning, critical, offline"),
    search: Optional[str] = Query(None, description="Search by hostname or display name"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Server).filter(Server.tenant_id == current_user.tenant_id)
    if status:
        query = query.filter(Server.status == status)
    if search:
        search_fmt = f"%{search}%"
        query = query.filter((Server.hostname.ilike(search_fmt)) | (Server.display_name.ilike(search_fmt)))
    
    servers = query.order_by(Server.hostname.asc()).all()
    return servers

@router.get("/{server_id}")
def get_server_detail(
    server_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    server = db.query(Server).filter(
        Server.id == server_id,
        Server.tenant_id == current_user.tenant_id
    ).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found or access denied")
    
    # Fetch last 30 telemetry points for detailed historical chart
    records = db.query(TelemetryRecord).filter(
        TelemetryRecord.server_id == server.id,
        TelemetryRecord.tenant_id == current_user.tenant_id
    ).order_by(TelemetryRecord.timestamp.desc()).limit(30).all()

    history = [
        {
            "timestamp": r.timestamp.strftime("%H:%M:%S"),
            "cpu": r.cpu_percent,
            "memory": r.memory_percent,
            "disk": r.disk_percent,
            "latency": r.network_latency_ms,
            "packet_loss": r.packet_loss_percent,
            "failed_logins": r.failed_login_count,
            "service_status": r.service_status
        }
        for r in reversed(records)
    ]

    return {
        "server": {
            "id": server.id,
            "hostname": server.hostname,
            "display_name": server.display_name,
            "ip_address": server.ip_address,
            "os_info": server.os_info,
            "status": server.status,
            "service_status": server.service_status,
            "last_cpu": server.last_cpu,
            "last_memory": server.last_memory,
            "last_disk": server.last_disk,
            "last_latency": server.last_latency,
            "last_packet_loss": server.last_packet_loss,
            "last_failed_logins": server.last_failed_logins,
            "is_simulated": server.is_simulated,
            "last_seen": server.last_seen.isoformat()
        },
        "history": history
    }
