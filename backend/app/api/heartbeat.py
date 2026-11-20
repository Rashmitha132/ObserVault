# backend/app/api/heartbeat.py
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.models import Collector
from app.schemas.schemas import HeartbeatRequest
from app.api.deps import get_current_collector

router = APIRouter()

@router.post("")
def receive_heartbeat(
    payload: HeartbeatRequest,
    collector: Collector = Depends(get_current_collector),
    db: Session = Depends(get_db)
):
    now = datetime.now(timezone.utc)
    collector.last_heartbeat = now
    collector.status = payload.status
    collector.buffered_records_count = payload.buffered_records_count
    collector.failed_transmissions_count = payload.failed_transmissions_count
    collector.collection_interval = payload.collection_interval
    for srv in collector.servers:
        srv.last_seen = now
        if srv.status == "offline":
            srv.status = "healthy"
    db.commit()

    return {
        "status": "acknowledged",
        "collector_id": collector.id,
        "server_time": now.isoformat(),
        "next_heartbeat_expected_in": collector.collection_interval
    }
