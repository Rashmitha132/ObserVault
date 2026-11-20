# backend/app/api/predictive.py
"""
ObserVault Predictive Analytics & Capacity Planning Endpoints (Phase 2E).
Provides resource forecasting, capacity warnings, and SLO / error budget monitoring.
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.models import User, Server, ServiceLevelObjective, CapacityWarning
from app.schemas.schemas import (
    ResourceForecastResponse, CapacityWarningOut, SLOOut, SLOCreateRequest
)
from app.detection.predictive_engine import PredictiveEngine

router = APIRouter(prefix="/v2/predictive", tags=["Predictive Analytics & Capacity Forecasting"])

@router.get("/forecast/{server_id}", response_model=ResourceForecastResponse)
def get_resource_forecast(
    server_id: str,
    metric_name: str = Query("disk_percent", pattern="^(disk_percent|memory_percent|cpu_percent|network_latency_ms|packet_loss_percent|throughput_rpm|latency_ms)$"),
    horizon: str = Query("7d"),
    horizon_days: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Computes statistical resource forecast for the given server and metric over a chosen horizon (15m, 1h, 24h, 7d, 14d, 30d).
    Returns 95% confidence intervals, daily velocity, estimated threshold breach date, and out-of-sample MAE/RMSE validation.
    """
    server = db.query(Server).filter(
        Server.id == server_id,
        Server.tenant_id == current_user.tenant_id
    ).first()

    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Server with ID {server_id} not found in current tenant."
        )

    # Use horizon_days if explicitly passed, otherwise use horizon string
    effective_horizon = f"{horizon_days}d" if horizon_days is not None else horizon

    forecast_data = PredictiveEngine.generate_server_forecast(
        db=db,
        tenant_id=current_user.tenant_id,
        server_id=server_id,
        metric_name=metric_name,
        horizon=effective_horizon
    )

    return forecast_data


@router.get("/capacity-warnings", response_model=List[CapacityWarningOut])
def get_capacity_warnings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns active capacity warnings across all tenant infrastructure,
    including estimated days to exhaustion and proactive mitigation recommendations.
    """
    warnings = PredictiveEngine.evaluate_active_capacity_warnings(
        db=db,
        tenant_id=current_user.tenant_id
    )
    return warnings


@router.get("/slo", response_model=List[SLOOut])
def get_slo_metrics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Calculates Service Level Objective (SLO) attainments, remaining Error Budgets,
    and consumption Burn Rates for the tenant.
    """
    slo_data = PredictiveEngine.compute_slo_metrics(
        db=db,
        tenant_id=current_user.tenant_id
    )
    return slo_data


@router.post("/slo", response_model=SLOOut, status_code=status.HTTP_201_CREATED)
def create_custom_slo(
    slo_in: SLOCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Configures a new Service Level Objective (SLO) target for a tenant microservice.
    """
    new_slo = ServiceLevelObjective(
        tenant_id=current_user.tenant_id,
        name=slo_in.name,
        service_name=slo_in.service_name,
        sli_type=slo_in.sli_type,
        target_percentage=slo_in.target_percentage,
        warning_threshold=slo_in.warning_threshold,
        latency_threshold_ms=slo_in.latency_threshold_ms or 250.0,
        rolling_window_days=slo_in.rolling_window_days
    )
    db.add(new_slo)
    db.commit()
    db.refresh(new_slo)

    # Recompute metrics with the new SLO included
    metrics = PredictiveEngine.compute_slo_metrics(
        db=db,
        tenant_id=current_user.tenant_id
    )
    matching = next((m for m in metrics if m["id"] == new_slo.id), None)
    if matching:
        return matching
    return new_slo
