# backend/app/models/models.py
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text, Table
)
from sqlalchemy.orm import relationship
from app.core.database import Base

def gen_uuid():
    return str(uuid.uuid4())

def utc_now():
    return datetime.now(timezone.utc)

# Association table between Incidents and Alerts
incident_alerts = Table(
    'incident_alerts',
    Base.metadata,
    Column('incident_id', String(36), ForeignKey('incidents.id', ondelete="CASCADE"), primary_key=True),
    Column('alert_id', String(36), ForeignKey('alerts.id', ondelete="CASCADE"), primary_key=True)
)

class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    name = Column(String(100), nullable=False)
    slug = Column(String(50), unique=True, nullable=False, index=True)
    plan = Column(String(50), default="Enterprise")
    # Configurable anomaly thresholds per tenant
    cpu_threshold = Column(Float, default=90.0)
    memory_threshold = Column(Float, default=90.0)
    disk_threshold = Column(Float, default=85.0)
    latency_threshold_ms = Column(Float, default=120.0)
    packet_loss_threshold = Column(Float, default=5.0)
    failed_login_threshold = Column(Integer, default=3)
    created_at = Column(DateTime, default=utc_now)

    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    collectors = relationship("Collector", back_populates="tenant", cascade="all, delete-orphan")
    servers = relationship("Server", back_populates="tenant", cascade="all, delete-orphan")
    telemetry_records = relationship("TelemetryRecord", back_populates="tenant", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="tenant", cascade="all, delete-orphan")
    incidents = relationship("Incident", back_populates="tenant", cascade="all, delete-orphan")
    recommendations = relationship("Recommendation", back_populates="tenant", cascade="all, delete-orphan")
    egress_audits = relationship("EgressAudit", back_populates="tenant", cascade="all, delete-orphan")
    trace_spans = relationship("TraceSpan", back_populates="tenant", cascade="all, delete-orphan")
    services = relationship("ServiceNode", back_populates="tenant", cascade="all, delete-orphan")
    ml_anomalies = relationship("MLAnomaly", back_populates="tenant", cascade="all, delete-orphan")
    slos = relationship("ServiceLevelObjective", back_populates="tenant", cascade="all, delete-orphan")
    capacity_warnings = relationship("CapacityWarning", back_populates="tenant", cascade="all, delete-orphan")
    integrations = relationship("IntegrationConfig", back_populates="tenant", cascade="all, delete-orphan")
    enrollment_tokens = relationship("DeviceEnrollmentToken", back_populates="tenant", cascade="all, delete-orphan")
    device_audit_logs = relationship("DeviceAuditLog", back_populates="tenant", cascade="all, delete-orphan")

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=False)
    role = Column(String(50), default="engineer")  # admin, engineer, viewer
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now)

    tenant = relationship("Tenant", back_populates="users")

class Collector(Base):
    __tablename__ = "collectors"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    hostname = Column(String(100), nullable=False)
    ip_address = Column(String(45), nullable=True)
    version = Column(String(20), default="1.0.0")
    status = Column(String(20), default="online")  # online, offline, degraded
    collection_interval = Column(Integer, default=5)  # in seconds
    buffered_records_count = Column(Integer, default=0)
    failed_transmissions_count = Column(Integer, default=0)
    last_heartbeat = Column(DateTime, default=utc_now)
    last_successful_transmission = Column(DateTime, default=utc_now)
    os_type = Column(String(50), default="windows")
    os_version = Column(String(100), nullable=True)
    environment = Column(String(50), default="production")  # production, staging, development
    enrollment_status = Column(String(30), default="active")  # pending, active, revoked
    is_revoked = Column(Boolean, default=False)
    revoked_at = Column(DateTime, nullable=True)
    revoked_by = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=utc_now)

    tenant = relationship("Tenant", back_populates="collectors")
    servers = relationship("Server", back_populates="collector")
    audit_logs = relationship("DeviceAuditLog", back_populates="collector")

class Server(Base):
    __tablename__ = "servers"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    collector_id = Column(String(36), ForeignKey("collectors.id", ondelete="SET NULL"), nullable=True)
    hostname = Column(String(100), nullable=False, index=True)
    display_name = Column(String(100), nullable=False)
    ip_address = Column(String(45), nullable=True)
    os_info = Column(String(100), default="Linux 6.8 x86_64")
    status = Column(String(20), default="healthy")  # healthy, warning, critical, offline
    service_status = Column(String(20), default="up")  # up, degraded, down
    last_cpu = Column(Float, default=0.0)
    last_memory = Column(Float, default=0.0)
    last_disk = Column(Float, default=0.0)
    last_latency = Column(Float, default=0.0)
    last_packet_loss = Column(Float, default=0.0)
    last_failed_logins = Column(Integer, default=0)
    is_simulated = Column(Boolean, default=False)
    last_seen = Column(DateTime, default=utc_now)
    created_at = Column(DateTime, default=utc_now)

    tenant = relationship("Tenant", back_populates="servers")
    collector = relationship("Collector", back_populates="servers")
    telemetry_records = relationship("TelemetryRecord", back_populates="server", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="server", cascade="all, delete-orphan")

class TelemetryRecord(Base):
    __tablename__ = "telemetry_records"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    collector_id = Column(String(36), ForeignKey("collectors.id", ondelete="SET NULL"), nullable=True)
    server_id = Column(String(36), ForeignKey("servers.id", ondelete="CASCADE"), nullable=False, index=True)
    event_id = Column(String(64), unique=True, nullable=False, index=True)  # Deduplication key
    timestamp = Column(DateTime, default=utc_now, index=True)
    cpu_percent = Column(Float, nullable=False)
    memory_percent = Column(Float, nullable=False)
    disk_percent = Column(Float, nullable=False)
    network_latency_ms = Column(Float, nullable=False)
    packet_loss_percent = Column(Float, nullable=False)
    network_status = Column(String(20), default="connected")
    failed_login_count = Column(Integer, default=0)
    service_status = Column(String(20), default="up")
    is_simulated = Column(Boolean, default=False)
    raw_metadata_json = Column(Text, nullable=True)  # Stores ONLY the validated outbound metadata JSON

    tenant = relationship("Tenant", back_populates="telemetry_records")
    server = relationship("Server", back_populates="telemetry_records")

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    server_id = Column(String(36), ForeignKey("servers.id", ondelete="CASCADE"), nullable=False, index=True)
    alert_type = Column(String(50), nullable=False)  # high_cpu, high_memory, high_latency, etc.
    severity = Column(String(20), nullable=False)  # critical, high, medium, low, info
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    metric_name = Column(String(50), nullable=False)
    observed_value = Column(Float, nullable=False)
    threshold_value = Column(Float, nullable=False)
    status = Column(String(20), default="active")  # active, acknowledged, resolved
    created_at = Column(DateTime, default=utc_now, index=True)
    resolved_at = Column(DateTime, nullable=True)

    tenant = relationship("Tenant", back_populates="alerts")
    server = relationship("Server", back_populates="alerts")
    incidents = relationship("Incident", secondary=incident_alerts, back_populates="alerts")

class Incident(Base):
    __tablename__ = "incidents"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    incident_code = Column(String(20), unique=True, nullable=False, index=True)  # e.g., INC-2026-001
    title = Column(String(200), nullable=False)
    severity = Column(String(20), default="high")  # critical, high, medium, low
    status = Column(String(20), default="open")  # open, investigating, acknowledged, resolved
    primary_server_id = Column(String(36), ForeignKey("servers.id", ondelete="SET NULL"), nullable=True)
    possible_cause = Column(Text, nullable=False)
    confidence_score = Column(Float, default=0.85)  # 0.0 - 1.0
    evidence_summary = Column(Text, nullable=False)
    recommended_actions_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now, index=True)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    resolved_at = Column(DateTime, nullable=True)

    tenant = relationship("Tenant", back_populates="incidents")
    primary_server = relationship("Server")
    alerts = relationship("Alert", secondary=incident_alerts, back_populates="incidents")
    recommendations = relationship("Recommendation", back_populates="incident")

class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    incident_id = Column(String(36), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=True)
    alert_id = Column(String(36), ForeignKey("alerts.id", ondelete="CASCADE"), nullable=True)
    severity = Column(String(20), default="medium")  # critical, high, medium, informational
    category = Column(String(50), default="infrastructure")  # infrastructure, security, network, reliability
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    rationale = Column(Text, nullable=False)
    action_steps_json = Column(Text, nullable=True)
    human_approval_required = Column(Boolean, default=True)  # Emphasize safety rule
    status = Column(String(20), default="pending")  # pending, acknowledged, completed, dismissed
    created_at = Column(DateTime, default=utc_now, index=True)

    tenant = relationship("Tenant", back_populates="recommendations")
    incident = relationship("Incident", back_populates="recommendations")

class EgressAudit(Base):
    __tablename__ = "egress_audit"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    collector_id = Column(String(36), ForeignKey("collectors.id", ondelete="SET NULL"), nullable=True)
    batch_id = Column(String(64), nullable=False, index=True)
    total_processed = Column(Integer, default=1)
    approved_count = Column(Integer, default=1)
    rejected_fields_count = Column(Integer, default=0)
    rejected_field_names_json = Column(Text, nullable=True)
    approved_fields_sample_json = Column(Text, nullable=True)
    simulated_attack_payload_stripped = Column(Boolean, default=False)
    status = Column(String(20), default="delivered")  # delivered, buffered, rejected
    timestamp = Column(DateTime, default=utc_now, index=True)

    tenant = relationship("Tenant", back_populates="egress_audits")

# ----------------- OPENTELEMETRY APPLICATION OBSERVABILITY -----------------

class TraceSpan(Base):
    __tablename__ = "trace_spans"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    collector_id = Column(String(36), ForeignKey("collectors.id", ondelete="SET NULL"), nullable=True)
    trace_id = Column(String(64), nullable=False, index=True)
    span_id = Column(String(64), nullable=False, index=True)
    parent_span_id = Column(String(64), nullable=True, index=True)
    service_name = Column(String(100), nullable=False, index=True)
    operation_name = Column(String(200), nullable=False)
    span_kind = Column(String(30), default="SERVER")  # SERVER, CLIENT, INTERNAL, PRODUCER, CONSUMER
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=False)
    duration_ms = Column(Float, nullable=False)
    status_code = Column(String(20), default="OK")  # OK, ERROR, UNSET
    status_message = Column(String(255), nullable=True)
    # Strictly sanitized, allow-listed attributes JSON (no payloads, no credentials, parameterized SQL)
    attributes_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    tenant = relationship("Tenant", back_populates="trace_spans")

class ServiceNode(Base):
    __tablename__ = "service_nodes"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False, index=True)
    service_type = Column(String(50), default="app_service")  # api_gateway, app_service, database, cache, auth
    health_status = Column(String(20), default="healthy")  # healthy, degraded, down
    avg_latency_ms = Column(Float, default=15.0)
    p95_latency_ms = Column(Float, default=35.0)
    error_rate = Column(Float, default=0.0)  # 0.0 - 1.0 (e.g. 0.02 = 2%)
    throughput_rpm = Column(Float, default=120.0)
    last_seen = Column(DateTime, default=utc_now)
    created_at = Column(DateTime, default=utc_now)

    tenant = relationship("Tenant", back_populates="services")

class ServiceDependency(Base):
    __tablename__ = "service_dependencies"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    caller_service_name = Column(String(100), nullable=False, index=True)
    callee_service_name = Column(String(100), nullable=False, index=True)
    call_count = Column(Integer, default=1)
    avg_duration_ms = Column(Float, default=10.0)
    error_count = Column(Integer, default=0)
    last_interaction = Column(DateTime, default=utc_now)

# ----------------- MACHINE LEARNING & STATISTICAL ANOMALY MODELS -----------------

class MLAnomaly(Base):
    __tablename__ = "ml_anomalies"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    server_id = Column(String(36), ForeignKey("servers.id", ondelete="CASCADE"), nullable=False, index=True)
    algorithm = Column(String(50), nullable=False)  # isolation_forest, z_score, ewma_residual, velocity_spike
    metric_name = Column(String(50), nullable=False)
    observed_value = Column(Float, nullable=False)
    expected_baseline = Column(Float, nullable=False)
    deviation = Column(Float, nullable=False)
    anomaly_score = Column(Float, nullable=False)  # 0.0 - 1.0 calibrated
    severity = Column(String(20), default="medium")  # critical, high, medium, low
    explanation = Column(Text, nullable=False)
    created_at = Column(DateTime, default=utc_now, index=True)

    tenant = relationship("Tenant", back_populates="ml_anomalies")
    server = relationship("Server")

class ModelMetadata(Base):
    __tablename__ = "model_metadata"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    model_name = Column(String(100), nullable=False)
    version = Column(String(20), default="1.0.0")
    algorithm = Column(String(50), nullable=False)
    f1_score = Column(Float, default=0.92)
    precision = Column(Float, default=0.90)
    recall = Column(Float, default=0.94)
    false_positive_rate = Column(Float, default=0.03)
    training_sample_count = Column(Integer, default=1000)
    features_json = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    trained_at = Column(DateTime, default=utc_now)


# ----------------- PHASE 2E: PREDICTIVE ANALYTICS & SLO MODELS -----------------

class ServiceLevelObjective(Base):
    __tablename__ = "slos"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    service_name = Column(String(100), nullable=False, index=True)  # api-gateway, order-service, global, etc.
    sli_type = Column(String(50), nullable=False)  # availability, latency_p95, error_rate, uptime
    target_percentage = Column(Float, nullable=False, default=99.9)  # e.g. 99.9%
    warning_threshold = Column(Float, nullable=False, default=99.0)  # e.g. 99.0%
    latency_threshold_ms = Column(Float, default=250.0)  # for latency SLIs
    rolling_window_days = Column(Integer, default=30)
    current_sli = Column(Float, default=99.95)
    error_budget_total_minutes = Column(Float, default=43.2)  # minutes of allowable downtime in 30 days
    error_budget_remaining_percent = Column(Float, default=100.0)
    burn_rate = Column(Float, default=1.0)  # 1.0 = normal consumption, >2.0 = fast burn, >14.4 = emergency
    status = Column(String(20), default="healthy")  # healthy, warning, breached
    created_at = Column(DateTime, default=utc_now, index=True)

    tenant = relationship("Tenant", back_populates="slos")


class CapacityWarning(Base):
    __tablename__ = "capacity_warnings"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    server_id = Column(String(36), ForeignKey("servers.id", ondelete="CASCADE"), nullable=True, index=True)
    component_name = Column(String(100), nullable=False)
    metric_name = Column(String(50), nullable=False)  # disk_percent, memory_percent, cpu_percent, request_rate_rpm
    current_value = Column(Float, nullable=False)
    threshold_value = Column(Float, default=90.0)
    days_to_exhaustion = Column(Float, nullable=True)  # e.g. 6.4 days
    projected_exhaustion_date = Column(DateTime, nullable=True)
    daily_growth_rate = Column(Float, default=0.0)  # delta % per day
    confidence_score = Column(Float, default=0.90)  # 0.0 - 1.0
    severity = Column(String(20), default="warning")  # critical, high, warning
    recommended_action = Column(Text, nullable=False)
    status = Column(String(20), default="active")  # active, mitigated
    created_at = Column(DateTime, default=utc_now, index=True)

    tenant = relationship("Tenant", back_populates="capacity_warnings")
    server = relationship("Server")


class IntegrationConfig(Base):
    __tablename__ = "integrations"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    integration_type = Column(String(50), nullable=False)  # linux_host, windows_host, docker, fastapi_app, postgres_db, nginx_proxy
    name = Column(String(100), nullable=False)
    status = Column(String(20), default="disconnected")  # connected, degraded, disconnected, unconfigured
    is_simulated = Column(Boolean, default=False)  # True = simulated mock telemetry; False = real live telemetry
    target_endpoint = Column(String(255), nullable=True)
    last_synced_at = Column(DateTime, nullable=True)
    telemetry_count = Column(Integer, default=0)
    config_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    tenant = relationship("Tenant", back_populates="integrations")


class DeviceEnrollmentToken(Base):
    __tablename__ = "device_enrollment_tokens"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    device_name = Column(String(100), nullable=False)
    os_type = Column(String(50), default="windows")  # windows, linux
    environment = Column(String(50), default="production")  # production, staging, development
    description = Column(String(255), nullable=True)
    token_hash = Column(String(64), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    consumed_at = Column(DateTime, nullable=True)
    created_by_user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    is_revoked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utc_now)

    tenant = relationship("Tenant", back_populates="enrollment_tokens")


class DeviceAuditLog(Base):
    __tablename__ = "device_audit_logs"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    collector_id = Column(String(36), ForeignKey("collectors.id", ondelete="SET NULL"), nullable=True, index=True)
    device_name = Column(String(100), nullable=False)
    action = Column(String(50), nullable=False)  # REGISTERED, ENROLLED, HEARTBEAT, TELEMETRY_INGESTED, REVOKED, RE_ENROLLED
    actor = Column(String(100), nullable=False)  # e.g., admin@acme.com, collector-daemon
    ip_address = Column(String(45), nullable=True)
    details_json = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=utc_now, index=True)

    tenant = relationship("Tenant", back_populates="device_audit_logs")
    collector = relationship("Collector", back_populates="audit_logs")

