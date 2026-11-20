# backend/app/api/alerts.py
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.models import Alert, Server, User
from app.schemas.schemas import AlertOut, AlertStatusUpdate
from app.api.deps import get_current_user

router = APIRouter()

@router.get("", response_model=List[AlertOut])
def list_alerts(
    status: Optional[str] = Query(None, description="active, acknowledged, resolved"),
    severity: Optional[str] = Query(None, description="critical, high, medium, low"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Alert).filter(Alert.tenant_id == current_user.tenant_id)
    if status:
        query = query.filter(Alert.status == status)
    if severity:
        query = query.filter(Alert.severity == severity)

    alerts = query.order_by(Alert.created_at.desc()).all()
    results = []
    for a in alerts:
        server = db.query(Server).filter(Server.id == a.server_id).first()
        results.append(AlertOut(
            id=a.id,
            tenant_id=a.tenant_id,
            server_id=a.server_id,
            server_hostname=server.hostname if server else "Unknown Host",
            alert_type=a.alert_type,
            severity=a.severity,
            title=a.title,
            description=a.description,
            metric_name=a.metric_name,
            observed_value=a.observed_value,
            threshold_value=a.threshold_value,
            status=a.status,
            created_at=a.created_at,
            resolved_at=a.resolved_at
        ))
    return results

@router.patch("/{alert_id}")
def update_alert_status(
    alert_id: str,
    update: AlertStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    alert = db.query(Alert).filter(
        Alert.id == alert_id,
        Alert.tenant_id == current_user.tenant_id
    ).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.status = update.status
    if update.status == "resolved":
        alert.resolved_at = datetime.now(timezone.utc)
    db.commit()

    return {"status": "success", "alert_id": alert.id, "new_status": alert.status}
