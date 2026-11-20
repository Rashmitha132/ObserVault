# tests/test_opentelemetry_traces.py
"""
Test Suite for ObserVault Phase 2B: OpenTelemetry Advanced Observability.
Validates trace privacy sanitization, SQL literal parameterization,
distributed trace ingestion, tree inspection, and service dependency mapping.
"""

import sys
import os
import uuid
import json
from datetime import datetime, timezone, timedelta

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, root_dir)
sys.path.insert(0, os.path.join(root_dir, "backend"))

from app.core.database import SessionLocal
from app.models.models import Tenant, Collector, TraceSpan, ServiceNode, ServiceDependency
from collector.privacy.trace_sanitiser import TracePrivacySanitiser
from collector.instrumentation.fastapi_instrumentor import TraceGenerator

def test_trace_privacy_sanitizer_allowlist():
    """Validates that span attributes not on the allow-list are pruned."""
    raw_span = {
        "trace_id": "test-trc-100",
        "span_id": "test-spn-101",
        "service_name": "checkout-service",
        "operation_name": "ProcessPayment",
        "attributes": {
            "http.method": "POST",
            "http.status_code": 200,
            "internal_worker_pid": 14920,       # Unapproved attribute
            "custom_telemetry_debug": "verbose"  # Unapproved attribute
        }
    }

    sanitized, audit = TracePrivacySanitiser.sanitize_span(raw_span)
    assert sanitized is not None
    assert "http.method" in sanitized["attributes"]
    assert "http.status_code" in sanitized["attributes"]
    assert "internal_worker_pid" not in sanitized["attributes"]
    assert "custom_telemetry_debug" not in sanitized["attributes"]
    assert audit["stripped_attributes_count"] == 2

def test_trace_privacy_sql_parameterization():
    """Tests that SQL literals are parameterized to '?' placeholders to prevent data leakage."""
    raw_sql = "SELECT id, balance FROM accounts WHERE user_id = 'alice_smith_99' AND pin = 4321 AND active = 1"
    sanitized_sql = TracePrivacySanitiser.sanitize_sql(raw_sql)

    assert "alice_smith_99" not in sanitized_sql
    assert "4321" not in sanitized_sql
    assert "?" in sanitized_sql
    assert "WHERE user_id = ?" in sanitized_sql

def test_trace_privacy_purges_tokens_and_bodies():
    """Assures credentials, cookies, and raw payloads are dropped locally before egress."""
    raw_span = {
        "trace_id": "test-trc-sec-01",
        "span_id": "test-spn-sec-02",
        "service_name": "user-auth",
        "operation_name": "LoginHandler",
        "attributes": {
            "http.method": "POST",
            "authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.sample_jwt",
            "cookie": "session_id=secret_session_token_123",
            "user_password": "PlainTextSuperSecretPassword!",
            "request.body": "{\"username\": \"admin\", \"password\": \"secret\"}"
        }
    }

    sanitized, audit = TracePrivacySanitiser.sanitize_span(raw_span)
    assert sanitized is not None
    for sensitive_key in ["authorization", "cookie", "user_password", "request.body"]:
        assert sensitive_key not in sanitized["attributes"]
    assert audit["stripped_attributes_count"] == 4

def test_trace_generator_multi_tier_pipeline():
    """Tests generation of multi-hop distributed spans with sanitized attributes."""
    spans = TraceGenerator.generate_distributed_trace(simulate_error=False)
    assert len(spans) == 4

    services = [s["service_name"] for s in spans]
    assert "api-gateway" in services
    assert "order-service" in services
    assert "postgres-db" in services
    assert "payment-gateway" in services

    # Verify that raw passwords or authorization tokens are absent across all generated spans
    for s in spans:
        attrs = s.get("attributes", {})
        assert "authorization" not in attrs
        assert "cookie" not in attrs
        assert "user_password" not in attrs
        if "db.statement" in attrs:
            assert "cust_9872" not in attrs["db.statement"]  # Sanitized to ?

def test_trace_ingestion_and_hierarchy():
    """Simulates database ingestion of a distributed trace and verifies span hierarchy."""
    db = SessionLocal()
    try:
        tenant = db.query(Tenant).filter(Tenant.slug == "acme-fintech").first()
        collector = db.query(Collector).filter(Collector.tenant_id == tenant.id).first()

        spans = TraceGenerator.generate_distributed_trace()
        trace_id = spans[0]["trace_id"]

        span_map = {s["span_id"]: s for s in spans}
        now = datetime.now(timezone.utc)

        for s in spans:
            start_dt = datetime.fromisoformat(s["start_time"])
            end_dt = datetime.fromisoformat(s["end_time"])
            span_rec = TraceSpan(
                tenant_id=tenant.id,
                collector_id=collector.id,
                trace_id=s["trace_id"],
                span_id=s["span_id"],
                parent_span_id=s.get("parent_span_id"),
                service_name=s["service_name"],
                operation_name=s["operation_name"],
                span_kind=s.get("span_kind", "SERVER"),
                start_time=start_dt,
                end_time=end_dt,
                duration_ms=s["duration_ms"],
                status_code=s["status_code"],
                status_message=s.get("status_message"),
                attributes_json=json.dumps(s.get("attributes", {}))
            )
            db.add(span_rec)

            # Auto-create or update ServiceNode
            svc = db.query(ServiceNode).filter(
                ServiceNode.tenant_id == tenant.id,
                ServiceNode.name == s["service_name"]
            ).first()
            if not svc:
                svc = ServiceNode(
                    tenant_id=tenant.id,
                    name=s["service_name"],
                    service_type="app_service",
                    health_status="healthy",
                    avg_latency_ms=s["duration_ms"],
                    last_seen=now
                )
                db.add(svc)

            # Track dependency
            if s.get("parent_span_id") and s["parent_span_id"] in span_map:
                parent = span_map[s["parent_span_id"]]
                if parent["service_name"] != s["service_name"]:
                    dep = db.query(ServiceDependency).filter(
                        ServiceDependency.tenant_id == tenant.id,
                        ServiceDependency.caller_service_name == parent["service_name"],
                        ServiceDependency.callee_service_name == s["service_name"]
                    ).first()
                    if not dep:
                        dep = ServiceDependency(
                            tenant_id=tenant.id,
                            caller_service_name=parent["service_name"],
                            callee_service_name=s["service_name"],
                            call_count=1,
                            avg_duration_ms=s["duration_ms"],
                            last_interaction=now
                        )
                        db.add(dep)

        db.commit()

        # Query back trace
        db_spans = db.query(TraceSpan).filter(
            TraceSpan.tenant_id == tenant.id,
            TraceSpan.trace_id == trace_id
        ).all()
        assert len(db_spans) == 4

        root_span = next((s for s in db_spans if s.parent_span_id is None), None)
        assert root_span is not None
        assert root_span.service_name == "api-gateway"

        # Verify dependency created
        gateway_dep = db.query(ServiceDependency).filter(
            ServiceDependency.tenant_id == tenant.id,
            ServiceDependency.caller_service_name == "api-gateway",
            ServiceDependency.callee_service_name == "order-service"
        ).first()
        assert gateway_dep is not None

    finally:
        db.close()
