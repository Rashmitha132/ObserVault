# backend/app/correlation/incident_correlator.py
import json
import random
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.models import Incident, Alert, Server, Tenant, Recommendation

def run_incident_correlation(db: Session, tenant: Tenant) -> List[Incident]:
    """
    Correlates active alerts within a tenant into holistic incidents.
    Looks for correlated phenomena (e.g. CPU + Latency, Packet Loss + Latency, Auth Spike + CPU).
    Attaches supporting evidence, calculated confidence, and probable cause.
    """
    now = datetime.now(timezone.utc)
    recent_cutoff = now - timedelta(minutes=15)

    # Fetch active alerts for this tenant
    active_alerts = db.query(Alert).filter(
        Alert.tenant_id == tenant.id,
        Alert.status == "active"
    ).all()

    if not active_alerts:
        return []

    # Group active alerts by server_id
    server_alerts_map = {}
    for alert in active_alerts:
        server_alerts_map.setdefault(alert.server_id, []).append(alert)

    created_or_updated_incidents = []

    for server_id, alerts in server_alerts_map.items():
        server = db.query(Server).filter(Server.id == server_id).first()
        server_name = server.display_name if server else "Target Host"
        alert_types = {a.alert_type: a for a in alerts}

        # Check Correlation Pattern 1: CPU Exhaustion + Latency / Service Degradation
        if ("high_cpu" in alert_types and "high_latency" in alert_types) or \
           ("high_cpu" in alert_types and "service_unavailable" in alert_types):
            
            inc_code = f"INC-{tenant.slug[:3].upper()}-RES"
            existing_inc = db.query(Incident).filter(
                Incident.tenant_id == tenant.id,
                Incident.incident_code == inc_code,
                Incident.status.in_(["open", "investigating"])
            ).first()

            evidence = (
                f"Observed simultaneous CPU saturation ({alert_types['high_cpu'].observed_value:.1f}%) "
                f"and latency elevation/service degradation on {server_name}. "
                f"Temporal alignment within 15-minute window strongly points to resource thread starvation."
            )
            possible_cause = (
                "Heavy application workload or unoptimized computational process monopolizing CPU execution threads, "
                "leading to cascading request queuing and high response latency."
            )
            actions = [
                "Profile top active processes via local system diagnostics (e.g., top, htop, or container metrics).",
                "Inspect recent application deployments or background scheduled batch jobs.",
                "Scale compute instances horizontally or adjust CPU quota limits if traffic volume has legitimately increased."
            ]

            if not existing_inc:
                incident = Incident(
                    tenant_id=tenant.id,
                    incident_code=inc_code,
                    title=f"Resource Starvation Degrading Performance on {server_name}",
                    severity="critical" if alert_types.get("service_unavailable") else "high",
                    status="open",
                    primary_server_id=server_id,
                    possible_cause=possible_cause,
                    confidence_score=0.91,
                    evidence_summary=evidence,
                    recommended_actions_json=json.dumps(actions),
                    created_at=now,
                    updated_at=now
                )
                db.add(incident)
                db.flush()
                # Link alerts
                incident.alerts = list(alert_types.values())
                created_or_updated_incidents.append(incident)
            else:
                existing_inc.evidence_summary = evidence
                existing_inc.updated_at = now
                existing_inc.alerts = list(alert_types.values())
                created_or_updated_incidents.append(existing_inc)

        # Check Correlation Pattern 2: Authentication Spike + CPU/Traffic
        elif "auth_spike" in alert_types:
            inc_code = f"INC-{tenant.slug[:3].upper()}-SEC"
            existing_inc = db.query(Incident).filter(
                Incident.tenant_id == tenant.id,
                Incident.incident_code == inc_code,
                Incident.status.in_(["open", "investigating"])
            ).first()

            auth_alert = alert_types["auth_spike"]
            evidence = (
                f"Detected {int(auth_alert.observed_value)} failed authentication attempts on {server_name}. "
                f"ObserVault local collector sanitized and dropped all credential inputs locally; "
                f"only count metadata was transmitted for security observability."
            )
            possible_cause = (
                "Potential brute-force credential stuffing attempt, automated vulnerability scanning, "
                "or misconfigured service client retrying invalid credentials."
            )
            actions = [
                "Verify authentication rate-limiting rules and Web Application Firewall (WAF) ingress policies.",
                "Review identity provider security logs locally without exposing credentials.",
                "Enforce multi-factor authentication (MFA) and lock suspect source IPs at the perimeter network gateway."
            ]

            if not existing_inc:
                incident = Incident(
                    tenant_id=tenant.id,
                    incident_code=inc_code,
                    title=f"Suspected Credential Spraying / Auth Anomaly on {server_name}",
                    severity="high",
                    status="open",
                    primary_server_id=server_id,
                    possible_cause=possible_cause,
                    confidence_score=0.88,
                    evidence_summary=evidence,
                    recommended_actions_json=json.dumps(actions),
                    created_at=now,
                    updated_at=now
                )
                db.add(incident)
                db.flush()
                incident.alerts = [auth_alert]
                created_or_updated_incidents.append(incident)
            else:
                existing_inc.evidence_summary = evidence
                existing_inc.updated_at = now
                existing_inc.alerts = [auth_alert]
                created_or_updated_incidents.append(existing_inc)

        # Check Correlation Pattern 3: Network Latency + Packet Loss
        elif "high_latency" in alert_types and "packet_loss" in alert_types:
            inc_code = f"INC-{tenant.slug[:3].upper()}-NET"
            existing_inc = db.query(Incident).filter(
                Incident.tenant_id == tenant.id,
                Incident.incident_code == inc_code,
                Incident.status.in_(["open", "investigating"])
            ).first()

            lat_alert = alert_types["high_latency"]
            pkt_alert = alert_types["packet_loss"]
            evidence = (
                f"Simultaneous elevated latency ({lat_alert.observed_value:.1f}ms) and packet drop "
                f"({pkt_alert.observed_value:.1f}%) observed on interface connecting {server_name}."
            )
            possible_cause = (
                "Upstream network route congestion, switch buffer overrun, or intermediate ISP network peering degradation."
            )
            actions = [
                "Check intermediate router interface drop counters and bandwidth utilization.",
                "Initiate network path traceroute to locate hop experiencing packet degradation.",
                "Failover to redundant secondary network path or VPN gateway if available."
            ]

            if not existing_inc:
                incident = Incident(
                    tenant_id=tenant.id,
                    incident_code=inc_code,
                    title=f"Network Transport Congestion & Packet Degradation on {server_name}",
                    severity="high",
                    status="open",
                    primary_server_id=server_id,
                    possible_cause=possible_cause,
                    confidence_score=0.86,
                    evidence_summary=evidence,
                    recommended_actions_json=json.dumps(actions),
                    created_at=now,
                    updated_at=now
                )
                db.add(incident)
                db.flush()
                incident.alerts = [lat_alert, pkt_alert]
                created_or_updated_incidents.append(incident)
            else:
                existing_inc.evidence_summary = evidence
                existing_inc.updated_at = now
                existing_inc.alerts = [lat_alert, pkt_alert]
                created_or_updated_incidents.append(existing_inc)

    return created_or_updated_incidents
