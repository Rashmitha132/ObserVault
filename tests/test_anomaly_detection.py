# tests/test_anomaly_detection.py
import pytest
import sys
import os
import uuid
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend"))

from app.core.database import SessionLocal
from app.models.models import Tenant, Server, TelemetryRecord, Alert
from app.detection.anomaly_engine import run_anomaly_detection

def test_anomaly_detection_and_deduplication():
    db = SessionLocal()
    try:
        tenant = db.query(Tenant).filter(Tenant.slug == "acme-fintech").first()
        server = db.query(Server).filter(Server.tenant_id == tenant.id).first()

        # Create record with breach condition: CPU at 96% (threshold 90%)
        record = TelemetryRecord(
            tenant_id=tenant.id,
            server_id=server.id,
            event_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc),
            cpu_percent=96.0,
            memory_percent=50.0,
            disk_percent=50.0,
            network_latency_ms=25.0,
            packet_loss_percent=0.0,
            failed_login_count=0,
            service_status="up",
            is_simulated=True
        )
        db.add(record)
        db.flush()

        # First run: should trigger high_cpu alert
        alerts1 = run_anomaly_detection(db, record, tenant, server)
        cpu_alerts = [a for a in alerts1 if a.alert_type == "high_cpu"]
        assert len(cpu_alerts) >= 1
        alert_id = cpu_alerts[0].id
        assert cpu_alerts[0].status == "active"
        assert cpu_alerts[0].observed_value == 96.0

        # Second run with another breach (CPU 98%): should DEDUPLICATE and update existing alert rather than create another
        record2 = TelemetryRecord(
            tenant_id=tenant.id,
            server_id=server.id,
            event_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc),
            cpu_percent=98.0,
            memory_percent=50.0,
            disk_percent=50.0,
            network_latency_ms=25.0,
            packet_loss_percent=0.0,
            failed_login_count=0,
            service_status="up",
            is_simulated=True
        )
        db.add(record2)
        db.flush()

        alerts2 = run_anomaly_detection(db, record2, tenant, server)
        cpu_alerts2 = [a for a in alerts2 if a.alert_type == "high_cpu"]
        assert len(cpu_alerts2) >= 1
        # ID must remain the same (deduplication confirmed)
        assert cpu_alerts2[0].id == alert_id
        assert cpu_alerts2[0].observed_value == 98.0

        # Third run: condition recovers (CPU falls to 45%)
        record3 = TelemetryRecord(
            tenant_id=tenant.id,
            server_id=server.id,
            event_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc),
            cpu_percent=45.0,
            memory_percent=50.0,
            disk_percent=50.0,
            network_latency_ms=25.0,
            packet_loss_percent=0.0,
            failed_login_count=0,
            service_status="up",
            is_simulated=True
        )
        db.add(record3)
        db.flush()

        run_anomaly_detection(db, record3, tenant, server)
        # Check that alert was marked resolved
        refreshed_alert = db.query(Alert).filter(Alert.id == alert_id).first()
        assert refreshed_alert.status == "resolved"

    finally:
        db.rollback()
        db.close()
