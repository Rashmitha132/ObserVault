# backend/app/api/simulator.py
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.models import Collector, Tenant, Server, TelemetryRecord, User
from app.schemas.schemas import OutboundTelemetryRecord, TelemetryBatchIngest, PrivacySummary
from app.api.deps import get_current_user
from app.detection.anomaly_engine import run_anomaly_detection
from app.correlation.incident_correlator import run_incident_correlation
from app.recommendations.advisor import generate_recommendations

router = APIRouter()

class ScenarioTriggerRequest(BaseModel):
    scenario: str  # "normal", "high_cpu", "network_failure", "security_spike", "service_crash", "collector_offline", "reconnect_buffer"
    server_target: Optional[str] = "srv-prod-api-01"

@router.post("/scenario")
def trigger_scenario(
    req: ScenarioTriggerRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    tenant_id = current_user.tenant_id
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    collector = db.query(Collector).filter(Collector.tenant_id == tenant_id).first()
    if not collector:
        raise HTTPException(status_code=404, detail="No collector found for tenant")

    now = datetime.now(timezone.utc)
    scenario = req.scenario.lower()

    if scenario == "collector_offline":
        # Simulate collector heartbeat timeout
        collector.status = "offline"
        # Set last heartbeat back 120 seconds
        from datetime import timedelta
        collector.last_heartbeat = now - timedelta(seconds=120)
        db.commit()
        return {
            "status": "success",
            "scenario": "collector_offline",
            "message": f"Collector {collector.name} heartbeat suppressed (simulating network disconnect/crash)."
        }

    # Define scenario metric presets
    if scenario == "high_cpu":
        cpu = 96.8
        mem = 88.5
        disk = 62.0
        lat = 145.2
        loss = 0.0
        failed_logins = 0
        service_st = "degraded"
        server_name = req.server_target or "srv-prod-api-01"
    elif scenario == "network_failure":
        cpu = 32.1
        mem = 45.0
        disk = 40.0
        lat = 380.0
        loss = 18.5
        failed_logins = 0
        service_st = "degraded"
        server_name = req.server_target or "srv-edge-gateway-01"
    elif scenario == "security_spike":
        cpu = 72.4
        mem = 50.1
        disk = 48.0
        lat = 35.0
        loss = 0.0
        failed_logins = 12
        service_st = "up"
        server_name = req.server_target or "srv-auth-cluster-01"
    elif scenario == "service_crash":
        cpu = 15.0
        mem = 22.0
        disk = 91.5
        lat = 420.0
        loss = 25.0
        failed_logins = 0
        service_st = "down"
        server_name = req.server_target or "srv-db-primary-01"
    else:  # normal
        cpu = 28.4
        mem = 52.0
        disk = 44.5
        lat = 22.0
        loss = 0.0
        failed_logins = 0
        service_st = "up"
        server_name = req.server_target or "srv-prod-api-01"

    # Find or create server
    server = db.query(Server).filter(
        Server.tenant_id == tenant_id,
        Server.hostname == server_name
    ).first()

    if not server:
        server = Server(
            tenant_id=tenant_id,
            collector_id=collector.id,
            hostname=server_name,
            display_name=server_name.replace("-", " ").title(),
            ip_address="192.168.1.105",
            os_info="Ubuntu 24.04 LTS (x86_64)",
            status="healthy",
            service_status=service_st,
            last_cpu=cpu,
            last_memory=mem,
            last_disk=disk,
            last_latency=lat,
            last_packet_loss=loss,
            last_failed_logins=failed_logins,
            is_simulated=True,
            last_seen=now
        )
        db.add(server)
        db.flush()
    else:
        server.last_cpu = cpu
        server.last_memory = mem
        server.last_disk = disk
        server.last_latency = lat
        server.last_packet_loss = loss
        server.last_failed_logins = failed_logins
        server.service_status = service_st
        server.is_simulated = True
        server.last_seen = now

    event_id = str(uuid.uuid4())
    record = TelemetryRecord(
        tenant_id=tenant_id,
        collector_id=collector.id,
        server_id=server.id,
        event_id=event_id,
        timestamp=now,
        cpu_percent=cpu,
        memory_percent=mem,
        disk_percent=disk,
        network_latency_ms=lat,
        packet_loss_percent=loss,
        network_status="connected" if loss < 10 else "degraded",
        failed_login_count=failed_logins,
        service_status=service_st,
        is_simulated=True,
        raw_metadata_json=f'{{"event_id": "{event_id}", "is_simulated": true, "scenario": "{scenario}"}}'
    )
    db.add(record)
    db.flush()

    # Run detection, correlation, and recommendations
    run_anomaly_detection(db, record, tenant, server)
    run_incident_correlation(db, tenant)
    generate_recommendations(db, tenant)

    collector.last_successful_transmission = now
    collector.last_heartbeat = now
    collector.status = "online"

    db.commit()

    return {
        "status": "success",
        "scenario": scenario,
        "server": server.hostname,
        "metrics": {
            "cpu": cpu,
            "memory": mem,
            "disk": disk,
            "latency": lat,
            "packet_loss": loss,
            "failed_logins": failed_logins,
            "service_status": service_st
        },
        "message": f"Scenario '{scenario}' executed. Pipeline evaluated anomalies and correlated incidents."
    }
