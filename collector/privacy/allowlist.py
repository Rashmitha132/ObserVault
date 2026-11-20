# collector/privacy/allowlist.py
"""
ObserVault Explicit Outbound Metadata Allow-List Definition.
Only fields defined here are permitted to be packaged into outbound telemetry records.
All other keys, attributes, and payloads are dropped locally at the edge.
"""

APPROVED_OUTBOUND_KEYS = {
    "event_id",
    "timestamp",
    "server_id",
    "hostname",
    "collector_id",
    "collector_version",
    "cpu_percent",
    "memory_percent",
    "disk_percent",
    "network_latency_ms",
    "packet_loss_percent",
    "network_status",
    "failed_login_count",
    "service_status",
    "is_simulated",
    "privacy_summary"
}

# Known sensitive key patterns that must trigger local security flags
SENSITIVE_KEY_PATTERNS = [
    "pass",
    "password",
    "pwd",
    "secret",
    "token",
    "auth",
    "key",
    "api_key",
    "bearer",
    "credential",
    "user",
    "username",
    "email",
    "payload",
    "body",
    "request",
    "response",
    "cookie",
    "session",
    "sql",
    "query",
    "card",
    "ssn",
    "cvv",
    "pin"
]
