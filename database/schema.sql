-- ObserVault PostgreSQL SaaS Multi-Tenant Schema DDL
-- Platform: ObserVault Tier-2 Central SaaS Storage

CREATE TABLE IF NOT EXISTS tenants (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    slug VARCHAR(50) UNIQUE NOT NULL,
    plan VARCHAR(50) DEFAULT 'Enterprise',
    cpu_threshold DOUBLE PRECISION DEFAULT 90.0,
    memory_threshold DOUBLE PRECISION DEFAULT 90.0,
    disk_threshold DOUBLE PRECISION DEFAULT 85.0,
    latency_threshold_ms DOUBLE PRECISION DEFAULT 120.0,
    packet_loss_threshold DOUBLE PRECISION DEFAULT 5.0,
    failed_login_threshold INTEGER DEFAULT 3,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_tenants_slug ON tenants(slug);

CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(36) PRIMARY KEY,
    tenant_id VARCHAR(36) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    role VARCHAR(50) DEFAULT 'engineer',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_users_tenant_email ON users(tenant_id, email);

CREATE TABLE IF NOT EXISTS collectors (
    id VARCHAR(36) PRIMARY KEY,
    tenant_id VARCHAR(36) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    token_hash VARCHAR(64) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    hostname VARCHAR(100) NOT NULL,
    ip_address VARCHAR(45),
    version VARCHAR(20) DEFAULT '1.0.0',
    status VARCHAR(20) DEFAULT 'online',
    collection_interval INTEGER DEFAULT 5,
    buffered_records_count INTEGER DEFAULT 0,
    failed_transmissions_count INTEGER DEFAULT 0,
    last_heartbeat TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_successful_transmission TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_collectors_token ON collectors(token_hash);
CREATE INDEX IF NOT EXISTS idx_collectors_tenant ON collectors(tenant_id);

CREATE TABLE IF NOT EXISTS servers (
    id VARCHAR(36) PRIMARY KEY,
    tenant_id VARCHAR(36) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    collector_id VARCHAR(36) REFERENCES collectors(id) ON DELETE SET NULL,
    hostname VARCHAR(100) NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    ip_address VARCHAR(45),
    os_info VARCHAR(100) DEFAULT 'Linux 6.8 x86_64',
    status VARCHAR(20) DEFAULT 'healthy',
    service_status VARCHAR(20) DEFAULT 'up',
    last_cpu DOUBLE PRECISION DEFAULT 0.0,
    last_memory DOUBLE PRECISION DEFAULT 0.0,
    last_disk DOUBLE PRECISION DEFAULT 0.0,
    last_latency DOUBLE PRECISION DEFAULT 0.0,
    last_packet_loss DOUBLE PRECISION DEFAULT 0.0,
    last_failed_logins INTEGER DEFAULT 0,
    is_simulated BOOLEAN DEFAULT FALSE,
    last_seen TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_servers_tenant_host ON servers(tenant_id, hostname);

CREATE TABLE IF NOT EXISTS telemetry_records (
    id VARCHAR(36) PRIMARY KEY,
    tenant_id VARCHAR(36) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    collector_id VARCHAR(36) REFERENCES collectors(id) ON DELETE SET NULL,
    server_id VARCHAR(36) NOT NULL REFERENCES servers(id) ON DELETE CASCADE,
    event_id VARCHAR(64) UNIQUE NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    cpu_percent DOUBLE PRECISION NOT NULL,
    memory_percent DOUBLE PRECISION NOT NULL,
    disk_percent DOUBLE PRECISION NOT NULL,
    network_latency_ms DOUBLE PRECISION NOT NULL,
    packet_loss_percent DOUBLE PRECISION NOT NULL,
    network_status VARCHAR(20) DEFAULT 'connected',
    failed_login_count INTEGER DEFAULT 0,
    service_status VARCHAR(20) DEFAULT 'up',
    is_simulated BOOLEAN DEFAULT FALSE,
    raw_metadata_json TEXT -- Stores ONLY validated allow-listed metadata; ZERO secrets
);
CREATE INDEX IF NOT EXISTS idx_telemetry_event_id ON telemetry_records(event_id);
CREATE INDEX IF NOT EXISTS idx_telemetry_tenant_time ON telemetry_records(tenant_id, timestamp);

CREATE TABLE IF NOT EXISTS alerts (
    id VARCHAR(36) PRIMARY KEY,
    tenant_id VARCHAR(36) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    server_id VARCHAR(36) NOT NULL REFERENCES servers(id) ON DELETE CASCADE,
    alert_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    metric_name VARCHAR(50) NOT NULL,
    observed_value DOUBLE PRECISION NOT NULL,
    threshold_value DOUBLE PRECISION NOT NULL,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP WITH TIME ZONE
);
CREATE INDEX IF NOT EXISTS idx_alerts_tenant_status ON alerts(tenant_id, status);

CREATE TABLE IF NOT EXISTS incidents (
    id VARCHAR(36) PRIMARY KEY,
    tenant_id VARCHAR(36) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    incident_code VARCHAR(20) UNIQUE NOT NULL,
    title VARCHAR(200) NOT NULL,
    severity VARCHAR(20) DEFAULT 'high',
    status VARCHAR(20) DEFAULT 'open',
    primary_server_id VARCHAR(36) REFERENCES servers(id) ON DELETE SET NULL,
    possible_cause TEXT NOT NULL,
    confidence_score DOUBLE PRECISION DEFAULT 0.85,
    evidence_summary TEXT NOT NULL,
    recommended_actions_json TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP WITH TIME ZONE
);
CREATE INDEX IF NOT EXISTS idx_incidents_tenant_code ON incidents(tenant_id, incident_code);

CREATE TABLE IF NOT EXISTS incident_alerts (
    incident_id VARCHAR(36) NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
    alert_id VARCHAR(36) NOT NULL REFERENCES alerts(id) ON DELETE CASCADE,
    PRIMARY KEY (incident_id, alert_id)
);

CREATE TABLE IF NOT EXISTS recommendations (
    id VARCHAR(36) PRIMARY KEY,
    tenant_id VARCHAR(36) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    incident_id VARCHAR(36) REFERENCES incidents(id) ON DELETE CASCADE,
    alert_id VARCHAR(36) REFERENCES alerts(id) ON DELETE CASCADE,
    severity VARCHAR(20) DEFAULT 'medium',
    category VARCHAR(50) DEFAULT 'infrastructure',
    title VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    rationale TEXT NOT NULL,
    action_steps_json TEXT,
    human_approval_required BOOLEAN DEFAULT TRUE,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS egress_audit (
    id VARCHAR(36) PRIMARY KEY,
    tenant_id VARCHAR(36) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    collector_id VARCHAR(36) REFERENCES collectors(id) ON DELETE SET NULL,
    batch_id VARCHAR(64) NOT NULL,
    total_processed INTEGER DEFAULT 1,
    approved_count INTEGER DEFAULT 1,
    rejected_fields_count INTEGER DEFAULT 0,
    rejected_field_names_json TEXT,
    approved_fields_sample_json TEXT,
    simulated_attack_payload_stripped BOOLEAN DEFAULT FALSE,
    status VARCHAR(20) DEFAULT 'delivered',
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
