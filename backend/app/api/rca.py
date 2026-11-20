# backend/app/api/rca.py
"""
ObserVault Root Cause Analysis (RCA) API Endpoints.
Provides incident-level causal ranking, chronological event timelines,
blast-radius topology tracking, and evidence-based investigation workflows.
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.models import User, Incident, ServiceNode, ServiceDependency
from app.correlation.rca_engine import RootCauseAnalysisEngine

router = APIRouter(prefix="/v2/rca", tags=["Root Cause Analysis (RCA)"])

@router.get("/incidents")
def list_rca_incidents(
    status_filter: Optional[str] = Query(None),
    severity_filter: Optional[str] = Query(None),
    limit: int = Query(25, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns active and historical incidents with high-level RCA summaries.
    """
    query = db.query(Incident).filter(Incident.tenant_id == current_user.tenant_id)

    if status_filter:
        query = query.filter(Incident.status == status_filter)
    if severity_filter:
        query = query.filter(Incident.severity == severity_filter)

    incidents = query.order_by(Incident.created_at.desc()).limit(limit).all()

    results = []
    for inc in incidents:
        # Quick summary of top candidate
        analysis = RootCauseAnalysisEngine.analyze_incident(
            db=db,
            tenant_id=current_user.tenant_id,
            incident_id=inc.id
        )
        top_cand = analysis.get("primary_root_cause_hypothesis")
        blast = analysis.get("blast_radius", {})

        results.append({
            "incident_id": inc.id,
            "incident_code": inc.incident_code,
            "title": inc.title,
            "severity": inc.severity,
            "status": inc.status,
            "created_at": inc.created_at.isoformat(),
            "primary_suspect": top_cand.get("name") if top_cand else "Unknown",
            "root_cause_confidence": top_cand.get("confidence_percent") if top_cand else int(inc.confidence_score * 100),
            "affected_services_count": blast.get("total_services_impacted", 0),
            "evidence_count": len(top_cand.get("supporting_evidence", [])) if top_cand else 0
        })

    return results

@router.get("/incidents/{incident_id}")
def get_incident_rca(
    incident_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns full, deep Root Cause Analysis for a specific incident:
    - Ranked root-cause candidates with evidence and confidence scores
    - Chronological incident timeline
    - Blast-radius propagation paths
    - Advisory investigation next steps
    """
    incident = db.query(Incident).filter(
        Incident.id == incident_id,
        Incident.tenant_id == current_user.tenant_id
    ).first()

    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident with ID '{incident_id}' not found."
        )

    analysis = RootCauseAnalysisEngine.analyze_incident(
        db=db,
        tenant_id=current_user.tenant_id,
        incident_id=incident_id
    )

    return analysis

@router.get("/blast-radius/{component_name}")
def get_component_blast_radius(
    component_name: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Calculates downstream and upstream blast radius for any individual service or component.
    """
    services = db.query(ServiceNode).filter(ServiceNode.tenant_id == current_user.tenant_id).all()
    dependencies = db.query(ServiceDependency).filter(ServiceDependency.tenant_id == current_user.tenant_id).all()

    report = RootCauseAnalysisEngine._compute_blast_radius(
        suspected_component=component_name,
        services=services,
        dependencies=dependencies,
        component_signals={}
    )

    return report
