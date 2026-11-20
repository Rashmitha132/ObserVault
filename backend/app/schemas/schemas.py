# backend/app/schemas/schemas.py
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict, field_validator

# ----------------- AUTH SCHEMAS -----------------
class LoginRequest(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    tenant_id: str
    tenant_name: str
    role: str
    email: str
    full_name: str

class UserOut(BaseModel):
    id: str
    tenant_id: str
    tenant_name: Optional[str] = None
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime

# ----------------- TELEMETRY SCHEMAS -----------------
# Strict allow-list of approved fields. Any unexpected field causes validation error.
class PrivacySummary(BaseModel):
    local_processed_count: int = 1
    fields_approved: int
    fields_rejected: int
    rejected_field_names: List[str] = Field(default_factory=list)
    sensitive_data_stripped: bool = True
    sanitization_timestamp: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(extra="forbid")

class OutboundTelemetryRecord(BaseModel):
    event_id: str
    timestamp: datetime
    server_id: str
    hostname: str
    collector_id: str
    collector_version: str = "1.0.0"
    cpu_percent: float = Field(..., ge=0.0, le=100.0)
    memory_percent: float = Field(..., ge=0.0, le=100.0)
    disk_percent: float = Field(..., ge=0.0, le=100.0)
    network_latency_ms: float = Field(..., ge=0.0)
    packet_loss_percent: float = Field(..., ge=0.0, le=100.0)
    network_status: str = Field(default="connected")
    failed_login_count: int = Field(default=0, ge=0)
    service_status: str = Field(default="up")
    is_simulated: bool = False
    privacy_summary: Optional[PrivacySummary] = None

    # CRITICAL: STRICT EXTRA FIELDS FORBIDDEN
    model_config = ConfigDict(extra="forbid")

class TelemetryBatchIngest(BaseModel):
    batch_id: str
    collector_id: str
    records: List[OutboundTelemetryRecord]
    
    # CRITICAL: STRICT EXTRA FIELDS FORBIDDEN
    model_config = ConfigDict(extra="forbid")

# ----------------- COLLECTOR SCHEMAS -----------------
class HeartbeatRequest(BaseModel):
    collector_id: str
    hostname: str
    status: str = "online"
    version: str = "1.0.0"
    collection_interval: int = 5
    buffered_records_count: int = 0
    failed_transmissions_count: int = 0

    model_config = ConfigDict(extra="forbid")

class CollectorOut(BaseModel):
    id: str
    tenant_id: str
    name: str
    hostname: str
    ip_address: Optional[str]
    version: str
    status: str
    collection_interval: int
    buffered_records_count: int
    failed_transmissions_count: int
    last_heartbeat: datetime
    last_successful_transmission: datetime
    created_at: datetime
    os_type: Optional[str] = "windows"
    os_version: Optional[str] = None
    environment: Optional[str] = "production"
    enrollment_status: Optional[str] = "active"
    is_revoked: Optional[bool] = False
    revoked_at: Optional[datetime] = None

# ----------------- DEVICE ONBOARDING & ENROLLMENT (PHASE 2F) -----------------
class DeviceRegisterRequest(BaseModel):
    device_name: str = Field(..., min_length=2, max_length=100)
    os_type: str = Field(default="windows")  # windows, linux
    environment: str = Field(default="production")  # production, staging, development
    description: Optional[str] = Field(default=None, max_length=255)

class DeviceRegisterResponse(BaseModel):
    token_id: str
    device_name: str
    os_type: str
    environment: str
    enrollment_token: str  # ONLY RETURNED ONCE!
    expires_at: datetime
    powershell_command: str
    enroll_cli_command: str

class DeviceEnrollRequest(BaseModel):
    enrollment_token: str
    hostname: str
    os_type: str = "windows"
    os_version: Optional[str] = None
    collector_version: str = "1.0.0"
    ip_address: Optional[str] = None
    machine_guid: Optional[str] = None

class DeviceEnrollResponse(BaseModel):
    collector_id: str
    collector_key: str  # Operational key for subsequent calls
    collector_name: str
    server_id: str
    tenant_id: str
    collection_interval: int
    heartbeat_interval: int
    backend_url: str

class DeviceRevokeResponse(BaseModel):
    collector_id: str
    status: str  # "revoked"
    revoked_at: datetime
    message: str

class DeviceAuditLogOut(BaseModel):
    id: str
    collector_id: Optional[str] = None
    device_name: str
    action: str
    actor: str
    ip_address: Optional[str] = None
    details_json: Optional[str] = None
    timestamp: datetime

class DeviceManagementStats(BaseModel):
    total_devices: int
    online_devices: int
    offline_devices: int
    pending_devices: int
    revoked_devices: int
    collectors: List[CollectorOut]

# ----------------- SERVER & INFRASTRUCTURE -----------------
class ServerOut(BaseModel):
    id: str
    tenant_id: str
    collector_id: Optional[str]
    hostname: str
    display_name: str
    ip_address: Optional[str]
    os_info: str
    status: str
    service_status: str
    last_cpu: float
    last_memory: float
    last_disk: float
    last_latency: float
    last_packet_loss: float
    last_failed_logins: int
    is_simulated: bool
    last_seen: datetime

# ----------------- ALERTS & INCIDENTS -----------------
class AlertOut(BaseModel):
    id: str
    tenant_id: str
    server_id: str
    server_hostname: Optional[str] = None
    alert_type: str
    severity: str
    title: str
    description: str
    metric_name: str
    observed_value: float
    threshold_value: float
    status: str
    created_at: datetime
    resolved_at: Optional[datetime]

class AlertStatusUpdate(BaseModel):
    status: str  # acknowledged, resolved

class IncidentOut(BaseModel):
    id: str
    tenant_id: str
    incident_code: str
    title: str
    severity: str
    status: str
    primary_server_id: Optional[str]
    primary_server_name: Optional[str] = None
    possible_cause: str
    confidence_score: float
    evidence_summary: str
    recommended_actions: List[str] = Field(default_factory=list)
    related_alerts: List[AlertOut] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime]

class IncidentStatusUpdate(BaseModel):
    status: str  # acknowledged, resolved

# ----------------- RECOMMENDATIONS -----------------
class RecommendationOut(BaseModel):
    id: str
    tenant_id: str
    incident_id: Optional[str]
    alert_id: Optional[str]
    severity: str
    category: str
    title: str
    description: str
    rationale: str
    action_steps: List[str] = Field(default_factory=list)
    human_approval_required: bool = True
    status: str
    created_at: datetime

class RecommendationStatusUpdate(BaseModel):
    status: str  # completed, dismissed, acknowledged

# ----------------- EGRESS AUDIT & PRIVACY PROOF -----------------
class EgressAuditOut(BaseModel):
    id: str
    tenant_id: str
    collector_id: Optional[str]
    batch_id: str
    total_processed: int
    approved_count: int
    rejected_fields_count: int
    rejected_field_names: List[str] = Field(default_factory=list)
    approved_fields_sample: Dict[str, Any] = Field(default_factory=dict)
    simulated_attack_payload_stripped: bool
    status: str
    timestamp: datetime

class PrivacyProofResponse(BaseModel):
    total_records_processed_locally: int
    total_records_approved: int
    total_records_rejected: int
    currently_buffered_records: int
    last_successful_transmission: Optional[datetime]
    approved_outbound_fields: List[str]
    rejected_fields_examples: List[str]
    recent_audits: List[EgressAuditOut]
    sample_safe_payload: Dict[str, Any]

class PrivacyVerifyRequest(BaseModel):
    """Used for live demonstration of client-side privacy filtering"""
    raw_event: Dict[str, Any]

class PrivacyVerifyResponse(BaseModel):
    raw_received_field_count: int
    sensitive_fields_detected: List[str]
    approved_outbound_metadata: Dict[str, Any]
    sensitive_data_in_cloud_db: bool = False
    status_message: str

# ----------------- TENANT SETTINGS -----------------
class TenantSettingsUpdate(BaseModel):
    cpu_threshold: Optional[float] = None
    memory_threshold: Optional[float] = None
    disk_threshold: Optional[float] = None
    latency_threshold_ms: Optional[float] = None
    packet_loss_threshold: Optional[float] = None
    failed_login_threshold: Optional[int] = None


# ----------------- PHASE 2E: PREDICTIVE & INTEGRATION SCHEMAS -----------------

class SLOCreateRequest(BaseModel):
    name: str
    service_name: str
    sli_type: str = "availability"  # availability, latency_p95, error_rate, uptime
    target_percentage: float = Field(..., ge=50.0, le=100.0)
    warning_threshold: float = Field(default=99.0, ge=50.0, le=100.0)
    latency_threshold_ms: Optional[float] = 250.0
    rolling_window_days: int = Field(default=30, ge=1, le=90)

class SLOOut(BaseModel):
    id: str
    tenant_id: str
    name: str
    service_name: str
    sli_type: str
    target_percentage: float
    warning_threshold: float
    latency_threshold_ms: Optional[float]
    rolling_window_days: int
    current_sli: float
    error_budget_total_minutes: float
    error_budget_remaining_percent: float
    burn_rate: float
    status: str
    status_message: Optional[str] = None
    created_at: datetime

class CapacityWarningOut(BaseModel):
    id: str
    tenant_id: str
    server_id: Optional[str]
    component_name: str
    metric_name: str
    current_value: float
    threshold_value: float
    days_to_exhaustion: Optional[float]
    projected_exhaustion_date: Optional[datetime]
    daily_growth_rate: float
    confidence_score: float
    severity: str
    recommended_action: str
    status: str
    created_at: datetime

class ForecastDataPoint(BaseModel):
    timestamp: str
    observed_value: Optional[float] = None
    forecasted_value: Optional[float] = None
    upper_bound: Optional[float] = None
    lower_bound: Optional[float] = None

class ResourceForecastResponse(BaseModel):
    server_id: str
    component_name: str
    metric_name: str
    horizon_label: Optional[str] = "7d"
    current_value: float
    slope_per_day: float
    daily_growth_percent: float
    model_used: str
    confidence_level: float
    is_real_telemetry: bool = False
    data_source: Optional[str] = "database_historical_telemetry"
    historical_points: List[ForecastDataPoint]
    forecast_points: List[ForecastDataPoint]
    threshold_value: float
    days_to_threshold: Optional[float]
    projected_breach_date: Optional[str]
    accuracy_evaluation: Optional[Dict[str, Any]] = None
    disclaimer: str
    recommendation: str

class IntegrationOut(BaseModel):
    id: str
    tenant_id: str
    integration_type: str
    name: str
    status: str
    is_simulated: bool
    target_endpoint: Optional[str]
    last_synced_at: Optional[datetime]
    telemetry_count: int
    config_json: Optional[str]
    created_at: datetime

class RealHostTelemetryResponse(BaseModel):
    hostname: str
    os_info: str
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    network_sent_mb: float
    network_recv_mb: float
    process_count: int
    is_simulated: bool = False
    timestamp: datetime

# ----------------- AI INTELLIGENCE SCHEMAS (PHASE 3) -----------------
class AIExplainResponse(BaseModel):
    incident_id: str
    incident_code: Optional[str] = None
    title: Optional[str] = None
    model_used: str
    confirmed_facts: List[str] = Field(default_factory=list)
    causal_hypotheses: List[str] = Field(default_factory=list)
    impact_assessment: Optional[str] = None
    supporting_evidence: List[str] = Field(default_factory=list)
    investigation_suggestions: List[str] = Field(default_factory=list)
    raw_narrative: str
    tokens_used: Optional[int] = None
    latency_ms: Optional[float] = None
    disclaimer: str = "AI-generated analysis grounded in telemetry; human confirmation required."

class AIRCAResponse(BaseModel):
    incident_id: str
    incident_code: Optional[str] = None
    model_used: str
    primary_root_cause: Optional[str] = None
    root_cause_score: Optional[float] = None
    score_type: str = "heuristic_ranking_score"
    explanation: str
    alternative_hypotheses: List[str] = Field(default_factory=list)
    evidence_limitations: List[str] = Field(default_factory=list)
    investigation_steps: List[str] = Field(default_factory=list)
    raw_narrative: str
    tokens_used: Optional[int] = None
    latency_ms: Optional[float] = None
    disclaimer: str = "Heuristic score reflects multi-signal convergence, not calibrated probability."

class AIPredictiveAnalysisRequest(BaseModel):
    metric_name: Optional[str] = "disk_percent"
    horizon: Optional[str] = "7d"

class AIPredictiveAnalysisResponse(BaseModel):
    server_id: str
    server_hostname: Optional[str] = None
    metric_name: str
    horizon: str
    model_used: str
    current_value: float
    daily_growth_percent: float
    days_to_threshold: Optional[float] = None
    projected_breach_date: Optional[str] = None
    trend_interpretation: str
    capacity_risks: List[str] = Field(default_factory=list)
    confidence_assessment: str
    prediction_limitations: List[str] = Field(default_factory=list)
    actionable_recommendations: List[str] = Field(default_factory=list)
    raw_narrative: str
    tokens_used: Optional[int] = None
    latency_ms: Optional[float] = None
    disclaimer: str = "Statistical projection based on historical OLS linear velocity; not a guarantee."

class AICopilotChatRequest(BaseModel):
    message: str
    incident_id: Optional[str] = None
    server_id: Optional[str] = None
    conversation_history: Optional[List[Dict[str, str]]] = None
    incident_limit: Optional[int] = Field(10, ge=1, le=25)
    incident_offset: Optional[int] = Field(0, ge=0)

class AICopilotChatResponse(BaseModel):
    answer: str
    model_used: str
    cites_evidence: List[str] = Field(default_factory=list)
    telemetry_status: str = "AVAILABLE"
    tokens_used: Optional[int] = None
    latency_ms: Optional[float] = None

class RemediationStepOut(BaseModel):
    step_number: int
    action: str
    target_component: str
    risk_level: str  # low | medium | high
    rationale: str
    rollback_procedure: str
    requires_human_approval: bool = True

class AIRemediationPlanResponse(BaseModel):
    incident_id: str
    incident_code: Optional[str] = None
    model_used: str
    strategy_overview: str
    prioritized_steps: List[RemediationStepOut] = Field(default_factory=list)
    post_remediation_checks: List[str] = Field(default_factory=list)
    human_approval_required: bool = True
    automated_execution_allowed: bool = False
    raw_narrative: str
    tokens_used: Optional[int] = None
    latency_ms: Optional[float] = None
    disclaimer: str = "Remediation recommendations must be manually verified and approved by an authorized engineer."
