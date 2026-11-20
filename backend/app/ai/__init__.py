# backend/app/ai/__init__.py
"""
ObserVault AI Intelligence Layer (Phase 3).
Provides Groq-powered high-throughput SRE intelligence, root-cause narrative synthesis,
and explainable predictive analytics while preserving strict privacy and tenant isolation.
"""

from app.ai.groq_client import (
    GroqClient,
    GroqClientError,
    GroqAuthenticationError,
    GroqRateLimitError,
    GroqTimeoutError,
    GroqServiceUnavailableError,
    GroqCompletionResult,
    get_groq_client,
    reset_groq_client
)
from app.ai.guardrails import (
    redact_sensitive_data,
    sanitize_untrusted_text,
    enforce_prompt_size_limit,
    validate_remediation_action
)
from app.ai.context_builder import (
    TenantSecurityError,
    build_incident_context,
    build_rca_context,
    build_anomaly_context,
    build_telemetry_context,
    build_predictive_context,
    build_copilot_context
)
from app.ai.prompts import (
    build_incident_prompt,
    build_rca_prompt,
    build_predictive_prompt,
    build_copilot_prompt,
    build_remediation_prompt,
    INCIDENT_EXPLANATION_SYSTEM_PROMPT,
    RCA_EXPLANATION_SYSTEM_PROMPT,
    PREDICTIVE_FORECAST_SYSTEM_PROMPT,
    COPILOT_CHAT_SYSTEM_PROMPT,
    REMEDIATION_PLAN_SYSTEM_PROMPT
)

__all__ = [
    "GroqClient",
    "GroqClientError",
    "GroqAuthenticationError",
    "GroqRateLimitError",
    "GroqTimeoutError",
    "GroqServiceUnavailableError",
    "GroqCompletionResult",
    "get_groq_client",
    "reset_groq_client",
    "redact_sensitive_data",
    "sanitize_untrusted_text",
    "enforce_prompt_size_limit",
    "validate_remediation_action",
    "TenantSecurityError",
    "build_incident_context",
    "build_rca_context",
    "build_anomaly_context",
    "build_telemetry_context",
    "build_predictive_context",
    "build_copilot_context",
    "build_incident_prompt",
    "build_rca_prompt",
    "build_predictive_prompt",
    "build_copilot_prompt",
    "build_remediation_prompt",
    "INCIDENT_EXPLANATION_SYSTEM_PROMPT",
    "RCA_EXPLANATION_SYSTEM_PROMPT",
    "PREDICTIVE_FORECAST_SYSTEM_PROMPT",
    "COPILOT_CHAT_SYSTEM_PROMPT",
    "REMEDIATION_PLAN_SYSTEM_PROMPT"
]
