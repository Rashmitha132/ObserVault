# backend/app/api/integrations.py
"""
ObserVault Real Infrastructure Integrations Endpoints (Phase 2E).
Provides real host telemetry capture, Docker engine probe, PostgreSQL probe,
and integration catalog management.
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.models import User, IntegrationConfig
from app.schemas.schemas import IntegrationOut, RealHostTelemetryResponse
from app.integrations.manager import IntegrationManager

router = APIRouter(prefix="/v2/integrations", tags=["Real Infrastructure Integrations"])

@router.get("", response_model=List[IntegrationOut])
def list_integrations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns the tenant's integration catalog, including connection health
    and clear indicators separating Real vs. Simulated telemetry.
    """
    integrations = IntegrationManager.get_or_seed_integrations(
        db=db,
        tenant_id=current_user.tenant_id
    )
    return integrations


@router.get("/real-host", response_model=RealHostTelemetryResponse)
def get_live_real_host_telemetry(
    current_user: User = Depends(get_current_user)
):
    """
    Captures live, authentic host machine metrics (CPU, RAM, Disk, Network) via psutil.
    Guaranteed: is_simulated is False.
    """
    telemetry = IntegrationManager.capture_real_host_telemetry()
    return telemetry


@router.get("/docker-status")
def get_docker_engine_status(
    current_user: User = Depends(get_current_user)
):
    """
    Probes local Docker daemon for container telemetry.
    Returns status: connected or disconnected with diagnostic explanation.
    """
    docker_data = IntegrationManager.probe_docker_status()
    return docker_data


@router.post("/test/{integration_type}")
def test_integration_connectivity(
    integration_type: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Tests live connection to specified infrastructure target.
    """
    if integration_type in ("windows_host", "linux_host"):
        data = IntegrationManager.capture_real_host_telemetry()
        return {
            "integration_type": integration_type,
            "connected": True,
            "message": "Host kernel probe succeeded.",
            "metrics": data
        }
    elif integration_type == "docker":
        data = IntegrationManager.probe_docker_status()
        return {
            "integration_type": "docker",
            "connected": data["docker_available"],
            "message": "Docker engine probe completed.",
            "detail": data
        }
    elif integration_type == "postgres_db":
        data = IntegrationManager.probe_postgres_status()
        return {
            "integration_type": "postgres_db",
            "connected": data["port_accessible"],
            "message": "PostgreSQL port probe completed.",
            "detail": data
        }
    elif integration_type == "nginx_proxy":
        data = IntegrationManager.probe_nginx_status()
        return {
            "integration_type": "nginx_proxy",
            "connected": data["port_accessible"],
            "message": "Nginx port probe completed.",
            "detail": data
        }
    elif integration_type == "fastapi_app":
        data = IntegrationManager.probe_fastapi_status()
        return {
            "integration_type": "fastapi_app",
            "connected": True,
            "message": "FastAPI internal telemetry stream active.",
            "detail": data
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown integration type: {integration_type}"
        )
