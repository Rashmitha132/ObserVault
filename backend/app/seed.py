# backend/app/seed.py
import json
import uuid
from datetime import datetime, timezone, timedelta
from app.core.database import SessionLocal, Base, engine
from app.core.security import get_password_hash, hash_token
from app.models.models import (
    Tenant, User, Collector, Server, TelemetryRecord, Alert, Incident, Recommendation, EgressAudit
)

def seed_database():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # Clear existing data for fresh seed if needed
    if db.query(Tenant).count() > 0:
        print("Database already contains data. Skipping re-seed.")
        db.close()
        return

    now = datetime.now(timezone.utc)

    print("Seeding ObserVault Multi-Tenant Database...")

    # ------------------ TENANT 1: ACME FINTECH CORP ------------------
    t1 = Tenant(
        id=str(uuid.uuid4()),
        name="Acme FinTech Corp",
        slug="acme-fintech",
        plan="Enterprise Shield",
        cpu_threshold=90.0,
        memory_threshold=90.0,
        disk_threshold=85.0,
        latency_threshold_ms=120.0,
        packet_loss_threshold=5.0,
        failed_login_threshold=3,
        created_at=now - timedelta(days=30)
    )
    db.add(t1)
    db.flush()

    # Users for Tenant 1
    u1_admin = User(
        id=str(uuid.uuid4()),
        tenant_id=t1.id,
        email="admin@acme.com",
        hashed_password=get_password_hash("Password123!"),
        full_name="Sarah Jenkins (SecOps Director)",
        role="admin",
        is_active=True,
        created_at=now - timedelta(days=30)
    )
    u1_eng = User(
        id=str(uuid.uuid4()),
        tenant_id=t1.id,
        email="sre@acme.com",
        hashed_password=get_password_hash("Password123!"),
        full_name="Alex Chen (Senior SRE)",
        role="engineer",
        is_active=True,
        created_at=now - timedelta(days=28)
    )
    db.add_all([u1_admin, u1_eng])

    # Collector for Tenant 1
    # Plain key: ov_col_acme_production_secret_key_2026
    c1_token = "ov_col_acme_production_secret_key_2026"
    c1 = Collector(
        id=str(uuid.uuid4()),
        tenant_id=t1.id,
        token_hash=hash_token(c1_token),
        name="Acme On-Prem Core Collector",
        hostname="acme-collector-node-01",
        ip_address="10.0.1.15",
        version="1.0.0",
        status="online",
        collection_interval=5,
        buffered_records_count=0,
        failed_transmissions_count=0,
        last_heartbeat=now,
        last_successful_transmission=now,
        created_at=now - timedelta(days=15)
    )
    db.add(c1)
    db.flush()

    # Servers for Tenant 1
    s1_api = Server(
        id=str(uuid.uuid4()),
        tenant_id=t1.id,
        collector_id=c1.id,
        hostname="prod-api-gateway",
        display_name="Production API Gateway",
        ip_address="10.0.2.10",
        os_info="Ubuntu 24.04 LTS (x86_64)",
        status="warning",
        service_status="degraded",
        last_cpu=94.2,
        last_memory=86.5,
        last_disk=64.0,
        last_latency=142.5,
        last_packet_loss=1.2,
        last_failed_logins=0,
        is_simulated=False,
        last_seen=now,
        created_at=now - timedelta(days=15)
    )
    s1_pay = Server(
        id=str(uuid.uuid4()),
        tenant_id=t1.id,
        collector_id=c1.id,
        hostname="prod-payment-svc",
        display_name="Payment Transaction Service",
        ip_address="10.0.2.11",
        os_info="RHEL 9.3 (x86_64)",
        status="healthy",
        service_status="up",
        last_cpu=42.1,
        last_memory=58.2,
        last_disk=49.0,
        last_latency=24.0,
        last_packet_loss=0.0,
        last_failed_logins=0,
        is_simulated=False,
        last_seen=now,
        created_at=now - timedelta(days=15)
    )
    s1_db = Server(
        id=str(uuid.uuid4()),
        tenant_id=t1.id,
        collector_id=c1.id,
        hostname="prod-database-primary",
        display_name="Primary Ledger Database",
        ip_address="10.0.2.12",
        os_info="Debian 12 Bookworm",
        status="healthy",
        service_status="up",
        last_cpu=58.4,
        last_memory=74.1,
        last_disk=78.2,
        last_latency=18.5,
        last_packet_loss=0.0,
        last_failed_logins=0,
        is_simulated=False,
        last_seen=now,
        created_at=now - timedelta(days=15)
    )
    s1_auth = Server(
        id=str(uuid.uuid4()),
        tenant_id=t1.id,
        collector_id=c1.id,
        hostname="prod-auth-cluster",
        display_name="Customer Auth Gateway",
        ip_address="10.0.2.13",
        os_info="Ubuntu 24.04 LTS (x86_64)",
        status="critical",
        service_status="up",
        last_cpu=68.9,
        last_memory=62.0,
        last_disk=51.4,
        last_latency=38.0,
        last_packet_loss=0.0,
        last_failed_logins=7,
        is_simulated=False,
        last_seen=now,
        created_at=now - timedelta(days=15)
    )
    db.add_all([s1_api, s1_pay, s1_db, s1_auth])
    db.flush()

    # Seed baseline Telemetry records for Acme
    for i in range(15):
        t_time = now - timedelta(minutes=(15 - i) * 2)
        rec = TelemetryRecord(
            tenant_id=t1.id,
            collector_id=c1.id,
            server_id=s1_api.id,
            event_id=str(uuid.uuid4()),
            timestamp=t_time,
            cpu_percent=70.0 + (i * 1.8),
            memory_percent=75.0 + (i * 0.8),
            disk_percent=64.0,
            network_latency_ms=60.0 + (i * 5.5),
            packet_loss_percent=0.1 * i,
            network_status="connected",
            failed_login_count=0,
            service_status="degraded" if i > 10 else "up",
            is_simulated=False,
            raw_metadata_json=f'{{"event_id": "init-{i}", "cpu_percent": {round(70.0 + (i * 1.8), 1)}}}'
        )
        db.add(rec)

    # Seed Alerts for Acme
    a1_cpu = Alert(
        id=str(uuid.uuid4()),
        tenant_id=t1.id,
        server_id=s1_api.id,
        alert_type="high_cpu",
        severity="critical",
        title=f"High CPU Utilisation on {s1_api.display_name}",
        description="CPU utilisation reached 94.2%, exceeding threshold of 90.0%.",
        metric_name="cpu_percent",
        observed_value=94.2,
        threshold_value=90.0,
        status="active",
        created_at=now - timedelta(minutes=18)
    )
    a1_lat = Alert(
        id=str(uuid.uuid4()),
        tenant_id=t1.id,
        server_id=s1_api.id,
        alert_type="high_latency",
        severity="high",
        title=f"Elevated Network Latency on {s1_api.display_name}",
        description="Network round-trip latency measured at 142.5ms, exceeding threshold of 120.0ms.",
        metric_name="network_latency_ms",
        observed_value=142.5,
        threshold_value=120.0,
        status="active",
        created_at=now - timedelta(minutes=16)
    )
    a1_auth = Alert(
        id=str(uuid.uuid4()),
        tenant_id=t1.id,
        server_id=s1_auth.id,
        alert_type="auth_spike",
        severity="high",
        title=f"Repeated Authentication Failures on {s1_auth.display_name}",
        description="Detected 7 failed login attempts within evaluation interval (threshold: 3).",
        metric_name="failed_login_count",
        observed_value=7.0,
        threshold_value=3.0,
        status="active",
        created_at=now - timedelta(minutes=10)
    )
    db.add_all([a1_cpu, a1_lat, a1_auth])
    db.flush()

    # Seed Incidents for Acme
    inc1 = Incident(
        id=str(uuid.uuid4()),
        tenant_id=t1.id,
        incident_code="INC-ACM-RES",
        title="Resource Starvation Degrading Performance on Production API Gateway",
        severity="critical",
        status="open",
        primary_server_id=s1_api.id,
        possible_cause="Heavy traffic spike or CPU thread exhaustion causing request queuing and elevated response latency.",
        confidence_score=0.91,
        evidence_summary="Simultaneous CPU saturation (94.2%) and latency elevation (142.5ms) observed on prod-api-gateway. Correlated within 15-minute operational window.",
        recommended_actions_json=json.dumps([
            "Inspect top running worker processes locally using system diagnostics.",
            "Review API rate limiter settings on ingress proxy.",
            "Scale horizontal worker instances if legitimate traffic surge is confirmed."
        ]),
        created_at=now - timedelta(minutes=15),
        updated_at=now - timedelta(minutes=5)
    )
    inc1.alerts = [a1_cpu, a1_lat]

    inc2 = Incident(
        id=str(uuid.uuid4()),
        tenant_id=t1.id,
        incident_code="INC-ACM-SEC",
        title="Suspected Credential Spraying / Auth Anomaly on Customer Auth Gateway",
        severity="high",
        status="investigating",
        primary_server_id=s1_auth.id,
        possible_cause="Automated credential stuffing or brute-force pattern targeting customer login endpoints.",
        confidence_score=0.88,
        evidence_summary="7 consecutive failed authentication attempts registered. Local privacy collector sanitized all credentials and transmitted only statistical count metadata.",
        recommended_actions_json=json.dumps([
            "Check ingress IP rate limiting rules at Cloudflare / Edge firewall.",
            "Verify account lockout policy triggers in identity provider.",
            "Ensure CAPTCHA / bot challenge is enforced on public auth routes."
        ]),
        created_at=now - timedelta(minutes=10),
        updated_at=now - timedelta(minutes=2)
    )
    inc2.alerts = [a1_auth]
    db.add_all([inc1, inc2])
    db.flush()

    # Seed Recommendations for Acme
    r1 = Recommendation(
        id=str(uuid.uuid4()),
        tenant_id=t1.id,
        incident_id=inc1.id,
        severity="critical",
        category="infrastructure",
        title="Remediate API Gateway CPU Starvation",
        description="Implement immediate horizontal scaling or investigate stuck asynchronous worker threads on prod-api-gateway.",
        rationale="CPU utilisation at 94.2% is causing request queuing with latency at 142.5ms.",
        action_steps_json=json.dumps([
            "Run local thread profiling on prod-api-gateway without transmitting thread dumps.",
            "Temporarily divert 30% of incoming read queries to secondary replica.",
            "Scale up container task count from 4 to 8 instances."
        ]),
        human_approval_required=True,
        status="pending",
        created_at=now - timedelta(minutes=12)
    )
    r2 = Recommendation(
        id=str(uuid.uuid4()),
        tenant_id=t1.id,
        incident_id=inc2.id,
        severity="high",
        category="security",
        title="Review Auth Gateway Ingress Firewall Rules",
        description="Verify edge rate limiting and block repetitive suspect CIDR blocks targeting customer authentication endpoints.",
        rationale="Spike of 7 failed login attempts observed on prod-auth-cluster.",
        action_steps_json=json.dumps([
            "Enforce IP throttling to 5 failed attempts per minute per subnet.",
            "Enable adaptive step-up MFA for flagged accounts.",
            "Review sanitized auth failure distribution in ObserVault Security dashboard."
        ]),
        human_approval_required=True,
        status="pending",
        created_at=now - timedelta(minutes=8)
    )
    db.add_all([r1, r2])

    # Seed Egress Audits for Acme
    egress1 = EgressAudit(
        id=str(uuid.uuid4()),
        tenant_id=t1.id,
        collector_id=c1.id,
        batch_id="batch-acme-initial-01",
        total_processed=42,
        approved_count=42,
        rejected_fields_count=84,
        rejected_field_names_json=json.dumps(["password", "token", "auth_header", "user_email", "raw_payload"]),
        approved_fields_sample_json=json.dumps({
            "event_id": str(uuid.uuid4()),
            "hostname": "prod-api-gateway",
            "cpu_percent": 94.2,
            "memory_percent": 86.5,
            "failed_login_count": 0,
            "service_status": "degraded"
        }),
        simulated_attack_payload_stripped=True,
        status="delivered",
        timestamp=now - timedelta(minutes=5)
    )
    db.add(egress1)

    # ------------------ TENANT 2: BIOHEALTH GLOBAL ------------------
    t2 = Tenant(
        id=str(uuid.uuid4()),
        name="BioHealth Global",
        slug="biohealth",
        plan="Healthcare Compliance Tier",
        cpu_threshold=88.0,
        memory_threshold=88.0,
        disk_threshold=80.0,
        latency_threshold_ms=100.0,
        packet_loss_threshold=3.0,
        failed_login_threshold=2,
        created_at=now - timedelta(days=20)
    )
    db.add(t2)
    db.flush()

    # User for Tenant 2
    u2_admin = User(
        id=str(uuid.uuid4()),
        tenant_id=t2.id,
        email="admin@biohealth.com",
        hashed_password=get_password_hash("Password123!"),
        full_name="Dr. Marcus Vance (Chief Medical Informatics Officer)",
        role="admin",
        is_active=True,
        created_at=now - timedelta(days=20)
    )
    db.add(u2_admin)

    # Collector for Tenant 2
    # Plain key: ov_col_biohealth_clinical_key_2026
    c2_token = "ov_col_biohealth_clinical_key_2026"
    c2 = Collector(
        id=str(uuid.uuid4()),
        tenant_id=t2.id,
        token_hash=hash_token(c2_token),
        name="BioHealth HIPAA-Compliant Edge Collector",
        hostname="biohealth-edge-node",
        ip_address="192.168.10.5",
        version="1.0.0",
        status="online",
        collection_interval=5,
        buffered_records_count=0,
        failed_transmissions_count=0,
        last_heartbeat=now,
        last_successful_transmission=now,
        created_at=now - timedelta(days=10)
    )
    db.add(c2)
    db.flush()

    # Servers for Tenant 2
    s2_gen = Server(
        id=str(uuid.uuid4()),
        tenant_id=t2.id,
        collector_id=c2.id,
        hostname="genomics-pipeline-01",
        display_name="Genomics Sequencer Node 01",
        ip_address="192.168.10.100",
        os_info="Ubuntu 22.04 LTS (x86_64)",
        status="healthy",
        service_status="up",
        last_cpu=45.2,
        last_memory=68.0,
        last_disk=52.1,
        last_latency=31.0,
        last_packet_loss=0.0,
        last_failed_logins=0,
        is_simulated=False,
        last_seen=now,
        created_at=now - timedelta(days=10)
    )
    s2_cli = Server(
        id=str(uuid.uuid4()),
        tenant_id=t2.id,
        collector_id=c2.id,
        hostname="clinical-portal-01",
        display_name="Clinical Patient Portal",
        ip_address="192.168.10.101",
        os_info="Debian 12 Bookworm",
        status="healthy",
        service_status="up",
        last_cpu=32.4,
        last_memory=48.2,
        last_disk=38.0,
        last_latency=22.5,
        last_packet_loss=0.0,
        last_failed_logins=0,
        is_simulated=False,
        last_seen=now,
        created_at=now - timedelta(days=10)
    )
    db.add_all([s2_gen, s2_cli])

    # Seed baseline Telemetry records for BioHealth
    for i in range(10):
        t_time = now - timedelta(minutes=(10 - i) * 3)
        rec2 = TelemetryRecord(
            tenant_id=t2.id,
            collector_id=c2.id,
            server_id=s2_gen.id,
            event_id=str(uuid.uuid4()),
            timestamp=t_time,
            cpu_percent=40.0 + (i * 0.5),
            memory_percent=60.0 + (i * 0.8),
            disk_percent=52.0,
            network_latency_ms=28.0 + (i * 0.3),
            packet_loss_percent=0.0,
            network_status="connected",
            failed_login_count=0,
            service_status="up",
            is_simulated=False,
            raw_metadata_json=f'{{"event_id": "bio-init-{i}", "cpu_percent": {round(40.0 + (i * 0.5), 1)}}}'
        )
        db.add(rec2)

    # Seed Egress Audits for BioHealth
    egress2 = EgressAudit(
        id=str(uuid.uuid4()),
        tenant_id=t2.id,
        collector_id=c2.id,
        batch_id="batch-biohealth-initial-01",
        total_processed=18,
        approved_count=18,
        rejected_fields_count=54,
        rejected_field_names_json=json.dumps(["patient_name", "mrn", "diagnosis_code", "raw_payload"]),
        approved_fields_sample_json=json.dumps({
            "event_id": str(uuid.uuid4()),
            "hostname": "clinical-portal-01",
            "cpu_percent": 32.4,
            "memory_percent": 48.2,
            "failed_login_count": 0,
            "service_status": "up"
        }),
        simulated_attack_payload_stripped=False,
        status="delivered",
        timestamp=now - timedelta(minutes=10)
    )
    db.add(egress2)

    db.commit()
    seed_traces_if_empty(db)
    db.close()
    print("Database seeding completed successfully!")
    print("Demo Organizations:")
    print(" 1) Acme FinTech Corp (email: admin@acme.com / Password123!)")
    print(" 2) BioHealth Global  (email: admin@biohealth.com / Password123!)")

def seed_traces_if_empty(db=None):
    from app.models.models import TraceSpan, ServiceNode, ServiceDependency, Tenant, Collector
    from collector.instrumentation.fastapi_instrumentor import TraceGenerator

    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        if db.query(TraceSpan).count() > 0:
            print("Trace spans already seeded.")
            return

        print("Seeding OpenTelemetry Traces & Microservice Topology...")
        t1 = db.query(Tenant).filter(Tenant.slug == "acme-fintech").first()
        col1 = db.query(Collector).filter(Collector.tenant_id == t1.id).first() if t1 else None

        if not t1 or not col1:
            return

        now = datetime.now(timezone.utc)

        # 1. Services
        services_data = [
            ("api-gateway", "api_gateway", "healthy", 32.4, 52.0, 0.008, 1450.0),
            ("auth-service", "auth", "healthy", 18.2, 29.5, 0.004, 980.0),
            ("orders-service", "app_service", "healthy", 44.1, 72.0, 0.015, 870.0),
            ("payments-service", "app_service", "healthy", 68.5, 110.0, 0.021, 440.0),
            ("postgres-primary", "database", "healthy", 11.8, 22.4, 0.002, 2900.0),
            ("redis-cache", "cache", "healthy", 2.4, 4.8, 0.000, 3800.0),
        ]

        for name, stype, health, avg_l, p95, err, rpm in services_data:
            node = ServiceNode(
                id=str(uuid.uuid4()),
                tenant_id=t1.id,
                name=name,
                service_type=stype,
                health_status=health,
                avg_latency_ms=avg_l,
                p95_latency_ms=p95,
                error_rate=err,
                throughput_rpm=rpm,
                last_seen=now
            )
            db.add(node)

        # 2. Dependencies
        dep_data = [
            ("api-gateway", "auth-service", 1240, 18.2, 5),
            ("api-gateway", "orders-service", 980, 44.1, 15),
            ("orders-service", "payments-service", 440, 68.5, 9),
            ("orders-service", "postgres-primary", 2400, 11.8, 4),
            ("auth-service", "redis-cache", 3100, 2.4, 0)
        ]

        for caller, callee, count, dur, err_cnt in dep_data:
            dep = ServiceDependency(
                id=str(uuid.uuid4()),
                tenant_id=t1.id,
                caller_service_name=caller,
                callee_service_name=callee,
                call_count=count,
                avg_duration_ms=dur,
                error_count=err_cnt,
                last_interaction=now
            )
            db.add(dep)

        # 3. Generate distributed traces (6 realistic traces: 5 nominal, 1 error scenario)
        for i in range(5):
            sim_error = (i == 3)  # One trace with downstream DB timeout
            spans = TraceGenerator.generate_distributed_trace(simulate_error=sim_error)
            for s in spans:
                span_rec = TraceSpan(
                    id=str(uuid.uuid4()),
                    tenant_id=t1.id,
                    collector_id=col1.id,
                    trace_id=s["trace_id"],
                    span_id=s["span_id"],
                    parent_span_id=s.get("parent_span_id"),
                    service_name=s["service_name"],
                    operation_name=s["operation_name"],
                    span_kind=s.get("span_kind", "SERVER"),
                    start_time=datetime.fromisoformat(s["start_time"]),
                    end_time=datetime.fromisoformat(s["end_time"]),
                    duration_ms=s["duration_ms"],
                    status_code=s["status_code"],
                    status_message=s.get("status_message"),
                    attributes_json=json.dumps(s.get("attributes", {}))
                )
                db.add(span_rec)

        db.commit()
        print("OpenTelemetry trace & topology seed successful!")
    finally:
        if close_db:
            db.close()

if __name__ == "__main__":
    seed_database()
