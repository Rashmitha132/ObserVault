# backend/app/ai/context_builder.py
"""
ObserVault Grounded AI Context Builder (Phase 3 - Step 2).
Aggregates authentic observability data from SQLite/PostgreSQL into privacy-sanitized,
token-budgeted context dictionaries for LLM prompts.

Key Guarantees:
1. Strict Multi-Tenant Isolation: Every query enforces `tenant_id == authenticated_user.tenant_id`.
2. Empirical Grounding: Sourced solely from real telemetry, alerts, traces, RCA, and predictive records.
3. Anti-Hallucination Labeling: Distinguishes measured zero from missing telemetry.
4. Privacy Sanitization: Strips API keys, passwords, and tokens before context generation.
5. Strict Record and Size Limits: Caps results and time windows to avoid context bloat.
"""

import json
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, or_

from app.models.models import (
    Incident,
    Alert,
    Server,
    TelemetryRecord,
    MLAnomaly,
    TraceSpan,
    ServiceNode,
    ServiceDependency,
    ServiceLevelObjective,
    CapacityWarning
)
from app.correlation.rca_engine import RootCauseAnalysisEngine
from app.detection.predictive_engine import PredictiveEngine
from app.ai.guardrails import redact_sensitive_data, MAX_CONTEXT_RECORD_CHARS


class TenantSecurityError(Exception):
    """Raised when an attempt is made to access cross-tenant data or an entity not in tenant."""
    pass


def _iso(dt: Optional[datetime]) -> Optional[str]:
    """Helper to safely format datetime to ISO string."""
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def build_incident_context(
    db: Session,
    tenant_id: str,
    incident_id: str
) -> Dict[str, Any]:
    """
    Builds verified factual context for an incident.
    Enforces strict tenant scoping.
    """
    incident = db.query(Incident).filter(
        Incident.id == incident_id,
        Incident.tenant_id == tenant_id
    ).first()

    if not incident:
        raise TenantSecurityError(f"Incident '{incident_id}' not found in the current organization.")

    # 1. Primary Server details
    primary_server_info = None
    if incident.primary_server_id:
        srv = db.query(Server).filter(
            Server.id == incident.primary_server_id,
            Server.tenant_id == tenant_id
        ).first()
        if srv:
            primary_server_info = {
                "server_id": srv.id,
                "hostname": srv.hostname,
                "display_name": srv.display_name,
                "status": srv.status,
                "os_info": srv.os_info,
                "last_seen": _iso(srv.last_seen)
            }

    # 2. Associated Alerts (max 20)
    alerts_data = []
    alerts = incident.alerts or []
    for a in alerts[:20]:
        if a.tenant_id != tenant_id:
            continue
        a_srv = db.query(Server).filter(
            Server.id == a.server_id,
            Server.tenant_id == tenant_id
        ).first()
        alerts_data.append({
            "alert_id": a.id,
            "title": redact_sensitive_data(a.title),
            "severity": a.severity,
            "metric_name": a.metric_name,
            "observed_value": a.observed_value,
            "threshold_value": a.threshold_value,
            "server_hostname": a_srv.hostname if a_srv else "unknown",
            "created_at": _iso(a.created_at),
            "status": a.status
        })

    # 3. Recent Telemetry Records around incident window (max 20)
    telemetry_samples = []
    if incident.primary_server_id:
        records = db.query(TelemetryRecord).filter(
            TelemetryRecord.server_id == incident.primary_server_id,
            TelemetryRecord.tenant_id == tenant_id
        ).order_by(TelemetryRecord.timestamp.desc()).limit(20).all()

        for r in records:
            telemetry_samples.append({
                "timestamp": _iso(r.timestamp),
                "cpu_percent": r.cpu_percent,
                "memory_percent": r.memory_percent,
                "disk_percent": r.disk_percent,
                "network_latency_ms": r.network_latency_ms,
                "packet_loss_percent": r.packet_loss_percent,
                "is_simulated": r.is_simulated
            })

    # 4. Action steps from database
    actions = []
    try:
        actions = json.loads(incident.recommended_actions_json or "[]")
    except Exception:
        actions = []

    return {
        "tenant_id": tenant_id,
        "incident_id": incident.id,
        "incident_code": incident.incident_code,
        "title": redact_sensitive_data(incident.title),
        "severity": incident.severity,
        "status": incident.status,
        "created_at": _iso(incident.created_at),
        "confidence_score": round(incident.confidence_score * 100, 1),
        "primary_server": primary_server_info,
        "confirmed_alerts_count": len(alerts_data),
        "confirmed_alerts": alerts_data,
        "telemetry_samples_count": len(telemetry_samples),
        "recent_telemetry_samples": telemetry_samples,
        "possible_cause_preliminary": redact_sensitive_data(incident.possible_cause or "Under investigation"),
        "stored_recommended_actions": [redact_sensitive_data(str(act)) for act in actions]
    }


def build_rca_context(
    db: Session,
    tenant_id: str,
    incident_id: str
) -> Dict[str, Any]:
    """
    Builds grounded context from the existing RootCauseAnalysisEngine.
    Enforces strict tenant scoping.
    """
    # Verify incident belongs to tenant
    incident = db.query(Incident).filter(
        Incident.id == incident_id,
        Incident.tenant_id == tenant_id
    ).first()

    if not incident:
        raise TenantSecurityError(f"Incident '{incident_id}' not found in current organization.")

    # Execute deterministic RCA
    analysis = RootCauseAnalysisEngine.analyze_incident(
        db=db,
        tenant_id=tenant_id,
        incident_id=incident_id
    )

    primary_hyp = analysis.get("primary_root_cause_hypothesis")
    ranked_candidates = analysis.get("ranked_candidates", [])
    timeline = analysis.get("incident_timeline", [])
    blast = analysis.get("blast_radius", {})
    investigation_steps = analysis.get("suggested_investigation_steps", [])

    return {
        "tenant_id": tenant_id,
        "incident_id": incident_id,
        "incident_code": incident.incident_code,
        "title": redact_sensitive_data(incident.title),
        "severity": incident.severity,
        "heuristic_score_type": analysis.get("score_type", "heuristic_root_cause_score"),
        "primary_root_cause_hypothesis": primary_hyp,
        "ranked_candidates_count": len(ranked_candidates),
        "ranked_candidates": ranked_candidates[:5],  # Top 5
        "timeline_events_count": len(timeline),
        "timeline_events": timeline[:15],           # Top 15 chronological events
        "blast_radius": {
            "originating_suspect": blast.get("originating_suspect"),
            "directly_affected_services": blast.get("directly_affected_services", []),
            "indirectly_affected_services": blast.get("indirectly_affected_services", []),
            "total_services_impacted": blast.get("total_services_impacted", 0),
            "user_impact_level": blast.get("user_impact_level", "low")
        },
        "investigation_steps": investigation_steps
    }


def build_anomaly_context(
    db: Session,
    tenant_id: str,
    hours: int = 2,
    server_id: Optional[str] = None,
    limit: int = 15
) -> Dict[str, Any]:
    """
    Builds context of recent statistical & IsolationForest anomalies.
    Enforces strict tenant scoping.
    """
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=hours)

    query = db.query(MLAnomaly).filter(
        MLAnomaly.tenant_id == tenant_id,
        MLAnomaly.created_at >= cutoff
    )

    if server_id:
        srv = db.query(Server).filter(Server.id == server_id, Server.tenant_id == tenant_id).first()
        if not srv:
            raise TenantSecurityError(f"Server '{server_id}' not found in current organization.")
        query = query.filter(MLAnomaly.server_id == server_id)

    anomalies = query.order_by(MLAnomaly.created_at.desc()).limit(limit).all()

    items = []
    for a in anomalies:
        srv = db.query(Server).filter(Server.id == a.server_id, Server.tenant_id == tenant_id).first()
        items.append({
            "anomaly_id": a.id,
            "algorithm": a.algorithm,
            "metric_name": a.metric_name,
            "severity": a.severity,
            "server_hostname": srv.hostname if srv else "unknown",
            "anomaly_score": a.anomaly_score,
            "observed_value": a.observed_value,
            "expected_baseline": a.expected_baseline,
            "deviation": a.deviation,
            "explanation": redact_sensitive_data(a.explanation),
            "created_at": _iso(a.created_at)
        })

    return {
        "tenant_id": tenant_id,
        "time_window_hours": hours,
        "total_anomalies_detected": len(items),
        "anomalies": items
    }


def build_telemetry_context(
    db: Session,
    tenant_id: str,
    server_id: str,
    hours: int = 1,
    limit: int = 30
) -> Dict[str, Any]:
    """
    Builds historical time-series telemetry context for a specific server.
    Clearly distinguishes zero values from missing samples.
    """
    srv = db.query(Server).filter(
        Server.id == server_id,
        Server.tenant_id == tenant_id
    ).first()

    if not srv:
        raise TenantSecurityError(f"Server '{server_id}' not found in current organization.")

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=hours)

    records = db.query(TelemetryRecord).filter(
        TelemetryRecord.server_id == server_id,
        TelemetryRecord.tenant_id == tenant_id,
        TelemetryRecord.timestamp >= cutoff
    ).order_by(TelemetryRecord.timestamp.desc()).limit(limit).all()

    if not records:
        return {
            "tenant_id": tenant_id,
            "server_id": server_id,
            "hostname": srv.hostname,
            "display_name": srv.display_name,
            "status": srv.status,
            "telemetry_status": "MISSING_DATA",
            "message": "No telemetry samples recorded in the specified time window.",
            "sample_count": 0,
            "samples": []
        }

    samples = []
    for r in records:
        samples.append({
            "timestamp": _iso(r.timestamp),
            "cpu_percent": r.cpu_percent,
            "memory_percent": r.memory_percent,
            "disk_percent": r.disk_percent,
            "network_latency_ms": r.network_latency_ms,
            "packet_loss_percent": r.packet_loss_percent,
            "failed_logins": r.failed_login_count,
            "is_simulated": r.is_simulated
        })

    return {
        "tenant_id": tenant_id,
        "server_id": server_id,
        "hostname": srv.hostname,
        "display_name": srv.display_name,
        "status": srv.status,
        "telemetry_status": "AVAILABLE",
        "sample_count": len(samples),
        "samples": samples
    }


def build_predictive_context(
    db: Session,
    tenant_id: str,
    server_id: str,
    metric_name: str = "disk_percent",
    horizon: str = "7d"
) -> Dict[str, Any]:
    """
    Builds capacity forecasting and SLO context using PredictiveEngine.
    Enforces strict tenant scoping and accuracy metrics (MAE/RMSE).
    """
    srv = db.query(Server).filter(
        Server.id == server_id,
        Server.tenant_id == tenant_id
    ).first()

    if not srv:
        raise TenantSecurityError(f"Server '{server_id}' not found in current organization.")

    # Call audited PredictiveEngine
    forecast = PredictiveEngine.generate_server_forecast(
        db=db,
        tenant_id=tenant_id,
        server_id=server_id,
        metric_name=metric_name,
        horizon=horizon
    )

    # Active capacity warnings for this server
    warnings = db.query(CapacityWarning).filter(
        CapacityWarning.tenant_id == tenant_id,
        CapacityWarning.server_id == server_id,
        CapacityWarning.status == "active"
    ).all()

    warnings_data = [
        {
            "warning_id": w.id,
            "metric_name": w.metric_name,
            "severity": w.severity,
            "days_to_exhaustion": w.days_to_exhaustion,
            "action_advice": redact_sensitive_data(w.recommended_action),
            "created_at": _iso(w.created_at)
        }
        for w in warnings
    ]

    return {
        "tenant_id": tenant_id,
        "server_id": server_id,
        "hostname": srv.hostname,
        "display_name": srv.display_name,
        "metric_name": metric_name,
        "horizon": horizon,
        "forecast": forecast,
        "active_capacity_warnings": warnings_data
    }


def build_copilot_context(
    db: Session,
    tenant_id: str,
    query_text: str = "",
    incident_id: Optional[str] = None,
    server_id: Optional[str] = None,
    incident_limit: int = 10,
    incident_offset: int = 0
) -> Dict[str, Any]:
    """
    Builds high-level holistic cluster context for interactive SRE Copilot chat.
    Enforces strict tenant scoping across all infrastructure entities.
    Clearly distinguishes measured 0.0 values from missing/stale telemetry.
    Computes tenant-wide open incidents independently from bounded prompt retrieval.
    Ensures every incident is represented as an independent structured record with 'Unavailable' defaults.
    """
    now = datetime.now(timezone.utc)
    STALE_THRESHOLD_SECONDS = 180  # 3 minutes

    # 1. Monitored servers breakdown & Health Counts
    servers = db.query(Server).filter(Server.tenant_id == tenant_id).order_by(Server.hostname.asc()).all()
    
    server_summary = {
        "total_servers": len(servers),
        "healthy": sum(1 for s in servers if s.status == "healthy"),
        "warning": sum(1 for s in servers if s.status == "warning"),
        "critical": sum(1 for s in servers if s.status == "critical"),
        "offline": sum(1 for s in servers if s.status == "offline")
    }

    # Latest telemetry across the entire tenant
    latest_telemetry_rec = db.query(TelemetryRecord).filter(
        TelemetryRecord.tenant_id == tenant_id
    ).order_by(TelemetryRecord.timestamp.desc()).first()

    if latest_telemetry_rec and latest_telemetry_rec.timestamp:
        rec_dt = latest_telemetry_rec.timestamp.replace(tzinfo=timezone.utc) if latest_telemetry_rec.timestamp.tzinfo is None else latest_telemetry_rec.timestamp
        tenant_age_seconds = max(0.0, round((now - rec_dt).total_seconds(), 1))
        is_tenant_stale = tenant_age_seconds > STALE_THRESHOLD_SECONDS
        latest_telemetry_ts = _iso(latest_telemetry_rec.timestamp)
        telemetry_health = "STALE" if is_tenant_stale else "ACTIVE"
        telemetry_freshness_label = f"STALE (Age: {tenant_age_seconds}s > {STALE_THRESHOLD_SECONDS}s threshold)" if is_tenant_stale else f"ACTIVE (Age: {tenant_age_seconds}s)"
    else:
        latest_telemetry_ts = "Unavailable"
        tenant_age_seconds = None
        is_tenant_stale = True
        telemetry_health = "NO_TELEMETRY"
        telemetry_freshness_label = "NO_TELEMETRY (No telemetry records found for tenant)"

    server_summary["latest_telemetry_timestamp"] = latest_telemetry_ts
    server_summary["is_telemetry_stale"] = is_tenant_stale
    server_summary["telemetry_age_seconds"] = tenant_age_seconds
    server_summary["telemetry_health"] = telemetry_health
    server_summary["telemetry_freshness_label"] = telemetry_freshness_label

    monitored_servers = []
    for s in servers[:15]:
        server_latest = db.query(TelemetryRecord).filter(
            TelemetryRecord.tenant_id == tenant_id,
            TelemetryRecord.server_id == s.id
        ).order_by(TelemetryRecord.timestamp.desc()).first()

        if server_latest and server_latest.timestamp:
            s_dt = server_latest.timestamp.replace(tzinfo=timezone.utc) if server_latest.timestamp.tzinfo is None else server_latest.timestamp
            s_age = max(0.0, round((now - s_dt).total_seconds(), 1))
            s_stale = s_age > STALE_THRESHOLD_SECONDS
            s_ts = _iso(server_latest.timestamp)
            cpu_val = round(server_latest.cpu_percent, 1) if server_latest.cpu_percent is not None else "Unavailable"
            mem_val = round(server_latest.memory_percent, 1) if server_latest.memory_percent is not None else "Unavailable"
            disk_val = round(server_latest.disk_percent, 1) if server_latest.disk_percent is not None else "Unavailable"
            tel_status = "STALE" if s_stale else "ACTIVE"
        else:
            s_age = None
            s_stale = True
            s_ts = "Unavailable"
            cpu_val = "Missing (No Telemetry)"
            mem_val = "Missing (No Telemetry)"
            disk_val = "Missing (No Telemetry)"
            tel_status = "NO_TELEMETRY"

        monitored_servers.append({
            "id": s.id or "Unavailable",
            "hostname": s.hostname or "Unavailable",
            "display_name": s.display_name or "Unavailable",
            "status": s.status or "Unavailable",
            "telemetry_status": tel_status,
            "latest_telemetry_timestamp": s_ts,
            "is_telemetry_stale": s_stale,
            "telemetry_age_seconds": s_age,
            "last_measured_cpu_percent": cpu_val,
            "last_measured_memory_percent": mem_val,
            "last_measured_disk_percent": disk_val
        })

    # 2. Active Incidents (Independently structured records with safe bounded retrieval)
    bounded_limit = min(max(1, incident_limit), 25)
    bounded_offset = max(0, incident_offset)

    open_incidents_query = db.query(Incident).filter(
        Incident.tenant_id == tenant_id,
        or_(
            Incident.status.in_(["open", "investigating", "active", "acknowledged"]),
            and_(Incident.status != "resolved", Incident.status.isnot(None)),
            Incident.status.is_(None)
        )
    ).order_by(Incident.created_at.desc())

    # Total open incidents is calculated independently across ALL tenant records
    total_open_incidents = open_incidents_query.count()

    # Bounded retrieval for prompt context
    incidents = open_incidents_query.offset(bounded_offset).limit(bounded_limit).all()

    incidents_data = []
    for inc in incidents:
        # Resolve affected host strictly for this incident without concatenating or cross-contaminating
        host_name = "Unavailable"
        if inc.primary_server and inc.primary_server.hostname:
            host_name = inc.primary_server.hostname
        elif inc.primary_server_id:
            rel_server = db.query(Server.hostname).filter(
                Server.id == inc.primary_server_id,
                Server.tenant_id == tenant_id
            ).first()
            if rel_server and rel_server[0]:
                host_name = rel_server[0]

        record = {
            "incident_id": inc.id if inc.id and str(inc.id).strip() else "Unavailable",
            "incident_code": inc.incident_code if inc.incident_code and str(inc.incident_code).strip() else "Unavailable",
            "title": redact_sensitive_data(inc.title) if inc.title and str(inc.title).strip() else "Unavailable",
            "severity": inc.severity if inc.severity and str(inc.severity).strip() else "Unavailable",
            "status": inc.status if inc.status and str(inc.status).strip() else "Unavailable",
            "affected_hostname": host_name,
            "primary_server_id": inc.primary_server_id if inc.primary_server_id and str(inc.primary_server_id).strip() else "Unavailable",
            "created_at": _iso(inc.created_at) if inc.created_at else "Unavailable",
            # Backwards-compatible aliases
            "id": inc.id if inc.id and str(inc.id).strip() else "Unavailable"
        }
        incidents_data.append(record)

    displayed_incidents_count = len(incidents_data)
    remaining_open_incidents = max(0, total_open_incidents - (bounded_offset + displayed_incidents_count))

    retrieval_metadata = {
        "total_open_incidents": total_open_incidents,
        "displayed_incidents_count": displayed_incidents_count,
        "remaining_open_incidents_count": remaining_open_incidents,
        "offset": bounded_offset,
        "limit": bounded_limit,
        "is_bounded_or_truncated": total_open_incidents > displayed_incidents_count
    }

    # 3. Active Alerts (max 10)
    alerts = db.query(Alert).filter(
        Alert.tenant_id == tenant_id,
        Alert.status == "active"
    ).order_by(Alert.created_at.desc()).limit(10).all()

    alerts_data = [
        {
            "id": a.id or "Unavailable",
            "title": redact_sensitive_data(a.title) if a.title and str(a.title).strip() else "Unavailable",
            "severity": a.severity or "Unavailable",
            "metric_name": a.metric_name or "Unavailable",
            "observed_value": a.observed_value if a.observed_value is not None else "Unavailable",
            "threshold_value": a.threshold_value if a.threshold_value is not None else "Unavailable",
            "server_hostname": a.server.hostname if a.server and a.server.hostname else "Unavailable",
            "created_at": _iso(a.created_at) if a.created_at else "Unavailable"
        }
        for a in alerts
    ]

    # 4. Recent Distributed Trace Errors (max 5)
    error_spans = db.query(TraceSpan).filter(
        TraceSpan.tenant_id == tenant_id,
        or_(
            TraceSpan.status_code == "ERROR",
            TraceSpan.status_code.in_(["ERROR", "error", "500", "502", "503", "504", "400", "401", "403", "404"]),
            TraceSpan.status_code.like("4%"),
            TraceSpan.status_code.like("5%"),
            and_(TraceSpan.status_message.isnot(None), TraceSpan.status_message != "")
        )
    ).order_by(TraceSpan.start_time.desc()).limit(5).all()

    traces_data = [
        {
            "trace_id": s.trace_id,
            "span_id": s.span_id,
            "operation_name": s.operation_name,
            "span_name": s.operation_name,
            "service_name": s.service_name,
            "status_code": s.status_code or "UNKNOWN",
            "status_message": redact_sensitive_data(s.status_message) if s.status_message else None,
            "duration_ms": round(s.duration_ms, 2) if s.duration_ms is not None else 0.0,
            "timestamp": _iso(s.start_time) if s.start_time else None
        }
        for s in error_spans
    ]

    # 5. Targeted context enrichment if incident_id or server_id provided
    targeted_context = {}
    if incident_id:
        try:
            targeted_context["focused_incident"] = build_incident_context(db, tenant_id, incident_id)
        except Exception:
            pass
    if server_id:
        try:
            targeted_context["focused_server_telemetry"] = build_telemetry_context(db, tenant_id, server_id, hours=1, limit=5)
        except Exception:
            pass

    return {
        "tenant_id": tenant_id,
        "total_open_incidents": total_open_incidents,
        "active_incidents_count": total_open_incidents,
        "incident_retrieval_metadata": retrieval_metadata,
        "monitored_servers": monitored_servers,
        "infrastructure_health": server_summary,
        "active_incidents": incidents_data,
        "active_alerts": alerts_data,
        "firing_alerts": alerts_data,
        "recent_error_traces": traces_data,
        "targeted_context": targeted_context
    }
