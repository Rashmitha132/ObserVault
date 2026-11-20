# backend/app/api/tenant.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.models import Tenant, User, Collector
from app.schemas.schemas import TenantSettingsUpdate
from app.api.deps import get_current_user

router = APIRouter()

@router.get("/settings")
def get_tenant_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    users = db.query(User).filter(User.tenant_id == tenant.id).all()
    collectors = db.query(Collector).filter(Collector.tenant_id == tenant.id).all()

    return {
        "tenant": {
            "id": tenant.id,
            "name": tenant.name,
            "slug": tenant.slug,
            "plan": tenant.plan,
            "thresholds": {
                "cpu_threshold": tenant.cpu_threshold,
                "memory_threshold": tenant.memory_threshold,
                "disk_threshold": tenant.disk_threshold,
                "latency_threshold_ms": tenant.latency_threshold_ms,
                "packet_loss_threshold": tenant.packet_loss_threshold,
                "failed_login_threshold": tenant.failed_login_threshold
            },
            "created_at": tenant.created_at.isoformat()
        },
        "users": [
            {
                "id": u.id,
                "email": u.email,
                "full_name": u.full_name,
                "role": u.role,
                "is_active": u.is_active,
                "created_at": u.created_at.isoformat()
            } for u in users
        ],
        "collectors_count": len(collectors)
    }

@router.patch("/settings")
def update_tenant_thresholds(
    update: TenantSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    if update.cpu_threshold is not None:
        tenant.cpu_threshold = update.cpu_threshold
    if update.memory_threshold is not None:
        tenant.memory_threshold = update.memory_threshold
    if update.disk_threshold is not None:
        tenant.disk_threshold = update.disk_threshold
    if update.latency_threshold_ms is not None:
        tenant.latency_threshold_ms = update.latency_threshold_ms
    if update.packet_loss_threshold is not None:
        tenant.packet_loss_threshold = update.packet_loss_threshold
    if update.failed_login_threshold is not None:
        tenant.failed_login_threshold = update.failed_login_threshold

    db.commit()
    return {
        "status": "success",
        "message": "Tenant anomaly thresholds updated successfully",
        "thresholds": {
            "cpu_threshold": tenant.cpu_threshold,
            "memory_threshold": tenant.memory_threshold,
            "disk_threshold": tenant.disk_threshold,
            "latency_threshold_ms": tenant.latency_threshold_ms,
            "packet_loss_threshold": tenant.packet_loss_threshold,
            "failed_login_threshold": tenant.failed_login_threshold
        }
    }
