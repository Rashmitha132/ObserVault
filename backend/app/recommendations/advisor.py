# backend/app/recommendations/advisor.py
import json
from datetime import datetime, timezone
from typing import List
from sqlalchemy.orm import Session
from app.models.models import Recommendation, Incident, Alert, Tenant

def generate_recommendations(db: Session, tenant: Tenant) -> List[Recommendation]:
    """
    Generates structured, safe recommendations for active incidents and alerts.
    Ensures human_approval_required is set to True to prevent accidental automatic modifications.
    """
    now = datetime.now(timezone.utc)
    new_recs = []

    # Process open incidents
    open_incidents = db.query(Incident).filter(
        Incident.tenant_id == tenant.id,
        Incident.status.in_(["open", "investigating"])
    ).all()

    for inc in open_incidents:
        existing = db.query(Recommendation).filter(
            Recommendation.tenant_id == tenant.id,
            Recommendation.incident_id == inc.id,
            Recommendation.status == "pending"
        ).first()

        if existing:
            continue

        raw_actions = json.loads(inc.recommended_actions_json or "[]")
        category = "security" if "SEC" in inc.incident_code else "infrastructure" if "RES" in inc.incident_code else "network"
        
        rec = Recommendation(
            tenant_id=tenant.id,
            incident_id=inc.id,
            severity=inc.severity,
            category=category,
            title=f"Action Plan for {inc.title}",
            description=f"Recommended protocol to remediate root causes identified in incident {inc.incident_code}.",
            rationale=inc.possible_cause,
            action_steps_json=json.dumps(raw_actions),
            human_approval_required=True,
            status="pending",
            created_at=now
        )
        db.add(rec)
        new_recs.append(rec)

    # Process standalone critical alerts that may not yet be in an incident
    critical_alerts = db.query(Alert).filter(
        Alert.tenant_id == tenant.id,
        Alert.status == "active",
        Alert.severity == "critical"
    ).all()

    for alert in critical_alerts:
        existing_alert_rec = db.query(Recommendation).filter(
            Recommendation.tenant_id == tenant.id,
            Recommendation.alert_id == alert.id,
            Recommendation.status == "pending"
        ).first()

        if existing_alert_rec:
            continue

        steps = [
            f"Review server logs locally on the target host for {alert.metric_name} triggers.",
            "Verify dependencies and upstream database/network connectivity.",
            "Confirm service health and auto-restart policy."
        ]
        
        rec = Recommendation(
            tenant_id=tenant.id,
            alert_id=alert.id,
            severity="critical",
            category="reliability",
            title=f"Urgent Attention Required: {alert.title}",
            description=alert.description,
            rationale=f"Observed metric {alert.metric_name} is {alert.observed_value}, exceeding critical limit {alert.threshold_value}.",
            action_steps_json=json.dumps(steps),
            human_approval_required=True,
            status="pending",
            created_at=now
        )
        db.add(rec)
        db.flush()
        new_recs.append(rec)

    # Return all pending recommendations for this tenant
    return db.query(Recommendation).filter(
        Recommendation.tenant_id == tenant.id,
        Recommendation.status == "pending"
    ).all()
