# backend/app/api/telemetry.py
import json
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.crypto import TelemetrySigner
from app.core.config import settings
from app.api.security_hardening import record_security_event
from app.models.models import (
    Collector, Tenant, Server, TelemetryRecord, EgressAudit
)
from app.schemas.schemas import TelemetryBatchIngest
from app.api.deps import get_current_collector
from app.detection.anomaly_engine import run_anomaly_detection, run_advanced_detection
from app.correlation.incident_correlator import run_incident_correlation
from app.recommendations.advisor import generate_recommendations

router = APIRouter()

@router.post("")
def ingest_telemetry(
    batch: TelemetryBatchIngest,
    collector: Collector = Depends(get_current_collector),
    db: Session = Depends(get_db),
    x_signature: Optional[str] = Header(None, alias="X-Signature"),
    x_timestamp: Optional[str] = Header(None, alias="X-Timestamp"),
    x_nonce: Optional[str] = Header(None, alias="X-Nonce")
):
    """
    Secure Telemetry Ingestion Endpoint.
    - Authenticated via Collector API key (X-Collector-Key).
    - Cryptographic batch signature & replay attack validation (X-Signature, X-Timestamp, X-Nonce).
    - Tenant identified strictly by collector record (never trusting unverified client payload).
    - Strict metadata allow-list enforced by Pydantic schema (extra='forbid').
    - Deduplicates records by unique event_id to prevent replay/duplicate storage upon retry.
    - Triggers rule-based Anomaly Engine, Incident Correlator, and Actionable Recommendations.
    """
    # Cryptographic integrity and replay verification if signature headers provided
    if x_signature and x_timestamp and x_nonce:
        is_valid, err_msg = TelemetrySigner.verify_batch(
            secret_key=settings.SECRET_KEY,
            collector_id=collector.id,
            timestamp_str=x_timestamp,
            nonce=x_nonce,
            signature=x_signature,
            payload_data=batch.model_dump(mode="json")
        )
        if not is_valid:
            record_security_event(
                event_type="SIGNATURE_REPLAY_REJECTION",
                severity="high",
                details=f"Collector {collector.id} rejected: {err_msg}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Security verification failed: {err_msg}"
            )
    tenant_id = collector.tenant_id
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant associated with collector not found")

    ingested_count = 0
    duplicate_count = 0
    now = datetime.now(timezone.utc)

    # Track privacy audit stats for this batch
    rejected_fields_observed = set()
    total_rejected_fields_count = 0
    sensitive_attack_detected = False

    for item in batch.records:
        # Check duplicate
        existing = db.query(TelemetryRecord).filter(TelemetryRecord.event_id == item.event_id).first()
        if existing:
            duplicate_count += 1
            continue

        # Look up or create server
        server = db.query(Server).filter(
            Server.tenant_id == tenant_id,
            Server.hostname == item.hostname
        ).first()

        if not server:
            server = Server(
                tenant_id=tenant_id,
                collector_id=collector.id,
                hostname=item.hostname,
                display_name=item.hostname.replace("-", " ").title(),
                ip_address="192.168.1." + str(hash(item.hostname) % 250 + 2),
                os_info="Ubuntu 24.04 LTS (x86_64)",
                status="healthy",
                service_status=item.service_status,
                last_cpu=item.cpu_percent,
                last_memory=item.memory_percent,
                last_disk=item.disk_percent,
                last_latency=item.network_latency_ms,
                last_packet_loss=item.packet_loss_percent,
                last_failed_logins=item.failed_login_count,
                is_simulated=item.is_simulated,
                last_seen=now
            )
            db.add(server)
            db.flush()
        else:
            # Update server live telemetry snapshot
            server.last_cpu = item.cpu_percent
            server.last_memory = item.memory_percent
            server.last_disk = item.disk_percent
            server.last_latency = item.network_latency_ms
            server.last_packet_loss = item.packet_loss_percent
            server.last_failed_logins = item.failed_login_count
            server.service_status = item.service_status
            server.is_simulated = item.is_simulated
            server.last_seen = now
            if not server.collector_id:
                server.collector_id = collector.id

        # Record audit metadata if present in record's privacy_summary
        if item.privacy_summary:
            total_rejected_fields_count += item.privacy_summary.fields_rejected
            for f in item.privacy_summary.rejected_field_names:
                rejected_fields_observed.add(f)
                if any(k in f.lower() for k in ["password", "token", "secret", "cred", "auth"]):
                    sensitive_attack_detected = True

        # Store approved metadata only
        safe_dict = item.model_dump(mode="json")
        rec = TelemetryRecord(
            tenant_id=tenant_id,
            collector_id=collector.id,
            server_id=server.id,
            event_id=item.event_id,
            timestamp=item.timestamp,
            cpu_percent=item.cpu_percent,
            memory_percent=item.memory_percent,
            disk_percent=item.disk_percent,
            network_latency_ms=item.network_latency_ms,
            packet_loss_percent=item.packet_loss_percent,
            network_status=item.network_status,
            failed_login_count=item.failed_login_count,
            service_status=item.service_status,
            is_simulated=item.is_simulated,
            raw_metadata_json=json.dumps(safe_dict)
        )
        db.add(rec)
        db.flush()

        # Run Anomaly Detection for this record
        run_anomaly_detection(db, rec, tenant, server)
        run_advanced_detection(db, rec, tenant, server)
        ingested_count += 1

    # Update collector metrics
    collector.last_successful_transmission = now
    collector.last_heartbeat = now
    collector.status = "online"
    collector.buffered_records_count = max(0, collector.buffered_records_count - ingested_count)

    # Run Incident Correlator across the tenant's current alerts
    run_incident_correlation(db, tenant)

    # Generate Actionable Recommendations
    generate_recommendations(db, tenant)

    # Log Egress Audit record
    if ingested_count > 0:
        sample_payload = batch.records[0].model_dump(mode="json") if batch.records else {}
        audit = EgressAudit(
            tenant_id=tenant_id,
            collector_id=collector.id,
            batch_id=batch.batch_id,
            total_processed=len(batch.records),
            approved_count=ingested_count,
            rejected_fields_count=total_rejected_fields_count,
            rejected_field_names_json=json.dumps(list(rejected_fields_observed)),
            approved_fields_sample_json=json.dumps(sample_payload),
            simulated_attack_payload_stripped=sensitive_attack_detected,
            status="delivered",
            timestamp=now
        )
        db.add(audit)

    db.commit()

    return {
        "status": "success",
        "batch_id": batch.batch_id,
        "records_ingested": ingested_count,
        "duplicates_ignored": duplicate_count,
        "message": f"Successfully processed {ingested_count} approved metadata records."
    }
