# tests/test_end_to_end.py
import pytest
import sys
import os
import uuid
import json
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend"))

from collector.privacy.sanitiser import LocalPrivacySanitiser
from app.core.database import SessionLocal
from app.models.models import Tenant, Collector, Server, TelemetryRecord, Alert, Incident, Recommendation
from app.detection.anomaly_engine import run_anomaly_detection
from app.correlation.incident_correlator import run_incident_correlation
from app.recommendations.advisor import generate_recommendations

def test_complete_observault_pipeline():
    """
    Simulates the entire workflow:
    1. Local Collector generates telemetry with sensitive credential artifact.
    2. Local Privacy Sanitiser purges credentials and produces approved metadata.
    3. Backend processes metadata record into database.
    4. Anomaly Engine detects breach.
    5. Incident Correlator groups multi-symptom alerts into unified Incident.
    6. Advisor issues human-in-the-loop Recommendations.
    """
    db = SessionLocal()
    try:
        tenant = db.query(Tenant).filter(Tenant.slug == "acme-fintech").first()
        collector = db.query(Collector).filter(Collector.tenant_id == tenant.id).first()

        # Step 1: Raw Local Event with sensitive payload
        raw_event = {
            "event_id": f"e2e-{uuid.uuid4().hex[:8]}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "server_id": "srv-e2e-cluster",
            "hostname": "e2e-cluster-node",
            "collector_id": collector.id,
            "collector_version": "1.0.0",
            "cpu_percent": 97.4,         # High CPU anomaly
            "memory_percent": 82.0,
            "disk_percent": 60.0,
            "network_latency_ms": 180.0, # High latency anomaly
            "packet_loss_percent": 0.0,
            "network_status": "connected",
            "failed_login_count": 0,
            "service_status": "degraded",
            "is_simulated": True,
            # Sensitive data that MUST NOT leak:
            "super_secret_admin_token": "bearer_jwt_unauthorized_token_xyz",
            "db_password": "PlaintextRootPassword!456",
            "internal_ip": "172.16.4.1"
        }

        # Step 2: Local Privacy Processing
        outbound, privacy_summary = LocalPrivacySanitiser.sanitise_and_transform(raw_event)
        
        # Verify sanitisation
        assert "db_password" not in outbound
        assert "super_secret_admin_token" not in outbound
        assert privacy_summary["sensitive_data_stripped"] is True

        # Step 3: Backend Ingestion
        server = db.query(Server).filter(Server.hostname == outbound["hostname"]).first()
        if not server:
            server = Server(
                tenant_id=tenant.id,
                collector_id=collector.id,
                hostname=outbound["hostname"],
                display_name="E2E Cluster Node",
                ip_address="10.0.99.1",
                os_info="Linux 6.8",
                status="healthy",
                service_status="degraded",
                last_cpu=outbound["cpu_percent"],
                last_memory=outbound["memory_percent"],
                last_disk=outbound["disk_percent"],
                last_latency=outbound["network_latency_ms"],
                last_packet_loss=outbound["packet_loss_percent"],
                last_failed_logins=0,
                is_simulated=True,
                last_seen=datetime.now(timezone.utc)
            )
            db.add(server)
            db.flush()

        rec = TelemetryRecord(
            tenant_id=tenant.id,
            collector_id=collector.id,
            server_id=server.id,
            event_id=outbound["event_id"],
            timestamp=datetime.now(timezone.utc),
            cpu_percent=outbound["cpu_percent"],
            memory_percent=outbound["memory_percent"],
            disk_percent=outbound["disk_percent"],
            network_latency_ms=outbound["network_latency_ms"],
            packet_loss_percent=outbound["packet_loss_percent"],
            network_status=outbound["network_status"],
            failed_login_count=outbound["failed_login_count"],
            service_status=outbound["service_status"],
            is_simulated=True,
            raw_metadata_json=json.dumps(outbound)
        )
        db.add(rec)
        db.flush()

        # Step 4: Run Anomaly Engine
        alerts = run_anomaly_detection(db, rec, tenant, server)
        alert_types = {a.alert_type for a in alerts}
        assert "high_cpu" in alert_types
        assert "high_latency" in alert_types

        # Step 5: Run Incident Correlation Engine
        incidents = run_incident_correlation(db, tenant)
        assert len(incidents) >= 1
        res_incident = next((inc for inc in incidents if "RES" in inc.incident_code or "Resource" in inc.title), None)
        assert res_incident is not None, "Expected resource exhaustion incident to be correlated"
        assert res_incident.confidence_score >= 0.85

        # Step 6: Generate Recommendations
        recs = generate_recommendations(db, tenant)
        assert len(recs) >= 1
        rec_item = recs[0]
        assert rec_item.human_approval_required is True

        # Commit
        db.commit()

        # Step 7: Leak Verification: Query DB directly to prove password was never stored
        leak_count = db.query(TelemetryRecord).filter(
            TelemetryRecord.raw_metadata_json.like("%PlaintextRootPassword%")
        ).count()
        assert leak_count == 0, "CRITICAL: Plaintext password leaked into cloud database!"

    finally:
        db.close()
