# backend/app/ai/guardrails.py
"""
ObserVault AI Guardrails & Privacy Protection Layer (Phase 3 - Step 2).
Provides:
1. Sensitive data redaction (API keys, JWTs, tokens, passwords, connection strings, private keys).
2. Prompt injection defense and untrusted text sanitization.
3. Prompt size budgeting and boundary encapsulation (<telemetry_context> tags).
4. Safe remediation enforcement (no automated execution, multi-party authorization flags for destructive commands).
"""

import re
import html
from typing import Dict, Any, List, Tuple

# Prompt and query length constraints
MAX_QUERY_CHARS = 2000
MAX_PROMPT_CHARS = 16000
MAX_CONTEXT_RECORD_CHARS = 12000

# High-entropy credential and secret regex patterns
REDACTION_PATTERNS: List[Tuple[re.Pattern, str]] = [
    # Private Keys
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----"), "[REDACTED_PRIVATE_KEY]"),
    # Groq API Keys (gsk_...)
    (re.compile(r"gsk_[A-Za-z0-9_-]{16,}"), "[REDACTED_GROQ_KEY]"),
    # ObserVault Collector Operational Keys (ov_col_...)
    (re.compile(r"ov_col_[A-Za-z0-9_-]{16,}"), "[REDACTED_COLLECTOR_KEY]"),
    # OpenAI and Generic sk- API Keys
    (re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"), "[REDACTED_API_KEY]"),
    # AWS Access Keys
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "[REDACTED_AWS_KEY]"),
    # JSON Web Tokens (JWT)
    (re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"), "[REDACTED_JWT]"),
    # Database connection strings with credentials (postgres://user:pass@host)
    (re.compile(r"(?i)\b(postgres(?:ql)?|mysql|mongodb|redis|amqp):\/\/([^:\s]+):([^@\s]+)@"), r"\1://\2:[REDACTED_PASSWORD]@"),
    # Key-value password/secret pairs (password="secret", secret: "...", etc.)
    (re.compile(r"(?i)\b(password|passwd|secret|api_key|token|auth_token)\s*([:=])\s*([\"'])(?:(?=(\\?))\4.)*?\3"), r"\1 \2 \3[REDACTED_CREDENTIAL]\3"),
    # Key-value unquoted password/secret pairs
    (re.compile(r"(?i)\b(password|passwd|secret|api_key|token|auth_token)\s*([:=])\s*([^\s,;'\"]+)"), r"\1 \2 [REDACTED_CREDENTIAL]"),
    # Authorization header style tokens
    (re.compile(r"(?i)\b(Bearer|Basic)\s+[A-Za-z0-9_\-\.\=\+\/]{16,}"), r"\1 [REDACTED_AUTH_TOKEN]"),
]

# Prompt injection signatures
PROMPT_INJECTION_PATTERNS: List[re.Pattern] = [
    re.compile(r"(?i)ignore\s+(all\s+)?(previous|above|prior)\s+(instructions|directives|prompts)"),
    re.compile(r"(?i)disregard\s+(all\s+)?(previous|above|prior)\s+(instructions|rules)"),
    re.compile(r"(?i)override\s+(all\s+)?(system|safety|security)\s+(instructions|prompts|rules)"),
    re.compile(r"(?i)you\s+are\s+now\s+(in\s+)?(dan|developer\s+mode|unrestricted|jailbroken)"),
    re.compile(r"(?i)forget\s+(all\s+)?(your\s+)?(rules|instructions|directives)"),
    re.compile(r"(?i)new\s+system\s+instruction:"),
    re.compile(r"(?i)output\s+(the\s+)?(full\s+)?system\s+prompt"),
    re.compile(r"(?i)<\/?system>"),
    re.compile(r"(?i)<\/?telemetry_context>"),  # Tag boundary spoofing
]

# Destructive command signatures (for safety evaluation of remediation plans)
DESTRUCTIVE_COMMAND_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"(?i)\brm\s+-(?:rf?|fr)\s+[\/\*]"), "Recursive filesystem deletion (rm -rf /)"),
    (re.compile(r"(?i)\bdrop\s+(database|schema|table)\b"), "Database destruction (DROP DATABASE/TABLE)"),
    (re.compile(r"(?i)\btruncate\s+table\b"), "Data truncation (TRUNCATE TABLE)"),
    (re.compile(r"(?i)\bformat\s+[a-z]:"), "Disk volume format (FORMAT C:)"),
    (re.compile(r"(?i)\b(?:reboot|shutdown|init\s+0|halt)\b"), "Host shutdown/reboot command"),
    (re.compile(r"(?i)\bkill\s+-9\s+1\b"), "Init process termination (kill -9 1)"),
    (re.compile(r"(?i)\bmkfs(?:\.[a-z0-9]+)?\b"), "Filesystem creation (mkfs)"),
    (re.compile(r"(?i)\bdd\s+if=.*of=\/dev\b"), "Raw disk block overwrite (dd of=/dev)"),
]


def redact_sensitive_data(text: str) -> str:
    """
    Strips API keys, passwords, bearer tokens, connection strings, and private keys.
    Returns sanitized text.
    """
    if not text or not isinstance(text, str):
        return ""

    sanitized = text
    for pattern, replacement in REDACTION_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)

    return sanitized


def sanitize_untrusted_text(text: str, max_length: int = MAX_QUERY_CHARS) -> str:
    """
    Sanitizes user queries, log lines, and trace metadata before prompt injection:
    - Truncates to max_length.
    - Defangs injection attempts.
    - Escapes boundary spoofing tags.
    - Redacts credentials.
    """
    if not text or not isinstance(text, str):
        return ""

    # 1. Truncate length
    truncated = text[:max_length].strip()

    # 2. Defang injection markers
    for pattern in PROMPT_INJECTION_PATTERNS:
        if pattern.search(truncated):
            truncated = pattern.sub("[FILTERED_INJECTION_ATTEMPT]", truncated)

    # 3. Neutralize context boundary spoofing
    truncated = truncated.replace("<telemetry_context>", "&lt;telemetry_context&gt;")
    truncated = truncated.replace("</telemetry_context>", "&lt;/telemetry_context&gt;")

    # 4. Redact sensitive credentials
    return redact_sensitive_data(truncated)


def enforce_prompt_size_limit(prompt_text: str, max_chars: int = MAX_PROMPT_CHARS) -> str:
    """
    Enforces ceiling on total prompt size to stay safely within Groq model context limits.
    """
    if not prompt_text:
        return ""
    if len(prompt_text) <= max_chars:
        return prompt_text

    excess = len(prompt_text) - max_chars
    safe_cut = prompt_text[:max_chars - 120]
    return f"{safe_cut}\n\n[NOTE: Context safely truncated: {excess} excess characters omitted to fit LLM window.]"


def validate_remediation_action(action_text: str) -> Dict[str, Any]:
    """
    Evaluates proposed remediation action or command for safety:
    - Never permits automated execution (`human_approval_required` is ALWAYS True).
    - Detects destructive commands and flags them for high-risk manual review.
    """
    if not action_text:
        return {
            "safe": True,
            "human_approval_required": True,
            "is_destructive": False,
            "warning": None
        }

    is_destructive = False
    warning = None

    for pattern, desc in DESTRUCTIVE_COMMAND_PATTERNS:
        if pattern.search(action_text):
            is_destructive = True
            warning = f"High-risk command detected: {desc}. Multi-party manual authorization required."
            break

    return {
        "safe": not is_destructive,
        "human_approval_required": True,
        "is_destructive": is_destructive,
        "warning": warning
    }
