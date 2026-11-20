# backend/app/correlation/rca_engine.py
"""
ObserVault Intelligent Root Cause Analysis (RCA) Engine.
Correlates infrastructure metrics, Scikit-Learn ML anomalies, distributed trace spans,
service dependency graphs, network telemetry, and security events to identify
the most probable origin of multi-tier incidents with explainable evidence.
"""

import json
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Set, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from app.models.models import (
    Incident,
    Alert,
    Server,
    Tenant,
    TraceSpan,
    ServiceNode,
    ServiceDependency,
    MLAnomaly,
    TelemetryRecord
)

class RootCauseAnalysisEngine:
    """
    Intelligent Root Cause Analysis Engine for ObserVault.
    Ranks causal hypotheses using temporal precedence, dependency tree topology,
    and multi-signal telemetry convergence.
    """

    @classmethod
    def analyze_incident(
        cls,
        db: Session,
        tenant_id: str,
        incident_id: str
    ) -> Dict[str, Any]:
        """
        Executes complete multi-signal RCA on an incident.
        Returns ranked hypotheses, incident timeline, blast-radius topology,
        and evidence-based investigation steps.
        """
        incident = db.query(Incident).filter(
            Incident.id == incident_id,
            Incident.tenant_id == tenant_id
        ).first()

        if not incident:
            return {"error": "Incident not found", "incident_id": incident_id}

        now = datetime.now(timezone.utc)

        # 1. Determine Incident Temporal Window
        alerts = incident.alerts or []
        if alerts:
            earliest_alert_time = min(a.created_at for a in alerts)
            latest_alert_time = max(a.created_at for a in alerts)
        else:
            earliest_alert_time = incident.created_at
            latest_alert_time = incident.created_at

        # Time window: 20 minutes before first symptom, up to 30 minutes after latest
        # Handle timezone-aware vs naive datetimes
        if earliest_alert_time.tzinfo is None:
            earliest_alert_time = earliest_alert_time.replace(tzinfo=timezone.utc)
        if latest_alert_time.tzinfo is None:
            latest_alert_time = latest_alert_time.replace(tzinfo=timezone.utc)

        window_start = earliest_alert_time - timedelta(minutes=20)
        window_end = latest_alert_time + timedelta(minutes=30)

        # 2. Collect Cross-Domain Signals in Time Window
        # Core Incident Servers & Services
        incident_server_ids = set()
        if incident.primary_server_id:
            incident_server_ids.add(incident.primary_server_id)
        for a in alerts:
            if a.server_id:
                incident_server_ids.add(a.server_id)

        servers = db.query(Server).filter(Server.tenant_id == tenant_id).all()
        server_map = {s.id: s for s in servers}
        services = db.query(ServiceNode).filter(ServiceNode.tenant_id == tenant_id).all()
        service_map = {s.name: s for s in services}
        dependencies = db.query(ServiceDependency).filter(ServiceDependency.tenant_id == tenant_id).all()

        # Determine directly involved service names from incident servers
        directly_involved_services: Set[str] = set()
        for sid in incident_server_ids:
            srv = server_map.get(sid)
            if srv:
                for s in services:
                    if s.name in srv.hostname or srv.hostname in s.name or ("db" in s.name and "db" in srv.hostname) or ("auth" in s.name and "auth" in srv.hostname) or ("gateway" in s.name and "gateway" in srv.hostname):
                        directly_involved_services.add(s.name)

        # Expand via Dependency Topology (Callers and Callees)
        related_service_names: Set[str] = set(directly_involved_services)
        for dep in dependencies:
            if dep.callee_service_name in directly_involved_services:
                related_service_names.add(dep.caller_service_name)
            if dep.caller_service_name in directly_involved_services:
                related_service_names.add(dep.callee_service_name)

        # Allowed servers = incident servers + servers hosting related services
        allowed_server_ids: Set[str] = set(incident_server_ids)
        for srv in servers:
            for r_svc in related_service_names:
                if r_svc in srv.hostname or (r_svc == "postgres-db" and "db" in srv.hostname):
                    allowed_server_ids.add(srv.id)

        # B. ML Anomalies (Isolation Forest, Z-Score, EWMA) - filtered by allowed servers to reject unrelated events
        all_ml_anomalies = db.query(MLAnomaly).filter(
            MLAnomaly.tenant_id == tenant_id,
            MLAnomaly.created_at >= window_start.replace(tzinfo=None),
            MLAnomaly.created_at <= window_end.replace(tzinfo=None)
        ).all()

        # Reject unrelated simultaneous ML anomalies occurring on completely unlinked nodes
        ml_anomalies = [
            ma for ma in all_ml_anomalies
            if ma.server_id in allowed_server_ids
        ]

        # C. Trace Spans (Failing and slow operations) - filtered strictly to topologically related services
        all_trace_spans = db.query(TraceSpan).filter(
            TraceSpan.tenant_id == tenant_id,
            TraceSpan.start_time >= window_start.replace(tzinfo=None),
            TraceSpan.start_time <= window_end.replace(tzinfo=None)
        ).all()

        error_spans = [
            s for s in all_trace_spans
            if (s.status_code == "ERROR" or s.duration_ms > 400.0) and
               (s.service_name in related_service_names)
        ] if related_service_names else []

        # 3. Component Extraction & Event Grouping
        # Map each involved component (services, servers, network interfaces) to its signals
        component_signals: Dict[str, Dict[str, Any]] = {}

        def get_or_create_component(comp_name: str, comp_type: str):
            if comp_name not in component_signals:
                component_signals[comp_name] = {
                    "name": comp_name,
                    "type": comp_type,
                    "first_seen": None,
                    "alerts": [],
                    "ml_anomalies": [],
                    "trace_errors": [],
                    "network_events": [],
                    "security_events": [],
                    "signal_categories": set(),
                    "max_severity": "low",
                    "server_id": None
                }
            return component_signals[comp_name]

        # Ingest Alerts into Components
        for a in alerts:
            srv = server_map.get(a.server_id)
            comp_name = srv.hostname if srv else (a.metric_name or "unknown-host")
            comp = get_or_create_component(comp_name, "infrastructure")
            comp["alerts"].append(a)
            comp["signal_categories"].add("infrastructure_alert")
            comp["server_id"] = a.server_id
            t = a.created_at.replace(tzinfo=timezone.utc) if a.created_at.tzinfo is None else a.created_at
            if comp["first_seen"] is None or t < comp["first_seen"]:
                comp["first_seen"] = t
            if a.severity == "critical" or comp["max_severity"] != "critical":
                if a.severity in ["critical", "high"]:
                    comp["max_severity"] = a.severity

        # Ingest ML Anomalies into Components
        for ma in ml_anomalies:
            srv = server_map.get(ma.server_id)
            comp_name = srv.hostname if srv else "unknown-host"
            comp = get_or_create_component(comp_name, "infrastructure")
            comp["ml_anomalies"].append(ma)
            comp["signal_categories"].add(f"ml_{ma.algorithm}")
            comp["server_id"] = ma.server_id
            t = ma.created_at.replace(tzinfo=timezone.utc) if ma.created_at.tzinfo is None else ma.created_at
            if comp["first_seen"] is None or t < comp["first_seen"]:
                comp["first_seen"] = t
            if ma.severity == "critical":
                comp["max_severity"] = "critical"
            elif ma.severity == "high" and comp["max_severity"] != "critical":
                comp["max_severity"] = "high"

        # Ingest Trace Errors into Service Components
        for span in error_spans:
            comp = get_or_create_component(span.service_name, "microservice")
            comp["trace_errors"].append(span)
            comp["signal_categories"].add("trace_error" if span.status_code == "ERROR" else "trace_latency")
            t = span.start_time.replace(tzinfo=timezone.utc) if span.start_time.tzinfo is None else span.start_time
            if comp["first_seen"] is None or t < comp["first_seen"]:
                comp["first_seen"] = t
            if span.status_code == "ERROR" and comp["max_severity"] != "critical":
                comp["max_severity"] = "high"

        # Check for correlated database services (e.g., if postgres-db called by order-service)
        # Connect hostnames to microservices (e.g. srv-prod-db-01 <-> postgres-db)
        for comp_name, comp_data in list(component_signals.items()):
            if "db" in comp_name.lower():
                # Correlate with database microservice if exists
                for s_name in service_map:
                    if "db" in s_name.lower() or "postgres" in s_name.lower():
                        # Unify or cross-reference
                        db_comp = get_or_create_component(s_name, "database")
                        db_comp["signal_categories"].update(comp_data["signal_categories"])
                        if comp_data["first_seen"] and (db_comp["first_seen"] is None or comp_data["first_seen"] < db_comp["first_seen"]):
                            db_comp["first_seen"] = comp_data["first_seen"]

        # If no components were detected (empty alert list / clean test state), create nominal entry from incident
        if not component_signals:
            prim_srv = server_map.get(incident.primary_server_id)
            comp_name = prim_srv.hostname if prim_srv else "primary-service"
            comp = get_or_create_component(comp_name, "service")
            comp["first_seen"] = earliest_alert_time
            comp["max_severity"] = incident.severity

        # 4. Rank Root Cause Candidates
        ranked_candidates = cls._rank_candidates(
            component_signals=component_signals,
            dependencies=dependencies,
            earliest_time=earliest_alert_time,
            latest_time=latest_alert_time
        )

        # Top candidate is primary hypothesis
        top_candidate = ranked_candidates[0] if ranked_candidates else None
        top_candidate_name = top_candidate["name"] if top_candidate else "Unknown Component"

        # 5. Build Unified Incident Timeline
        timeline_events = cls._build_timeline(
            incident=incident,
            alerts=alerts,
            ml_anomalies=ml_anomalies,
            error_spans=error_spans,
            component_signals=component_signals
        )

        # 6. Compute Blast Radius for Primary Suspected Cause
        blast_radius_report = cls._compute_blast_radius(
            suspected_component=top_candidate_name,
            services=services,
            dependencies=dependencies,
            component_signals=component_signals
        )

        # 7. Generate Evidence-Based Investigation Steps
        investigation_steps = cls._generate_investigation_steps(
            top_candidate=top_candidate,
            component_signals=component_signals,
            blast_radius=blast_radius_report
        )

        return {
            "incident_id": incident.id,
            "incident_code": incident.incident_code,
            "title": incident.title,
            "severity": incident.severity,
            "status": incident.status,
            "created_at": incident.created_at.isoformat(),
            "analyzed_at": now.isoformat(),
            "analysis_window": {
                "start": window_start.isoformat(),
                "end": window_end.isoformat(),
                "duration_minutes": 50
            },
            "disclaimer": (
                "Heuristic Root-Cause Score (0-100%): This is an empirical multi-signal heuristic score, "
                "NOT a statistical probability. It quantifies evidence convergence, temporal precedence, "
                "and topology correlation to prioritize engineering investigation. Correlation does not guarantee causation."
            ),
            "score_type": "heuristic_root_cause_score",
            "primary_root_cause_hypothesis": top_candidate,
            "ranked_candidates": ranked_candidates,
            "incident_timeline": timeline_events,
            "blast_radius": blast_radius_report,
            "suggested_investigation_steps": investigation_steps
        }

    @classmethod
    def _rank_candidates(
        cls,
        component_signals: Dict[str, Dict[str, Any]],
        dependencies: List[ServiceDependency],
        earliest_time: datetime,
        latest_time: datetime
    ) -> List[Dict[str, Any]]:
        """
        Applies multi-factor scoring to rank root cause candidates.
        Score = 0.35 * TimePrecedence + 0.30 * TopologyPrecedence + 0.20 * SignalConvergence + 0.15 * Severity
        """
        dep_graph_callees: Set[str] = set()
        dep_graph_callers: Set[str] = set()
        caller_to_callees: Dict[str, List[str]] = {}
        callee_to_callers: Dict[str, List[str]] = {}

        for dep in dependencies:
            dep_graph_callers.add(dep.caller_service_name)
            dep_graph_callees.add(dep.callee_service_name)
            caller_to_callees.setdefault(dep.caller_service_name, []).append(dep.callee_service_name)
            callee_to_callers.setdefault(dep.callee_service_name, []).append(dep.caller_service_name)

        time_range_seconds = max(1.0, (latest_time - earliest_time).total_seconds())
        candidates = []

        for name, data in component_signals.items():
            alerts_count = len(data.get("alerts", []))
            ml_count = len(data.get("ml_anomalies", []))
            trace_err_count = len(data.get("trace_errors", []))
            signal_count = len(data.get("signal_categories", []))
            has_direct_evidence = (
                alerts_count > 0 or 
                ml_count > 0 or 
                trace_err_count > 0 or 
                len(data.get("network_events", [])) > 0 or 
                len(data.get("security_events", [])) > 0 or
                signal_count > 0
            )

            # A. Direct Evidence Strength (Weight: 40%) - Primary Driver
            # A component without actual observed evidence cannot be crowned root cause merely by being a leaf.
            if has_direct_evidence:
                ev_score = 0.35
                if alerts_count > 0:
                    ev_score += 0.20
                if ml_count > 0:
                    ev_score += 0.20
                if trace_err_count > 0:
                    ev_score += 0.15
                if signal_count > 1:
                    ev_score += 0.10
                evidence_score = min(1.0, ev_score)
            else:
                evidence_score = 0.05

            # B. Temporal Precedence (Weight: 35%)
            if data.get("first_seen"):
                dt_seconds = max(0.0, (data["first_seen"] - earliest_time).total_seconds())
                time_score = max(0.20, 1.0 - (0.80 * (dt_seconds / time_range_seconds)))
            else:
                time_score = 0.10

            # C. Topological Position (Weight: 15%) - Gated by Evidence
            # Leaf callee position only elevates a component if it actually has evidence of failure.
            is_callee = name in dep_graph_callees or "db" in name.lower() or "database" in data.get("type", "")
            is_caller = name in dep_graph_callers or "gateway" in name.lower()

            if has_direct_evidence:
                if is_callee and not is_caller:
                    topo_score = 0.85
                elif is_callee and is_caller:
                    topo_score = 0.65
                elif is_caller and not is_callee:
                    topo_score = 0.40
                else:
                    topo_score = 0.60
            else:
                topo_score = 0.10

            # D. Severity Score (Weight: 10%)
            sev_map = {"critical": 1.0, "high": 0.80, "medium": 0.60, "low": 0.40}
            sev_score = sev_map.get(data.get("max_severity", ""), 0.40) if has_direct_evidence else 0.10

            # Composite Heuristic Root-Cause Score (0.0 to 1.0)
            composite_score = (
                (0.40 * evidence_score) +
                (0.35 * time_score) +
                (0.15 * topo_score) +
                (0.10 * sev_score)
            )
            if not has_direct_evidence:
                composite_score = min(0.20, composite_score)

            composite_score = round(min(0.99, max(0.05, composite_score)), 3)
            score_pct = int(composite_score * 100)

            # Generate Supporting Evidence
            evidence_points = []
            if data["alerts"]:
                for a in data["alerts"][:3]:
                    evidence_points.append(f"Alert: {a.title} ({a.metric_name}={a.observed_value:.1f})")
            if data["ml_anomalies"]:
                for ma in data["ml_anomalies"][:2]:
                    evidence_points.append(f"ML Outlier ({ma.algorithm}): {ma.explanation}")
            if data["trace_errors"]:
                evidence_points.append(f"Trace Failures: {len(data['trace_errors'])} spans recorded errors or timeouts")
            if not evidence_points:
                evidence_points.append("Correlated through primary host involvement (No direct anomalous telemetry recorded)")

            # Generate Alternative Hypotheses
            alternatives = []
            if "gateway" in name.lower():
                alternatives.append("Ingress traffic surge or connection pool starvation at gateway layer rather than internal failure.")
            elif "db" in name.lower():
                alternatives.append("Downstream database connection pool starvation vs upstream unoptimized query burst.")
            else:
                alternatives.append("Transient network jitter between caller and intermediate proxies.")

            # Rationale for Ranking
            first_seen_str = data["first_seen"].strftime("%H:%M:%S UTC") if data["first_seen"] else "N/A"
            rationale = (
                f"Ranked with a {score_pct}% heuristic root-cause score (NOT a statistical probability). "
                f"Driven by {len(evidence_points)} concrete telemetry fact(s) [earliest deviation at {first_seen_str}], "
                f"{data['type']} topology position ({'Leaf Dependency' if is_callee else 'Caller/Ingress'}), "
                f"and {signal_count} converging telemetry signal(s) [{', '.join(sorted(data['signal_categories'])) or 'none'}]."
            )

            candidates.append({
                "candidate_id": f"rca-cand-{len(candidates) + 1}",
                "name": name,
                "component_type": data["type"],
                "root_cause_score": composite_score,
                "root_cause_score_percent": score_pct,
                "confidence_percent": score_pct,  # Kept as alias for UI compatibility
                "score_label": f"{score_pct}% Root-Cause Score",
                "severity": data["max_severity"],
                "has_direct_evidence": has_direct_evidence,
                "first_observed_at": data["first_seen"].isoformat() if data["first_seen"] else None,
                "signals_detected": list(data["signal_categories"]),
                "signal_count": signal_count,
                "supporting_evidence": evidence_points,
                "alternative_hypotheses": alternatives,
                "ranking_rationale": rationale,
                "is_primary_hypothesis": False
            })

        # Sort descending by root_cause_score
        candidates.sort(key=lambda c: c["root_cause_score"], reverse=True)

        # Assign ranks and mark primary hypothesis
        for idx, cand in enumerate(candidates, start=1):
            cand["rank"] = idx
            cand["is_primary_hypothesis"] = (idx == 1)

        return candidates

    @classmethod
    def _build_timeline(
        cls,
        incident: Incident,
        alerts: List[Alert],
        ml_anomalies: List[MLAnomaly],
        error_spans: List[TraceSpan],
        component_signals: Dict[str, Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Constructs an ordered, human-readable timeline of incident evolution.
        """
        events = []

        # Alerts to timeline
        for a in alerts:
            t = a.created_at.replace(tzinfo=timezone.utc) if a.created_at.tzinfo is None else a.created_at
            events.append({
                "timestamp": t.isoformat(),
                "time_obj": t,
                "type": "INFRASTRUCTURE_ALERT",
                "severity": a.severity,
                "component": a.metric_name or "Host",
                "title": a.title,
                "description": f"Threshold breach: observed {a.observed_value:.1f} (threshold {a.threshold_value:.1f})",
                "icon": "alert"
            })

        # ML Anomalies to timeline
        for ma in ml_anomalies:
            t = ma.created_at.replace(tzinfo=timezone.utc) if ma.created_at.tzinfo is None else ma.created_at
            events.append({
                "timestamp": t.isoformat(),
                "time_obj": t,
                "type": "ML_ANOMALY",
                "severity": ma.severity,
                "component": ma.algorithm.upper(),
                "title": f"ML Outlier Detected on {ma.metric_name}",
                "description": ma.explanation,
                "icon": "brain"
            })

        # Trace Errors to timeline
        for sp in error_spans[:10]:
            t = sp.start_time.replace(tzinfo=timezone.utc) if sp.start_time.tzinfo is None else sp.start_time
            events.append({
                "timestamp": t.isoformat(),
                "time_obj": t,
                "type": "TRACE_FAILURE",
                "severity": "high" if sp.status_code == "ERROR" else "medium",
                "component": sp.service_name,
                "title": f"Span Failure in {sp.operation_name}",
                "description": f"Duration {sp.duration_ms:.1f}ms - {sp.status_message or 'Error status code'}",
                "icon": "trace"
            })

        # Incident state markers
        inc_t = incident.created_at.replace(tzinfo=timezone.utc) if incident.created_at.tzinfo is None else incident.created_at
        events.append({
            "timestamp": inc_t.isoformat(),
            "time_obj": inc_t,
            "type": "INCIDENT_CORRELATED",
            "severity": incident.severity,
            "component": "IncidentCorrelator",
            "title": f"Incident {incident.incident_code} Formed",
            "description": incident.possible_cause,
            "icon": "shield"
        })

        if incident.resolved_at:
            res_t = incident.resolved_at.replace(tzinfo=timezone.utc) if incident.resolved_at.tzinfo is None else incident.resolved_at
            events.append({
                "timestamp": res_t.isoformat(),
                "time_obj": res_t,
                "type": "INCIDENT_RECOVERED",
                "severity": "info",
                "component": "SystemRecovery",
                "title": f"Incident Marked {incident.status.upper()}",
                "description": "Telemetry returned within baseline tolerance parameters.",
                "icon": "check"
            })

        # Sort chronologically
        events.sort(key=lambda e: e["time_obj"])

        # Remove temporary sorting key
        for e in events:
            del e["time_obj"]

        return events

    @classmethod
    def _compute_blast_radius(
        cls,
        suspected_component: str,
        services: List[ServiceNode],
        dependencies: List[ServiceDependency],
        component_signals: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Traverses caller-callee dependency graphs to compute the ripple effect
        from the suspected root-cause origin outward.
        """
        # Map callers of callees
        callee_to_callers: Dict[str, List[str]] = {}
        for d in dependencies:
            callee_to_callers.setdefault(d.callee_service_name, []).append(d.caller_service_name)

        directly_affected: Set[str] = set()
        indirectly_affected: Set[str] = set()
        dependency_paths: List[List[str]] = []

        # Find direct callers
        # If suspected component is hostname (e.g. srv-prod-db-01), match to service (postgres-db)
        target_name = suspected_component
        for s in services:
            if s.name in suspected_component or suspected_component in s.name or ("db" in s.name and "db" in suspected_component):
                target_name = s.name
                break

        direct_callers = callee_to_callers.get(target_name, [])
        for caller in direct_callers:
            directly_affected.add(caller)
            dependency_paths.append([target_name, caller])

            # Indirect callers (callers of callers)
            second_hop = callee_to_callers.get(caller, [])
            for indirect_caller in second_hop:
                if indirect_caller != target_name and indirect_caller not in directly_affected:
                    indirectly_affected.add(indirect_caller)
                    dependency_paths.append([target_name, caller, indirect_caller])

        total_affected = len(directly_affected) + len(indirectly_affected)

        # Impact evaluation
        has_gateway = any("gateway" in s.lower() for s in directly_affected.union(indirectly_affected))
        impact_level = "critical" if has_gateway or total_affected >= 3 else ("high" if total_affected >= 1 else "medium")

        return {
            "originating_suspect": suspected_component,
            "resolved_service_target": target_name,
            "directly_affected_services": list(directly_affected),
            "indirectly_affected_services": list(indirectly_affected),
            "total_services_impacted": total_affected,
            "user_impact_level": impact_level,
            "dependency_propagation_paths": dependency_paths,
            "causal_link_summary": (
                f"Degradation originating at '{suspected_component}' propagated to "
                f"{len(directly_affected)} direct caller(s) and {len(indirectly_affected)} indirect upstream service(s)."
            )
        }

    @classmethod
    def _generate_investigation_steps(
        cls,
        top_candidate: Optional[Dict[str, Any]],
        component_signals: Dict[str, Dict[str, Any]],
        blast_radius: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Synthesizes evidence-based, safe investigation recommendations.
        Advisory only: does NOT modify systems or assume fictitious deployments.
        """
        steps = []
        if not top_candidate:
            return [{
                "step_number": 1,
                "title": "Inspect System Baseline",
                "rationale": "No dominant anomaly detected. Verify telemetry collection stream.",
                "action": "Check collector heartbeat and buffer depth.",
                "command_hint": "systemctl status observault-collector"
            }]

        comp_name = top_candidate["name"]
        comp_type = top_candidate["component_type"]
        signals = top_candidate.get("signals_detected", [])

        # Step 1: Target Component Diagnostic
        if "db" in comp_name.lower() or comp_type == "database":
            steps.append({
                "step_number": 1,
                "title": f"Inspect Query Concurrency & Lock Contention on {comp_name}",
                "rationale": "Database operations show elevated latency and cascading client timeouts.",
                "action": "Inspect active connection states and lock queues without printing raw query literals.",
                "command_hint": "SELECT pid, now() - query_start AS duration, state, wait_event_type, wait_event, pg_blocking_pids(pid) AS blocked_by FROM pg_stat_activity WHERE state != 'idle';",
                "privacy_safeguard": "Privacy Guard Enforced: Raw SQL query text is omitted to protect customer PII and records."
            })
            steps.append({
                "step_number": 2,
                "title": "Validate Client Connection Pool Sizing",
                "rationale": f"Directly affected services ({', '.join(blast_radius['directly_affected_services']) or 'callers'}) may be exhausting pool limits.",
                "action": "Review max_connections and active connection count in upstream microservice configurations.",
                "command_hint": "SHOW max_connections;",
                "privacy_safeguard": "Privacy Guard Enforced: Metric threshold inspection without payload exposure."
            })
        elif "gateway" in comp_name.lower():
            steps.append({
                "step_number": 1,
                "title": f"Review Ingress Route Throttling on {comp_name}",
                "rationale": "API Gateway showing elevated latency or 5xx proxy timeouts.",
                "action": "Check ingress rate-limiting quotas, connection timeouts, and backend proxy status codes.",
                "command_hint": "tail -n 100 /var/log/nginx/access.log | awk '{print $4, $6, $9}' | grep -E ' 50[234] '",
                "privacy_safeguard": "Privacy Guard Enforced: URL query parameters stripped to prevent token or PII exposure."
            })
        elif "network" in comp_name.lower() or "network_events" in signals:
            steps.append({
                "step_number": 1,
                "title": f"Inspect Physical Interface Drop Counters on {comp_name}",
                "rationale": "Network telemetry detected packet loss and latency spikes.",
                "action": "Examine interface queue drops, ring buffer overruns, and MTU mismatches.",
                "command_hint": "netstat -i && ethtool -S eth0 | grep -E 'drop|error'",
                "privacy_safeguard": "Privacy Guard Enforced: Network counters inspect packet headers and drop metrics; packet payloads are never captured."
            })
        else:
            steps.append({
                "step_number": 1,
                "title": f"Inspect Process-Level Resource Allocation on {comp_name}",
                "rationale": "Host metric deviations (CPU/Memory/Disk) isolated by ML engine.",
                "action": "Run process diagnostic to identify thread monopolization or runaway child processes.",
                "command_hint": "pidstat -u -r 1 5",
                "privacy_safeguard": "Privacy Guard Enforced: Process telemetry inspects CPU/memory metrics without reading process memory or environment variables."
            })

        # Step 2: Corroborate Upstream Impact
        if blast_radius["directly_affected_services"]:
            affected_str = ", ".join(blast_radius["directly_affected_services"])
            steps.append({
                "step_number": len(steps) + 1,
                "title": f"Verify Circuit Breakers & Fallback Paths on {affected_str}",
                "rationale": f"These upstream services directly depend on {comp_name} and are vulnerable to cascading timeouts.",
                "action": "Check if circuit breakers tripped into OPEN state or if retry storms are amplifying the outage.",
                "command_hint": "curl -s http://localhost:8080/actuator/health | jq .details.circuitBreakers",
                "privacy_safeguard": "Privacy Guard Enforced: Local actuator health endpoint queried without passing customer headers."
            })

        # Step 3: Privacy Verification Reminder
        steps.append({
            "step_number": len(steps) + 1,
            "title": "Maintain Privacy Hygiene During Investigation",
            "rationale": "ObserVault enforces zero customer credential egress.",
            "action": "Ensure local debugging logs containing authorization headers or customer query literals remain on the local machine.",
            "command_hint": "Use ObserVault Privacy Proof view to audit sanitized telemetry",
            "privacy_safeguard": "Privacy Guard Enforced: All diagnostic output remains strictly within local node boundary."
        })

        return steps
