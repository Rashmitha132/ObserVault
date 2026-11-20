# backend/app/api/traces.py
"""
ObserVault OpenTelemetry Distributed Tracing & Service Dependency Engine.
Provides trace ingestion, tree inspection, service discovery, and dependency graph generation.
"""

import json
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Header
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.database import get_db
from app.api.deps import get_current_user, get_current_collector
from app.models.models import User, Collector, Tenant, TraceSpan, ServiceNode, ServiceDependency

router = APIRouter(prefix="/v2", tags=["OpenTelemetry & Distributed Tracing"])

# Pydantic schemas for trace ingestion
class IngestSpanItem(BaseModel):
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    service_name: str
    operation_name: str
    span_kind: str = "SERVER"
    start_time: datetime
    end_time: datetime
    duration_ms: float
    status_code: str = "OK"  # OK, ERROR
    status_message: Optional[str] = None
    attributes: Dict[str, Any] = Field(default_factory=dict)

class TraceBatchIngest(BaseModel):
    batch_id: str
    collector_id: str
    spans: List[IngestSpanItem]

# ----------------- TRACE INGESTION -----------------

@router.post("/telemetry/traces")
def ingest_traces(
    batch: TraceBatchIngest,
    collector: Collector = Depends(get_current_collector),
    db: Session = Depends(get_db)
):
    """
    Ingests sanitized OpenTelemetry trace spans.
    Automatically updates service node health statistics and infers caller-callee dependencies.
    """
    tenant_id = collector.tenant_id
    now = datetime.now(timezone.utc)
    ingested_spans = 0

    span_map = {s.span_id: s for s in batch.spans}

    for item in batch.spans:
        # Check duplicate
        existing = db.query(TraceSpan).filter(
            TraceSpan.tenant_id == tenant_id,
            TraceSpan.span_id == item.span_id
        ).first()
        if existing:
            continue

        # Create TraceSpan
        span_rec = TraceSpan(
            tenant_id=tenant_id,
            collector_id=collector.id,
            trace_id=item.trace_id,
            span_id=item.span_id,
            parent_span_id=item.parent_span_id,
            service_name=item.service_name,
            operation_name=item.operation_name,
            span_kind=item.span_kind,
            start_time=item.start_time,
            end_time=item.end_time,
            duration_ms=item.duration_ms,
            status_code=item.status_code,
            status_message=item.status_message,
            attributes_json=json.dumps(item.attributes)
        )
        db.add(span_rec)
        ingested_spans += 1

        # Register or update ServiceNode
        service = db.query(ServiceNode).filter(
            ServiceNode.tenant_id == tenant_id,
            ServiceNode.name == item.service_name
        ).first()

        svc_type = "database" if "db." in str(item.attributes) or "db" in item.service_name.lower() \
            else "api_gateway" if "gateway" in item.service_name.lower() \
            else "auth" if "auth" in item.service_name.lower() \
            else "app_service"

        if not service:
            service = ServiceNode(
                tenant_id=tenant_id,
                name=item.service_name,
                service_type=svc_type,
                health_status="degraded" if item.status_code == "ERROR" else "healthy",
                avg_latency_ms=item.duration_ms,
                p95_latency_ms=item.duration_ms * 1.4,
                error_rate=1.0 if item.status_code == "ERROR" else 0.0,
                throughput_rpm=60.0,
                last_seen=now
            )
            db.add(service)
            db.flush()
        else:
            # Running average update
            service.avg_latency_ms = round((service.avg_latency_ms * 0.9) + (item.duration_ms * 0.1), 1)
            service.p95_latency_ms = round(service.avg_latency_ms * 1.5, 1)
            is_err = 1.0 if item.status_code == "ERROR" else 0.0
            service.error_rate = round((service.error_rate * 0.9) + (is_err * 0.1), 3)
            service.health_status = "down" if service.error_rate > 0.5 \
                else "degraded" if service.error_rate > 0.1 or service.avg_latency_ms > 200 \
                else "healthy"
            service.last_seen = now

        # Dynamic Dependency Inference: If span has parent in batch from different service
        if item.parent_span_id and item.parent_span_id in span_map:
            parent_span = span_map[item.parent_span_id]
            if parent_span.service_name != item.service_name:
                dep = db.query(ServiceDependency).filter(
                    ServiceDependency.tenant_id == tenant_id,
                    ServiceDependency.caller_service_name == parent_span.service_name,
                    ServiceDependency.callee_service_name == item.service_name
                ).first()

                if not dep:
                    dep = ServiceDependency(
                        tenant_id=tenant_id,
                        caller_service_name=parent_span.service_name,
                        callee_service_name=item.service_name,
                        call_count=1,
                        avg_duration_ms=item.duration_ms,
                        error_count=1 if item.status_code == "ERROR" else 0,
                        last_interaction=now
                    )
                    db.add(dep)
                else:
                    dep.call_count += 1
                    dep.avg_duration_ms = round((dep.avg_duration_ms * 0.9) + (item.duration_ms * 0.1), 1)
                    if item.status_code == "ERROR":
                        dep.error_count += 1
                    dep.last_interaction = now

    db.commit()
    return {
        "status": "success",
        "batch_id": batch.batch_id,
        "spans_ingested": ingested_spans,
        "timestamp": now.isoformat()
    }

# ----------------- TRACE INSPECTION APIS -----------------

@router.get("/traces")
def list_traces(
    service_name: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None),  # OK, ERROR
    min_duration_ms: Optional[float] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Lists aggregated traces grouped by trace_id with root operation and overall duration.
    """
    tenant_id = current_user.tenant_id
    query = db.query(TraceSpan).filter(TraceSpan.tenant_id == tenant_id)

    if service_name:
        query = query.filter(TraceSpan.service_name == service_name)
    if status_filter:
        query = query.filter(TraceSpan.status_code == status_filter)
    if min_duration_ms:
        query = query.filter(TraceSpan.duration_ms >= min_duration_ms)

    spans = query.order_by(TraceSpan.start_time.desc()).limit(limit * 5).all()

    # Group by trace_id
    traces_dict = {}
    for s in spans:
        if s.trace_id not in traces_dict:
            traces_dict[s.trace_id] = {
                "trace_id": s.trace_id,
                "root_service": s.service_name,
                "root_operation": s.operation_name,
                "start_time": s.start_time.isoformat(),
                "duration_ms": s.duration_ms,
                "span_count": 0,
                "has_error": False,
                "services": set()
            }
        
        t = traces_dict[s.trace_id]
        t["span_count"] += 1
        t["services"].add(s.service_name)
        if s.status_code == "ERROR":
            t["has_error"] = True
        # If this is root span (no parent), use its operation
        if not s.parent_span_id:
            t["root_service"] = s.service_name
            t["root_operation"] = s.operation_name
            t["duration_ms"] = s.duration_ms

    results = []
    for t in traces_dict.values():
        t["services"] = list(t["services"])
        results.append(t)

    return results[:limit]

@router.get("/traces/{trace_id}")
def get_trace_details(
    trace_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns full trace hierarchy with timeline offsets and sanitized span attributes.
    """
    spans = db.query(TraceSpan).filter(
        TraceSpan.tenant_id == current_user.tenant_id,
        TraceSpan.trace_id == trace_id
    ).order_by(TraceSpan.start_time.asc()).all()

    if not spans:
        raise HTTPException(status_code=404, detail="Trace ID not found")

    root_start = spans[0].start_time
    span_list = []

    for s in spans:
        offset_ms = max(0.0, (s.start_time - root_start).total_seconds() * 1000.0)
        span_list.append({
            "id": s.id,
            "span_id": s.span_id,
            "parent_span_id": s.parent_span_id,
            "service_name": s.service_name,
            "operation_name": s.operation_name,
            "span_kind": s.span_kind,
            "start_time": s.start_time.isoformat(),
            "end_time": s.end_time.isoformat(),
            "duration_ms": s.duration_ms,
            "offset_ms": round(offset_ms, 2),
            "status_code": s.status_code,
            "status_message": s.status_message,
            "attributes": json.loads(s.attributes_json or "{}")
        })

    # Calculate total duration
    max_end = max(s.end_time for s in spans)
    total_duration = max(0.0, (max_end - root_start).total_seconds() * 1000.0)

    return {
        "trace_id": trace_id,
        "total_spans": len(spans),
        "total_duration_ms": round(total_duration, 2),
        "root_service": spans[0].service_name,
        "has_error": any(s.status_code == "ERROR" for s in spans),
        "spans": span_list
    }

# ----------------- SERVICE DEPENDENCY & TOPOLOGY -----------------

@router.get("/services")
def list_services(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Lists monitored microservices, databases, and gateways with performance indicators.
    """
    services = db.query(ServiceNode).filter(
        ServiceNode.tenant_id == current_user.tenant_id
    ).all()
    return services

@router.get("/services/dependencies")
def get_service_dependencies(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns the interactive Service Dependency Graph with node health, latency edges,
    and downstream blast-radius impact analysis.
    """
    tenant_id = current_user.tenant_id
    services = db.query(ServiceNode).filter(ServiceNode.tenant_id == tenant_id).all()
    dependencies = db.query(ServiceDependency).filter(ServiceDependency.tenant_id == tenant_id).all()

    # Format nodes
    nodes = []
    for s in services:
        nodes.append({
            "id": s.name,
            "name": s.name,
            "type": s.service_type,
            "status": s.health_status,
            "avg_latency_ms": s.avg_latency_ms,
            "p95_latency_ms": s.p95_latency_ms,
            "error_rate": s.error_rate,
            "throughput_rpm": s.throughput_rpm
        })

    # Format edges
    edges = []
    adjacency = {}
    for d in dependencies:
        edges.append({
            "source": d.caller_service_name,
            "target": d.callee_service_name,
            "call_count": d.call_count,
            "avg_latency_ms": d.avg_duration_ms,
            "error_count": d.error_count,
            "status": "error" if d.error_count > 0 else "nominal"
        })
        adjacency.setdefault(d.caller_service_name, []).append(d.callee_service_name)

    # Compute Blast Radius for degraded / down services
    blast_radius = {}
    for s in services:
        if s.health_status in ["degraded", "down"]:
            # Traverse reverse dependencies (who calls this degraded service?)
            affected_callers = [
                d.caller_service_name for d in dependencies if d.callee_service_name == s.name
            ]
            blast_radius[s.name] = {
                "source_service": s.name,
                "current_status": s.health_status,
                "affected_upstream_callers": affected_callers,
                "estimated_user_impact": "high" if "gateway" in affected_callers or s.service_type == "database" else "medium"
            }

    return {
        "nodes": nodes,
        "edges": edges,
        "total_services": len(nodes),
        "total_dependencies": len(edges),
        "blast_radius_analysis": blast_radius
    }
