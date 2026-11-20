# backend/app/api/recommendations.py
import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.models import Recommendation, User
from app.schemas.schemas import RecommendationOut, RecommendationStatusUpdate
from app.api.deps import get_current_user

router = APIRouter()

@router.get("", response_model=List[RecommendationOut])
def list_recommendations(
    severity: Optional[str] = Query(None, description="critical, high, medium, informational"),
    status: Optional[str] = Query(None, description="pending, acknowledged, completed, dismissed"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Recommendation).filter(Recommendation.tenant_id == current_user.tenant_id)
    if severity:
        query = query.filter(Recommendation.severity == severity)
    if status:
        query = query.filter(Recommendation.status == status)

    recs = query.order_by(Recommendation.created_at.desc()).all()
    results = []
    for r in recs:
        steps = json.loads(r.action_steps_json or "[]")
        results.append(RecommendationOut(
            id=r.id,
            tenant_id=r.tenant_id,
            incident_id=r.incident_id,
            alert_id=r.alert_id,
            severity=r.severity,
            category=r.category,
            title=r.title,
            description=r.description,
            rationale=r.rationale,
            action_steps=steps,
            human_approval_required=r.human_approval_required,
            status=r.status,
            created_at=r.created_at
        ))
    return results

@router.patch("/{recommendation_id}")
def update_recommendation(
    recommendation_id: str,
    update: RecommendationStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    rec = db.query(Recommendation).filter(
        Recommendation.id == recommendation_id,
        Recommendation.tenant_id == current_user.tenant_id
    ).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")

    rec.status = update.status
    db.commit()
    return {"status": "success", "recommendation_id": rec.id, "new_status": rec.status}
