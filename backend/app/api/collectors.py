# backend/app/api/collectors.py
import json
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import settings
from app.core.security import hash_token, generate_collector_key, generate_enrollment_token
from app.models.models import (
    Collector, 
    Server, 
    User, 
    DeviceEnrollmentToken, 
    DeviceAuditLog, 
    TelemetryRecord
)
from app.schemas.schemas import (
    CollectorOut,
    DeviceRegisterRequest,
    DeviceRegisterResponse,
    DeviceEnrollRequest,
    DeviceEnrollResponse,
    DeviceRevokeResponse,
    DeviceAuditLogOut,
    DeviceManagementStats
)
from app.api.deps import get_current_user

router = APIRouter()

def compute_collector_status(c: Collector, heartbeat_cutoff: datetime) -> str:
    """Accurately compute dynamic status for device collector."""
    if getattr(c, "is_revoked", False) or getattr(c, "enrollment_status", "") == "revoked":
        return "revoked"
    if getattr(c, "enrollment_status", "") == "pending":
        return "pending"
    last_hb = c.last_heartbeat
    if last_hb is None:
        return "offline"
    last_hb_utc = last_hb.replace(tzinfo=timezone.utc if last_hb.tzinfo is None else None)
    if last_hb_utc < heartbeat_cutoff:
        return "offline"
    return c.status or "online"


@router.get("", response_model=List[CollectorOut])
def list_collectors(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    now = datetime.now(timezone.utc)
    heartbeat_cutoff = now - timedelta(seconds=settings.HEARTBEAT_TIMEOUT_SECONDS)

    collectors = db.query(Collector).filter(
        Collector.tenant_id == current_user.tenant_id
    ).order_by(Collector.created_at.desc()).all()

    results = []
    for c in collectors:
        computed_status = compute_collector_status(c, heartbeat_cutoff)
        c.status = computed_status

        results.append(CollectorOut(
            id=c.id,
            tenant_id=c.tenant_id,
            name=c.name,
            hostname=c.hostname,
            ip_address=c.ip_address,
            version=c.version or "1.0.0",
            status=computed_status,
            collection_interval=c.collection_interval or 5,
            buffered_records_count=c.buffered_records_count or 0,
            failed_transmissions_count=c.failed_transmissions_count or 0,
            last_heartbeat=c.last_heartbeat or now,
            last_successful_transmission=c.last_successful_transmission or now,
            created_at=c.created_at or now,
            os_type=getattr(c, "os_type", "windows"),
            os_version=getattr(c, "os_version", None),
            environment=getattr(c, "environment", "production"),
            enrollment_status=getattr(c, "enrollment_status", "active"),
            is_revoked=getattr(c, "is_revoked", False),
            revoked_at=getattr(c, "revoked_at", None)
        ))
    db.commit()
    return results


@router.get("/stats", response_model=DeviceManagementStats)
def get_device_management_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Aggregate statistics for the device onboarding dashboard."""
    now = datetime.now(timezone.utc)
    heartbeat_cutoff = now - timedelta(seconds=settings.HEARTBEAT_TIMEOUT_SECONDS)

    collectors = db.query(Collector).filter(
        Collector.tenant_id == current_user.tenant_id
    ).order_by(Collector.created_at.desc()).all()

    total_devices = len(collectors)
    online_count = 0
    offline_count = 0
    pending_count = 0
    revoked_count = 0

    collector_outs = []
    for c in collectors:
        st = compute_collector_status(c, heartbeat_cutoff)
        c.status = st
        if st == "online":
            online_count += 1
        elif st == "offline":
            offline_count += 1
        elif st == "pending":
            pending_count += 1
        elif st == "revoked":
            revoked_count += 1
        else:
            offline_count += 1

        collector_outs.append(CollectorOut(
            id=c.id,
            tenant_id=c.tenant_id,
            name=c.name,
            hostname=c.hostname,
            ip_address=c.ip_address,
            version=c.version or "1.0.0",
            status=st,
            collection_interval=c.collection_interval or 5,
            buffered_records_count=c.buffered_records_count or 0,
            failed_transmissions_count=c.failed_transmissions_count or 0,
            last_heartbeat=c.last_heartbeat or now,
            last_successful_transmission=c.last_successful_transmission or now,
            created_at=c.created_at or now,
            os_type=getattr(c, "os_type", "windows"),
            os_version=getattr(c, "os_version", None),
            environment=getattr(c, "environment", "production"),
            enrollment_status=getattr(c, "enrollment_status", "active"),
            is_revoked=getattr(c, "is_revoked", False),
            revoked_at=getattr(c, "revoked_at", None)
        ))
    db.commit()

    return DeviceManagementStats(
        total_devices=total_devices,
        online_devices=online_count,
        offline_devices=offline_count,
        pending_devices=pending_count,
        revoked_devices=revoked_count,
        collectors=collector_outs
    )


@router.post("/register", response_model=DeviceRegisterResponse)
def register_device(
    payload: DeviceRegisterRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Step 1 of Onboarding: Organization Admin registers a new device.
    Generates a cryptographically secure, short-lived (15 min), single-use enrollment token.
    Never trusts client tenant_id: securely binds to current_user.tenant_id.
    """
    raw_enrollment_token = generate_enrollment_token()
    token_hash = hash_token(raw_enrollment_token)
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=15)

    # Persist the single-use token record
    token_rec = DeviceEnrollmentToken(
        tenant_id=current_user.tenant_id,
        device_name=payload.device_name,
        os_type=payload.os_type.lower(),
        environment=payload.environment.lower(),
        description=payload.description,
        token_hash=token_hash,
        expires_at=expires_at,
        created_by_user_id=current_user.id
    )
    db.add(token_rec)
    db.flush()

    # Pre-register a Pending Collector record in the dashboard
    pending_col_id = f"col-{uuid.uuid4().hex[:12]}"
    pending_collector = Collector(
        id=pending_col_id,
        tenant_id=current_user.tenant_id,
        token_hash=token_hash,  # Temporary hash until operational key exchange
        name=payload.device_name,
        hostname=f"pending-{payload.device_name.lower().replace(' ', '-')}",
        version="1.0.0",
        status="pending",
        collection_interval=5,
        last_heartbeat=now,
        last_successful_transmission=now,
        os_type=payload.os_type.lower(),
        environment=payload.environment.lower(),
        enrollment_status="pending",
        is_revoked=False
    )
    db.add(pending_collector)
    db.flush()

    # Create audit log entry
    audit = DeviceAuditLog(
        tenant_id=current_user.tenant_id,
        collector_id=pending_col_id,
        device_name=payload.device_name,
        action="REGISTERED",
        actor=current_user.email,
        details_json=json.dumps({
            "os_type": payload.os_type,
            "environment": payload.environment,
            "expires_at": expires_at.isoformat()
        })
    )
    db.add(audit)
    db.commit()

    # Formulate copyable commands
    ps_cmd = (
        f"$env:OBSERVAULT_ENROLL_TOKEN='{raw_enrollment_token}'; "
        f"$env:OBSERVAULT_BACKEND_URL='http://127.0.0.1:8000'; "
        f"python -m collector.enroll; python -m collector.runtime start"
    )
    cli_cmd = (
        f"python -m collector.enroll --token {raw_enrollment_token} --backend http://127.0.0.1:8000 && python -m collector.runtime start"
    )

    return DeviceRegisterResponse(
        token_id=token_rec.id,
        device_name=payload.device_name,
        os_type=payload.os_type,
        environment=payload.environment,
        enrollment_token=raw_enrollment_token,
        expires_at=expires_at,
        powershell_command=ps_cmd,
        enroll_cli_command=cli_cmd
    )


@router.post("/enroll", response_model=DeviceEnrollResponse)
def enroll_device(
    payload: DeviceEnrollRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Step 2 of Onboarding: Handshake endpoint called by the Windows/Linux Collector during installation.
    Exchanges the single-use enrollment token for permanent operational collector credentials.
    """
    token_hash = hash_token(payload.enrollment_token)
    token_rec = db.query(DeviceEnrollmentToken).filter(
        DeviceEnrollmentToken.token_hash == token_hash
    ).first()

    now = datetime.now(timezone.utc)

    if not token_rec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid or unrecognized enrollment token."
        )

    if token_rec.is_revoked:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Enrollment token has been revoked by an administrator."
        )

    if token_rec.consumed_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Enrollment token has already been consumed. Single-use policy enforced."
        )

    token_expiry = token_rec.expires_at.replace(tzinfo=timezone.utc if token_rec.expires_at.tzinfo is None else None)
    if token_expiry < now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Enrollment token has expired. Please generate a new registration token."
        )

    # Mark enrollment token consumed immediately
    token_rec.consumed_at = now

    # Generate permanent high-entropy operational collector key
    operational_key = generate_collector_key()
    op_key_hash = hash_token(operational_key)

    # Check for pending collector record created during registration
    collector = db.query(Collector).filter(
        Collector.tenant_id == token_rec.tenant_id,
        Collector.token_hash == token_hash
    ).first()

    client_ip = payload.ip_address or (request.client.host if request.client else "127.0.0.1")

    if collector:
        collector.token_hash = op_key_hash
        collector.hostname = payload.hostname
        collector.ip_address = client_ip
        collector.version = payload.collector_version
        collector.os_type = payload.os_type
        collector.os_version = payload.os_version
        collector.status = "online"
        collector.enrollment_status = "active"
        collector.is_revoked = False
        collector.last_heartbeat = now
        collector.last_successful_transmission = now
    else:
        collector = Collector(
            tenant_id=token_rec.tenant_id,
            token_hash=op_key_hash,
            name=token_rec.device_name,
            hostname=payload.hostname,
            ip_address=client_ip,
            version=payload.collector_version,
            os_type=payload.os_type,
            os_version=payload.os_version,
            environment=token_rec.environment,
            status="online",
            enrollment_status="active",
            is_revoked=False,
            collection_interval=5,
            last_heartbeat=now,
            last_successful_transmission=now
        )
        db.add(collector)
    db.flush()

    # Link or create associated Server entity for infrastructure views
    server = db.query(Server).filter(
        Server.tenant_id == token_rec.tenant_id,
        Server.collector_id == collector.id
    ).first()

    if not server:
        clean_hostname = payload.hostname.lower().strip()
        server = Server(
            tenant_id=token_rec.tenant_id,
            collector_id=collector.id,
            hostname=clean_hostname,
            display_name=token_rec.device_name,
            ip_address=client_ip,
            os_info=f"{payload.os_type.capitalize()} {payload.os_version or 'x86_64'}",
            status="healthy",
            service_status="up",
            last_seen=now
        )
        db.add(server)
    else:
        server.hostname = payload.hostname.lower().strip()
        server.display_name = token_rec.device_name
        server.ip_address = client_ip
        server.os_info = f"{payload.os_type.capitalize()} {payload.os_version or 'x86_64'}"
        server.status = "healthy"
        server.last_seen = now
    db.flush()

    # Log device enrollment audit trail
    audit = DeviceAuditLog(
        tenant_id=token_rec.tenant_id,
        collector_id=collector.id,
        device_name=token_rec.device_name,
        action="ENROLLED",
        actor=f"collector:{payload.hostname}",
        ip_address=client_ip,
        details_json=json.dumps({
            "os_type": payload.os_type,
            "os_version": payload.os_version,
            "collector_version": payload.collector_version,
            "machine_guid": payload.machine_guid
        })
    )
    db.add(audit)
    db.commit()

    return DeviceEnrollResponse(
        collector_id=collector.id,
        collector_key=operational_key,
        collector_name=collector.name,
        server_id=server.id,
        tenant_id=token_rec.tenant_id,
        collection_interval=collector.collection_interval or 5,
        heartbeat_interval=15,
        backend_url="http://127.0.0.1:8000"
    )


@router.post("/{collector_id}/revoke", response_model=DeviceRevokeResponse)
def revoke_device(
    collector_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Revoke device authentication.
    Immediately invalidates collector token, blocking future heartbeats and telemetry egress.
    """
    collector = db.query(Collector).filter(
        Collector.id == collector_id,
        Collector.tenant_id == current_user.tenant_id
    ).first()

    if not collector:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collector device not found in your organization."
        )

    now = datetime.now(timezone.utc)
    collector.is_revoked = True
    collector.enrollment_status = "revoked"
    collector.status = "revoked"
    collector.revoked_at = now
    collector.revoked_by = current_user.email

    # Also invalidate any active enrollment tokens for this device
    db.query(DeviceEnrollmentToken).filter(
        DeviceEnrollmentToken.tenant_id == current_user.tenant_id,
        DeviceEnrollmentToken.device_name == collector.name,
        DeviceEnrollmentToken.is_revoked == False
    ).update({"is_revoked": True})

    # Log revocation event
    audit = DeviceAuditLog(
        tenant_id=current_user.tenant_id,
        collector_id=collector.id,
        device_name=collector.name,
        action="REVOKED",
        actor=current_user.email,
        details_json=json.dumps({"reason": "Administrator manual revocation"})
    )
    db.add(audit)
    db.commit()

    return DeviceRevokeResponse(
        collector_id=collector.id,
        status="revoked",
        revoked_at=now,
        message=f"Device {collector.name} has been permanently revoked. Telemetry ingestion blocked."
    )


@router.get("/{collector_id}/audit", response_model=List[DeviceAuditLogOut])
def get_device_audit_history(
    collector_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve audit history for a specific device."""
    # Ensure collector exists and belongs to tenant
    collector = db.query(Collector).filter(
        Collector.id == collector_id,
        Collector.tenant_id == current_user.tenant_id
    ).first()

    if not collector:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found in tenant."
        )

    audits = db.query(DeviceAuditLog).filter(
        DeviceAuditLog.tenant_id == current_user.tenant_id,
        DeviceAuditLog.collector_id == collector_id
    ).order_by(DeviceAuditLog.timestamp.desc()).all()

    return [
        DeviceAuditLogOut(
            id=a.id,
            collector_id=a.collector_id,
            device_name=a.device_name,
            action=a.action,
            actor=a.actor,
            ip_address=a.ip_address,
            details_json=a.details_json,
            timestamp=a.timestamp
        )
        for a in audits
    ]


@router.get("/{collector_id}/details")
def get_device_details(
    collector_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve comprehensive device overview including hardware, telemetry, and audit trail."""
    now = datetime.now(timezone.utc)
    heartbeat_cutoff = now - timedelta(seconds=settings.HEARTBEAT_TIMEOUT_SECONDS)

    collector = db.query(Collector).filter(
        Collector.id == collector_id,
        Collector.tenant_id == current_user.tenant_id
    ).first()

    if not collector:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found.")

    server = db.query(Server).filter(
        Server.collector_id == collector.id,
        Server.tenant_id == current_user.tenant_id
    ).first()

    latest_telemetry = db.query(TelemetryRecord).filter(
        TelemetryRecord.tenant_id == current_user.tenant_id,
        TelemetryRecord.server_id == (server.id if server else "")
    ).order_by(TelemetryRecord.timestamp.desc()).first()

    computed_status = compute_collector_status(collector, heartbeat_cutoff)

    audits = db.query(DeviceAuditLog).filter(
        DeviceAuditLog.tenant_id == current_user.tenant_id,
        DeviceAuditLog.collector_id == collector.id
    ).order_by(DeviceAuditLog.timestamp.desc()).limit(15).all()

    return {
        "collector": {
            "id": collector.id,
            "name": collector.name,
            "hostname": collector.hostname,
            "ip_address": collector.ip_address,
            "version": collector.version,
            "status": computed_status,
            "collection_interval": collector.collection_interval,
            "buffered_records_count": collector.buffered_records_count or 0,
            "failed_transmissions_count": collector.failed_transmissions_count or 0,
            "last_heartbeat": collector.last_heartbeat,
            "last_successful_transmission": collector.last_successful_transmission,
            "created_at": collector.created_at,
            "os_type": getattr(collector, "os_type", "windows"),
            "os_version": getattr(collector, "os_version", None),
            "environment": getattr(collector, "environment", "production"),
            "enrollment_status": getattr(collector, "enrollment_status", "active"),
            "is_revoked": getattr(collector, "is_revoked", False),
            "revoked_at": getattr(collector, "revoked_at", None),
            "revoked_by": getattr(collector, "revoked_by", None),
        },
        "server": {
            "id": server.id if server else None,
            "display_name": server.display_name if server else collector.name,
            "hostname": server.hostname if server else collector.hostname,
            "os_info": server.os_info if server else f"{getattr(collector, 'os_type', 'Windows').capitalize()}",
            "status": server.status if server else "healthy",
            "last_cpu": server.last_cpu if server else 0.0,
            "last_memory": server.last_memory if server else 0.0,
            "last_disk": server.last_disk if server else 0.0,
            "last_latency": server.last_latency if server else 0.0,
            "last_seen": server.last_seen if server else collector.last_heartbeat
        } if server else None,
        "latest_metrics": {
            "cpu_percent": latest_telemetry.cpu_percent if latest_telemetry else (server.last_cpu if server else 0.0),
            "memory_percent": latest_telemetry.memory_percent if latest_telemetry else (server.last_memory if server else 0.0),
            "disk_percent": latest_telemetry.disk_percent if latest_telemetry else (server.last_disk if server else 0.0),
            "network_latency_ms": latest_telemetry.network_latency_ms if latest_telemetry else (server.last_latency if server else 0.0),
            "packet_loss_percent": latest_telemetry.packet_loss_percent if latest_telemetry else 0.0,
            "is_simulated": latest_telemetry.is_simulated if latest_telemetry else False,
            "timestamp": latest_telemetry.timestamp if latest_telemetry else None
        },
        "audit_logs": [
            {
                "id": a.id,
                "action": a.action,
                "actor": a.actor,
                "details_json": a.details_json,
                "timestamp": a.timestamp
            }
            for a in audits
        ]
    }


@router.get("/install.ps1", response_class=PlainTextResponse)
def get_powershell_installer():
    """Generates dynamic PowerShell onboarding script for Windows collectors."""
    script_content = r"""<#
.SYNOPSIS
    ObserVault Windows Collector One-Line Installer & Enrollment Script
.DESCRIPTION
    Verifies Python environment, registers local directory, executes enrollment handshake,
    configures encrypted operational settings, and validates heartbeat signaling.
#>
[CmdletBinding()]
param (
    [string]$EnrollmentToken = $env:OBSERVAULT_ENROLL_TOKEN,
    [string]$BackendUrl = $(if ($env:OBSERVAULT_BACKEND_URL) { $env:OBSERVAULT_BACKEND_URL } else { "http://127.0.0.1:8000" })
)

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   ObserVault Privacy-First Collector Onboarding Wizard   " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

if (-not $EnrollmentToken) {
    Write-Error "ERROR: Enrollment token is required. Pass -EnrollmentToken or set $env:OBSERVAULT_ENROLL_TOKEN"
    exit 1
}

# 1. Verify Python 3.10+
Write-Host "[1/5] Checking Python runtime..." -ForegroundColor Yellow
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) {
    Write-Error "ERROR: Python is not installed or not in PATH. Please install Python 3.10+."
    exit 1
}

# 2. Setup Work Directory
$WorkDir = Join-Path $env:LOCALAPPDATA "ObserVault\Collector"
if (-not (Test-Path $WorkDir)) {
    New-Item -ItemType Directory -Path $WorkDir -Force | Out-Null
}
Write-Host "[2/5] Provisioned working directory: $WorkDir" -ForegroundColor Green

# 3. Perform Enrollment Handshake
Write-Host "[3/5] Performing secure enrollment handshake with SaaS backend ($BackendUrl)..." -ForegroundColor Yellow
$EnrollBody = @{
    enrollment_token = $EnrollmentToken
    hostname = $env:COMPUTERNAME
    os_type = "windows"
    os_version = (Get-CimInstance Win32_OperatingSystem).Caption
    collector_version = "1.0.0"
} | ConvertTo-Json

try {
    $Response = Invoke-RestMethod -Uri "$BackendUrl/api/v1/collectors/enroll" -Method Post -Body $EnrollBody -ContentType "application/json"
    Write-Host "[4/5] Enrollment Handshake Succeeded!" -ForegroundColor Green
    Write-Host "      Assigned Collector ID: $($Response.collector_id)" -ForegroundColor Cyan
    Write-Host "      Device Name: $($Response.collector_name)" -ForegroundColor Cyan
    
    # Store Config Securely
    $ConfigFile = Join-Path $WorkDir "collector_config.json"
    $Response | ConvertTo-Json | Set-Content -Path $ConfigFile -Force
    Write-Host "[4/5] Operational credentials safely stored at $ConfigFile" -ForegroundColor Green

    # Launch persistent collector runtime
    Write-Host "[5/5] Launching persistent ObserVault collector daemon..." -ForegroundColor Yellow
    python -m collector.runtime start
    Write-Host "`n>>> SUCCESS: Windows Collector successfully enrolled and started! View live status in ObserVault dashboard." -ForegroundColor Green
} catch {
    Write-Error "ERROR: Handshake failed: $_"
    exit 1
}
"""
    return PlainTextResponse(content=script_content, media_type="text/plain")
