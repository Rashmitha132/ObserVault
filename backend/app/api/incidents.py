# backend/app/api/incidents.py
import json
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.models import Incident, Alert, Server, User
from app.schemas.schemas import IncidentOut, IncidentStatusUpdate, AlertOut
from app.api.deps import get_current_user

router = APIRouter()

@router.get("", response_model=List[IncidentOut])
def list_incidents(
    status: Optional[str] = Query(None, description="open, investigating, acknowledged, resolved"),
    severity: Optional[str] = Query(None, description="critical, high, medium, low"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Incident).filter(Incident.tenant_id == current_user.tenant_id)
    if status:
        query = query.filter(Incident.status == status)
    if severity:
        query = query.filter(Incident.severity == severity)

    incidents = query.order_by(Incident.created_at.desc()).all()
    results = []
    for inc in incidents:
        server = db.query(Server).filter(Server.id == inc.primary_server_id).first() if inc.primary_server_id else None
        
        # Load related alerts
        related_alerts_out = []
        for a in inc.alerts:
            a_server = db.query(Server).filter(Server.id == a.server_id).first()
            related_alerts_out.append(AlertOut(
                id=a.id,
                tenant_id=a.tenant_id,
                server_id=a.server_id,
                server_hostname=a_server.hostname if a_server else None,
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

        actions = json.loads(inc.recommended_actions_json or "[]")

        results.append(IncidentOut(
            id=inc.id,
            tenant_id=inc.tenant_id,
            incident_code=inc.incident_code,
            title=inc.title,
            severity=inc.severity,
            status=inc.status,
            primary_server_id=inc.primary_server_id,
            primary_server_name=server.display_name if server else None,
            possible_cause=inc.possible_cause,
            confidence_score=inc.confidence_score,
            evidence_summary=inc.evidence_summary,
            recommended_actions=actions,
            related_alerts=related_alerts_out,
            created_at=inc.created_at,
            updated_at=inc.updated_at,
            resolved_at=inc.resolved_at
        ))
    return results

@router.get("/{incident_id}", response_model=IncidentOut)
def get_incident(
    incident_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    inc = db.query(Incident).filter(
        Incident.id == incident_id,
        Incident.tenant_id == current_user.tenant_id
    ).first()
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")

    server = db.query(Server).filter(Server.id == inc.primary_server_id).first() if inc.primary_server_id else None
    
    related_alerts_out = []
    for a in inc.alerts:
        a_server = db.query(Server).filter(Server.id == a.server_id).first()
        related_alerts_out.append(AlertOut(
            id=a.id,
            tenant_id=a.tenant_id,
            server_id=a.server_id,
            server_hostname=a_server.hostname if a_server else None,
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

    actions = json.loads(inc.recommended_actions_json or "[]")

    return IncidentOut(
        id=inc.id,
        tenant_id=inc.tenant_id,
        incident_code=inc.incident_code,
        title=inc.title,
        severity=inc.severity,
        status=inc.status,
        primary_server_id=inc.primary_server_id,
        primary_server_name=server.display_name if server else None,
        possible_cause=inc.possible_cause,
        confidence_score=inc.confidence_score,
        evidence_summary=inc.evidence_summary,
        recommended_actions=actions,
        related_alerts=related_alerts_out,
        created_at=inc.created_at,
        updated_at=inc.updated_at,
        resolved_at=inc.resolved_at
    )

@router.patch("/{incident_id}")
def update_incident_status(
    incident_id: str,
    update: IncidentStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    inc = db.query(Incident).filter(
        Incident.id == incident_id,
        Incident.tenant_id == current_user.tenant_id
    ).first()
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")

    inc.status = update.status
    inc.updated_at = datetime.now(timezone.utc)
    if update.status == "resolved":
        inc.resolved_at = datetime.now(timezone.utc)
        # Also mark associated alerts resolved
        for a in inc.alerts:
            a.status = "resolved"
            a.resolved_at = datetime.now(timezone.utc)
    db.commit()

    return {"status": "success", "incident_id": inc.id, "new_status": inc.status}
