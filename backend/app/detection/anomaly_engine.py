# backend/app/detection/anomaly_engine.py
from datetime import datetime, timezone
from typing import List, Tuple
from sqlalchemy.orm import Session
from app.models.models import Alert, Server, Tenant, TelemetryRecord, MLAnomaly
from app.detection.ml_engine import ml_detector
from app.detection.statistical_engine import StatisticalAnomalyEngine

def run_anomaly_detection(
    db: Session,
    record: TelemetryRecord,
    tenant: Tenant,
    server: Server
) -> List[Alert]:
    """
    Explainable, rule-based anomaly detection engine with deduplication.
    Evaluates telemetry against tenant-specific thresholds.
    Deduplicates continuous breaches by updating observed values rather than spamming alerts.
    Resolves alerts when conditions return to normal.
    """
    generated_alerts: List[Alert] = []
    now = datetime.now(timezone.utc)

    # List of checks: (condition, alert_type, severity, title, description, metric_name, observed_val, threshold_val)
    checks = []

    # 1. CPU Check
    if record.cpu_percent >= tenant.cpu_threshold:
        severity = "critical" if record.cpu_percent >= 95.0 else "high"
        checks.append((
            True,
            "high_cpu",
            severity,
            f"High CPU Utilisation on {server.display_name}",
            f"CPU utilisation reached {record.cpu_percent:.1f}%, exceeding the configured threshold of {tenant.cpu_threshold:.1f}%.",
            "cpu_percent",
            record.cpu_percent,
            tenant.cpu_threshold
        ))
    else:
        checks.append((False, "high_cpu", None, None, None, "cpu_percent", record.cpu_percent, tenant.cpu_threshold))

    # 2. Memory Check
    if record.memory_percent >= tenant.memory_threshold:
        severity = "critical" if record.memory_percent >= 95.0 else "high"
        checks.append((
            True,
            "high_memory",
            severity,
            f"High Memory Utilisation on {server.display_name}",
            f"Memory consumption reached {record.memory_percent:.1f}%, exceeding the configured threshold of {tenant.memory_threshold:.1f}%.",
            "memory_percent",
            record.memory_percent,
            tenant.memory_threshold
        ))
    else:
        checks.append((False, "high_memory", None, None, None, "memory_percent", record.memory_percent, tenant.memory_threshold))

    # 3. Disk Check
    if record.disk_percent >= tenant.disk_threshold:
        severity = "high" if record.disk_percent >= 95.0 else "medium"
        checks.append((
            True,
            "high_disk",
            severity,
            f"High Disk Utilisation on {server.display_name}",
            f"Storage volume utilisation is {record.disk_percent:.1f}%, exceeding the threshold of {tenant.disk_threshold:.1f}%.",
            "disk_percent",
            record.disk_percent,
            tenant.disk_threshold
        ))
    else:
        checks.append((False, "high_disk", None, None, None, "disk_percent", record.disk_percent, tenant.disk_threshold))

    # 4. Latency Check
    if record.network_latency_ms >= tenant.latency_threshold_ms:
        severity = "high" if record.network_latency_ms >= 250.0 else "medium"
        checks.append((
            True,
            "high_latency",
            severity,
            f"Elevated Network Latency on {server.display_name}",
            f"Network round-trip latency measured at {record.network_latency_ms:.1f}ms, exceeding the threshold of {tenant.latency_threshold_ms:.1f}ms.",
            "network_latency_ms",
            record.network_latency_ms,
            tenant.latency_threshold_ms
        ))
    else:
        checks.append((False, "high_latency", None, None, None, "network_latency_ms", record.network_latency_ms, tenant.latency_threshold_ms))

    # 5. Packet Loss Check
    if record.packet_loss_percent >= tenant.packet_loss_threshold:
        severity = "critical" if record.packet_loss_percent >= 15.0 else "high"
        checks.append((
            True,
            "packet_loss",
            severity,
            f"Packet Loss Detected on {server.display_name}",
            f"Network interface observed {record.packet_loss_percent:.1f}% packet drop, exceeding the threshold of {tenant.packet_loss_threshold:.1f}%.",
            "packet_loss_percent",
            record.packet_loss_percent,
            tenant.packet_loss_threshold
        ))
    else:
        checks.append((False, "packet_loss", None, None, None, "packet_loss_percent", record.packet_loss_percent, tenant.packet_loss_threshold))

    # 6. Failed Logins Check
    if record.failed_login_count >= tenant.failed_login_threshold:
        severity = "high" if record.failed_login_count >= 10 else "medium"
        checks.append((
            True,
            "auth_spike",
            severity,
            f"Repeated Authentication Failures on {server.display_name}",
            f"Detected {record.failed_login_count} failed login attempts within the evaluation interval (threshold: {tenant.failed_login_threshold}).",
            "failed_login_count",
            float(record.failed_login_count),
            float(tenant.failed_login_threshold)
        ))
    else:
        checks.append((False, "auth_spike", None, None, None, "failed_login_count", float(record.failed_login_count), float(tenant.failed_login_threshold)))

    # 7. Service Availability Check
    if record.service_status in ["down", "degraded"]:
        severity = "critical" if record.service_status == "down" else "high"
        checks.append((
            True,
            "service_unavailable",
            severity,
            f"Application Service {record.service_status.upper()} on {server.display_name}",
            f"Monitored service health check returned status '{record.service_status}'.",
            "service_status",
            0.0 if record.service_status == "down" else 0.5,
            1.0
        ))
    else:
        checks.append((False, "service_unavailable", None, None, None, "service_status", 1.0, 1.0))

    # Process all checks for this server
    for triggered, alert_type, severity, title, desc, metric_name, obs_val, thresh_val in checks:
        existing_active = db.query(Alert).filter(
            Alert.tenant_id == tenant.id,
            Alert.server_id == server.id,
            Alert.alert_type == alert_type,
            Alert.status == "active"
        ).first()

        if triggered:
            if existing_active:
                # Deduplication: update existing alert observed value without spamming
                existing_active.observed_value = obs_val
                existing_active.description = desc
                generated_alerts.append(existing_active)
            else:
                # Create new alert
                new_alert = Alert(
                    tenant_id=tenant.id,
                    server_id=server.id,
                    alert_type=alert_type,
                    severity=severity,
                    title=title,
                    description=desc,
                    metric_name=metric_name,
                    observed_value=obs_val,
                    threshold_value=thresh_val,
                    status="active",
                    created_at=now
                )
                db.add(new_alert)
                db.flush()
                generated_alerts.append(new_alert)
        else:
            # Condition normalized: if active alert existed, auto-resolve it
            if existing_active:
                existing_active.status = "resolved"
                existing_active.resolved_at = now

    # Update server status based on active alerts
    active_count = db.query(Alert).filter(
        Alert.server_id == server.id,
        Alert.status == "active"
    ).count()

    critical_count = db.query(Alert).filter(
        Alert.server_id == server.id,
        Alert.status == "active",
        Alert.severity == "critical"
    ).count()

    if critical_count > 0:
        server.status = "critical"
    elif active_count > 0:
        server.status = "warning"
    else:
        server.status = "healthy"

    return generated_alerts


def run_advanced_detection(
    db: Session,
    record: TelemetryRecord,
    tenant: Tenant,
    server: Server
) -> List[MLAnomaly]:
    """
    Evaluates telemetry against Scikit-Learn IsolationForest (multivariate)
    and Statistical Engines (Z-Score 3-Sigma, EWMA drift).
    Persists explainable anomalies to db.
    """
    anomalies: List[MLAnomaly] = []

    # 1. Isolation Forest Multi-metric vector
    feature_dict = {
        "cpu_percent": float(record.cpu_percent),
        "memory_percent": float(record.memory_percent),
        "disk_percent": float(record.disk_percent),
        "network_latency_ms": float(record.network_latency_ms),
        "packet_loss_percent": float(record.packet_loss_percent),
        "failed_login_count": float(record.failed_login_count)
    }

    is_anomaly, score, explanation = ml_detector.score_telemetry_vector(feature_dict)
    if is_anomaly:
        severity = "critical" if score >= 0.85 else ("high" if score >= 0.75 else "medium")
        ml_anom = MLAnomaly(
            tenant_id=tenant.id,
            server_id=server.id,
            algorithm="isolation_forest",
            metric_name="multivariate_vector",
            observed_value=score,
            expected_baseline=0.35,
            deviation=round(score - 0.35, 3),
            anomaly_score=score,
            severity=severity,
            explanation=explanation
        )
        db.add(ml_anom)
        anomalies.append(ml_anom)

    # 2. Statistical Analysis using rolling history
    history = db.query(TelemetryRecord).filter(
        TelemetryRecord.server_id == server.id
    ).order_by(TelemetryRecord.timestamp.desc()).limit(15).all()

    if len(history) >= 5:
        # Exclude current record if it was already stored or top of list
        cpu_history = [r.cpu_percent for r in history if r.id != record.id]
        if len(cpu_history) >= 4:
            is_z, z_score, mean_cpu, std_cpu, z_expl = StatisticalAnomalyEngine.compute_z_score(
                record.cpu_percent, cpu_history, min_history_len=4, z_threshold=3.0
            )
            if is_z:
                z_anom = MLAnomaly(
                    tenant_id=tenant.id,
                    server_id=server.id,
                    algorithm="z_score",
                    metric_name="cpu_percent",
                    observed_value=record.cpu_percent,
                    expected_baseline=round(mean_cpu, 2),
                    deviation=round(record.cpu_percent - mean_cpu, 2),
                    anomaly_score=min(1.0, round(z_score / 4.0, 3)),
                    severity="critical" if z_score >= 4.0 else "high",
                    explanation=z_expl
                )
                db.add(z_anom)
                anomalies.append(z_anom)

        # EWMA for memory creep
        mem_history = [r.memory_percent for r in history if r.id != record.id]
        if len(mem_history) >= 4:
            is_drift, ewma_mean, residual, drift_expl = StatisticalAnomalyEngine.compute_ewma_drift(
                record.memory_percent, mem_history
            )
            if is_drift:
                drift_anom = MLAnomaly(
                    tenant_id=tenant.id,
                    server_id=server.id,
                    algorithm="ewma_residual",
                    metric_name="memory_percent",
                    observed_value=record.memory_percent,
                    expected_baseline=round(ewma_mean, 2),
                    deviation=round(residual, 2),
                    anomaly_score=0.75,
                    severity="medium",
                    explanation=drift_expl
                )
                db.add(drift_anom)
                anomalies.append(drift_anom)

    return anomalies
