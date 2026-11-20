# collector/instrumentation/fastapi_instrumentor.py
"""
ObserVault OpenTelemetry Instrumentation & Sample Trace Generator.
Demonstrates realistic multi-tier distributed tracing across:
api-gateway -> order-service -> postgres-db / payment-gateway
Applies local TracePrivacySanitiser before transmission to guarantee zero credential leak.
"""

import uuid
import time
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
from collector.privacy.trace_sanitiser import TracePrivacySanitiser

class TraceGenerator:
    """
    Simulates distributed microservice request paths with real timing and span relationships.
    Automatically applies edge sanitization.
    """

    @classmethod
    def generate_distributed_trace(
        cls,
        trace_id: str = None,
        simulate_error: bool = False,
        error_service: str = "postgres-db"
    ) -> List[Dict[str, Any]]:
        """
        Simulates:
        [api-gateway: GET /api/v1/orders] (Span 1, root)
           ├── [order-service: FetchOrderDetails] (Span 2)
           │      └── [postgres-db: SELECT * FROM orders WHERE id = 1042] (Span 3)
           └── [payment-service: CheckPaymentStatus] (Span 4)
        """
        trace_id = trace_id or f"trace-{uuid.uuid4().hex}"
        now = datetime.now(timezone.utc)

        # 1. Root Span: API Gateway
        span1_id = f"span-{uuid.uuid4().hex[:12]}"
        span1_start = now
        span1_duration = 185.0 if simulate_error else 45.0
        span1_end = span1_start + timedelta(milliseconds=span1_duration)

        raw_span1 = {
            "trace_id": trace_id,
            "span_id": span1_id,
            "parent_span_id": None,
            "service_name": "api-gateway",
            "operation_name": "GET /api/v1/orders/{order_id}",
            "span_kind": "SERVER",
            "start_time": span1_start.isoformat(),
            "end_time": span1_end.isoformat(),
            "duration_ms": span1_duration,
            "status_code": "ERROR" if simulate_error else "OK",
            "status_message": "Downstream dependency failure" if simulate_error else None,
            "attributes": {
                "http.method": "GET",
                "http.route": "/api/v1/orders/{order_id}",
                "http.status_code": 500 if simulate_error else 200,
                "net.peer.name": "192.168.1.150",
                # SENSITIVE KEYS THAT MUST BE DROPPED LOCALLY:
                "authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.secret_auth_token_sample",
                "cookie": "session_id=s%3Aabc123secret; user_email=customer@corp.com",
                "user_password": "PlaintextPasswordThatMustBePurged!"
            }
        }

        # 2. Child Span: Order Service
        span2_id = f"span-{uuid.uuid4().hex[:12]}"
        span2_start = span1_start + timedelta(milliseconds=5.0)
        span2_duration = 140.0 if simulate_error else 28.0
        span2_end = span2_start + timedelta(milliseconds=span2_duration)

        raw_span2 = {
            "trace_id": trace_id,
            "span_id": span2_id,
            "parent_span_id": span1_id,
            "service_name": "order-service",
            "operation_name": "OrderService.FetchOrderDetails",
            "span_kind": "INTERNAL",
            "start_time": span2_start.isoformat(),
            "end_time": span2_end.isoformat(),
            "duration_ms": span2_duration,
            "status_code": "ERROR" if simulate_error and error_service in ["order-service", "postgres-db"] else "OK",
            "attributes": {
                "service.name": "order-service",
                "component": "order_manager",
                "order_id": "ORD-9942",
                # Sensitive request body payload that must be pruned:
                "request.body": "{\"user\": \"alice\", \"credit_card\": \"4111-2222-3333-4444\"}"
            }
        }

        # 3. Leaf Span: Postgres DB (Database query)
        span3_id = f"span-{uuid.uuid4().hex[:12]}"
        span3_start = span2_start + timedelta(milliseconds=8.0)
        span3_duration = 125.0 if simulate_error and error_service == "postgres-db" else 14.0
        span3_end = span3_start + timedelta(milliseconds=span3_duration)

        raw_span3 = {
            "trace_id": trace_id,
            "span_id": span3_id,
            "parent_span_id": span2_id,
            "service_name": "postgres-db",
            "operation_name": "SELECT orders",
            "span_kind": "CLIENT",
            "start_time": span3_start.isoformat(),
            "end_time": span3_end.isoformat(),
            "duration_ms": span3_duration,
            "status_code": "ERROR" if simulate_error and error_service == "postgres-db" else "OK",
            "status_message": "Query timeout exceeded: lock contention" if simulate_error else None,
            "attributes": {
                "db.system": "postgresql",
                "db.name": "production_orders",
                "db.operation": "SELECT",
                # Literal values in SQL statement that must be parameterized to ?
                "db.statement": "SELECT * FROM orders WHERE customer_id = 'cust_9872' AND pin_code = 560034"
            }
        }

        # 4. Sibling Span: Payment Service (Client call)
        span4_id = f"span-{uuid.uuid4().hex[:12]}"
        span4_start = span1_start + timedelta(milliseconds=12.0)
        span4_duration = 18.0
        span4_end = span4_start + timedelta(milliseconds=span4_duration)

        raw_span4 = {
            "trace_id": trace_id,
            "span_id": span4_id,
            "parent_span_id": span1_id,
            "service_name": "payment-gateway",
            "operation_name": "PaymentClient.VerifyPayment",
            "span_kind": "CLIENT",
            "start_time": span4_start.isoformat(),
            "end_time": span4_end.isoformat(),
            "duration_ms": span4_duration,
            "status_code": "OK",
            "attributes": {
                "rpc.system": "grpc",
                "rpc.service": "PaymentVerificationService",
                "net.peer.name": "payment-internal.finance.local",
                "net.peer.port": 50051
            }
        }

        raw_spans = [raw_span1, raw_span2, raw_span3, raw_span4]

        # Apply Local Edge Privacy Filter before export
        sanitized_spans, summary = TracePrivacySanitiser.sanitize_trace_batch(raw_spans)
        return sanitized_spans
