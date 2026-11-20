# collector/privacy/trace_sanitiser.py
"""
ObserVault OpenTelemetry Trace Privacy Sanitiser.
Enforces strict span attribute allow-listing, parameterizes SQL literals,
and purges all credentials, cookies, headers, and request/response payloads
locally BEFORE traces leave the customer perimeter.
"""

import re
from typing import Dict, Any, Tuple, Optional, List

# Explicit allowable span attributes permitted to egress
APPROVED_SPAN_ATTRIBUTES = {
    "service.name",
    "service.version",
    "http.method",
    "http.status_code",
    "http.route",
    "http.target",
    "http.scheme",
    "db.system",
    "db.name",
    "db.operation",
    "rpc.system",
    "rpc.service",
    "rpc.method",
    "net.peer.name",
    "net.peer.port",
    "net.transport",
    "error.type",
    "component"
}

# Regex patterns to scrub sensitive literals in SQL queries (replaces with ?)
SQL_STRING_LITERAL_PATTERN = re.compile(r"'(?:''|[^'])*'")
SQL_NUMERIC_LITERAL_PATTERN = re.compile(r"\b(?<!\.)\d+(?!\.)\b")

# Sensitive attribute name substrings that trigger immediate purge
SENSITIVE_ATTRIBUTE_SUBSTRINGS = [
    "pass", "token", "key", "auth", "secret", "bearer", "cookie",
    "session", "body", "payload", "email", "ssn", "user", "card"
]

class TracePrivacySanitiser:
    """
    Tier-1 Edge Trace Sanitizer.
    Audits raw OpenTelemetry spans, drops unauthorized attributes,
    and strips database parameters and headers.
    """

    @classmethod
    def sanitize_sql(cls, raw_sql: str) -> str:
        """
        Replaces raw string and numeric literal values in SQL with '?' placeholders.
        Prevents leaking PII and sensitive parameters stored in database query spans.
        Example:
            SELECT * FROM users WHERE email = 'ceo@company.com' AND pin = 1234
            -> SELECT * FROM users WHERE email = ? AND pin = ?
        """
        if not raw_sql:
            return ""
        # 1. Replace quoted strings
        sanitized = SQL_STRING_LITERAL_PATTERN.sub("?", raw_sql)
        # 2. Replace standalone numeric constants in WHERE / VALUES clauses
        # Only scrub numeric values after WHERE, IN, =, <, >, VALUES, etc.
        sanitized = re.sub(r"(=|<|>|LIKE|IN|VALUES\s*\()\s*(\d+)", r"\1 ?", sanitized, flags=re.IGNORECASE)
        return sanitized

    @classmethod
    def sanitize_span(cls, raw_span: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
        """
        Sanitizes a single OpenTelemetry span dictionary.
        Returns:
            (sanitized_span_or_none, privacy_audit_summary)
        """
        raw_attributes = raw_span.get("attributes", {})
        sanitized_attributes: Dict[str, Any] = {}
        stripped_attributes: List[str] = []

        # 1. Audit and filter attributes against allow-list
        for attr_key, attr_val in raw_attributes.items():
            lower_key = attr_key.lower()

            # Immediate rejection if sensitive keyword is found
            if any(s in lower_key for s in SENSITIVE_ATTRIBUTE_SUBSTRINGS):
                stripped_attributes.append(attr_key)
                continue

            # Allow-list validation
            if attr_key in APPROVED_SPAN_ATTRIBUTES:
                # If it's a database statement, scrub literals
                if attr_key == "db.statement":
                    sanitized_attributes["db.statement"] = cls.sanitize_sql(str(attr_val))
                else:
                    # Strings capped to prevent buffer overflow attacks
                    if isinstance(attr_val, str):
                        sanitized_attributes[attr_key] = attr_val[:120]
                    else:
                        sanitized_attributes[attr_key] = attr_val
            else:
                stripped_attributes.append(attr_key)

        # 2. Construct sanitized span record
        sanitized_span = {
            "trace_id": str(raw_span.get("trace_id", "")),
            "span_id": str(raw_span.get("span_id", "")),
            "parent_span_id": raw_span.get("parent_span_id"),
            "service_name": str(raw_span.get("service_name", "unknown_service"))[:100],
            "operation_name": str(raw_span.get("operation_name", "operation"))[:200],
            "span_kind": str(raw_span.get("span_kind", "SERVER")),
            "start_time": raw_span.get("start_time"),
            "end_time": raw_span.get("end_time"),
            "duration_ms": max(0.0, float(raw_span.get("duration_ms", 0.0))),
            "status_code": "ERROR" if raw_span.get("status_code") == "ERROR" else "OK",
            "status_message": str(raw_span.get("status_message") or "")[:255] if raw_span.get("status_message") else None,
            "attributes": sanitized_attributes
        }

        # Safety check: Required identifiers must be non-empty
        if not sanitized_span["trace_id"] or not sanitized_span["span_id"]:
            return None, {
                "valid": False,
                "reason": "Missing trace_id or span_id",
                "stripped_count": len(stripped_attributes)
            }

        audit_summary = {
            "valid": True,
            "approved_attributes_count": len(sanitized_attributes),
            "stripped_attributes_count": len(stripped_attributes),
            "stripped_keys": stripped_attributes,
            "sql_parameterized": "db.statement" in raw_attributes
        }

        return sanitized_span, audit_summary

    @classmethod
    def sanitize_trace_batch(cls, spans: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Sanitizes an entire batch of spans. Drops invalid or unsafe spans.
        """
        approved_spans = []
        total_stripped_keys = 0

        for s in spans:
            sanitized, audit = cls.sanitize_span(s)
            if sanitized:
                approved_spans.append(sanitized)
                total_stripped_keys += audit.get("stripped_attributes_count", 0)

        batch_summary = {
            "received_count": len(spans),
            "approved_count": len(approved_spans),
            "dropped_count": len(spans) - len(approved_spans),
            "total_stripped_attributes": total_stripped_keys
        }

        return approved_spans, batch_summary
