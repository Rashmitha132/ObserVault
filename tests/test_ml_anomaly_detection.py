# tests/test_ml_anomaly_detection.py
"""
Test Suite for ObserVault Phase 2C:
Machine Learning Anomaly Detection, Statistical Baselines (Z-Score & EWMA),
Model Persistence, Benchmark Evaluation, and API endpoints.
"""

import os
import sys
import pytest
from datetime import datetime, timezone

# Add backend directory to module search path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal, Base, engine
from app.models.models import Tenant, User, Server, Collector, MLAnomaly, ModelMetadata
from app.detection.statistical_engine import StatisticalAnomalyEngine
from app.detection.ml_engine import ml_detector, IsolationForestAnomalyDetector
from app.core.security import create_access_token

client = TestClient(app)

@pytest.fixture(scope="module")
def setup_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    tenant = db.query(Tenant).filter((Tenant.name == "Acme FinTech") | (Tenant.slug == "acme-fintech")).first()
    if not tenant:
        tenant = db.query(Tenant).first()
    if not tenant:
        tenant = Tenant(name="Acme FinTech", slug="acme-fintech", plan="Enterprise")
        db.add(tenant)
        db.commit()
        db.refresh(tenant)

    user = db.query(User).filter(User.tenant_id == tenant.id).first()
    if not user:
        from app.core.security import get_password_hash
        user = User(
            tenant_id=tenant.id,
            email="admin@acme.com",
            hashed_password=get_password_hash("Password123!"),
            full_name="Admin Acme",
            role="admin"
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    server = db.query(Server).filter(Server.hostname == "ml-test-node-01").first()
    if not server:
        server = Server(
            tenant_id=tenant.id,
            hostname="ml-test-node-01",
            display_name="ML Test Node 01",
            ip_address="192.168.1.188",
            os_info="Ubuntu 24.04 LTS",
            status="healthy"
        )
        db.add(server)
        db.commit()
        db.refresh(server)

    t_id = str(tenant.id)
    u_id = str(user.id)
    s_id = str(server.id)
    db.close()
    return {"tenant_id": t_id, "user_id": u_id, "server_id": s_id}

def test_statistical_engine_z_score():
    """Verify 3-Sigma Z-Score outlier detection and explainability."""
    history = [30.0, 32.0, 29.5, 31.0, 30.5, 33.0, 31.5, 30.0]
    
    # Inlier value
    is_anom, z_score, mean, std, expl = StatisticalAnomalyEngine.compute_z_score(
        current_value=32.0, history=history, z_threshold=3.0
    )
    assert not is_anom
    assert z_score < 3.0
    assert expl is None

    # Outlier spike
    is_anom, z_score, mean, std, expl = StatisticalAnomalyEngine.compute_z_score(
        current_value=85.0, history=history, z_threshold=3.0
    )
    assert is_anom
    assert z_score >= 3.0
    assert "surged above" in expl
    assert "standard deviations" in expl

def test_statistical_engine_ewma_drift():
    """Verify EWMA drift detection for slow memory creep."""
    creeping_history = [40.0, 42.0, 44.0, 46.0, 49.0, 52.0]
    is_drift, ewma, residual, expl = StatisticalAnomalyEngine.compute_ewma_drift(
        current_value=75.0, history=creeping_history, alpha=0.25, drift_factor=2.0
    )
    assert is_drift
    assert residual > 0.0
    assert "trend divergence" in expl

def test_isolation_forest_scoring():
    """Verify multivariate Isolation Forest distinguishes normal vectors from anomalous ones."""
    normal_vector = {
        "cpu_percent": 35.0,
        "memory_percent": 50.0,
        "disk_percent": 55.0,
        "network_latency_ms": 20.0,
        "packet_loss_percent": 0.0,
        "failed_login_count": 0
    }
    is_anom, score, expl = ml_detector.score_telemetry_vector(normal_vector)
    assert not is_anom
    assert score < 0.65
    assert "normal operating envelope" in expl

    anomaly_vector = {
        "cpu_percent": 76.0,
        "memory_percent": 82.0,
        "disk_percent": 65.0,
        "network_latency_ms": 95.0,
        "packet_loss_percent": 4.5,
        "failed_login_count": 6
    }
    is_anom, score, expl = ml_detector.score_telemetry_vector(anomaly_vector)
    assert is_anom
    assert score >= 0.65
    assert "Isolation Forest outlier" in expl

def test_model_persistence_and_benchmark_evaluation():
    """Verify Isolation Forest training, metadata persistence, and benchmark metrics."""
    eval_report = ml_detector.evaluate_model_benchmark()
    assert "isolation_forest_metrics" in eval_report
    assert "static_threshold_metrics" in eval_report
    assert "architectural_advantage" in eval_report

    ml_metrics = eval_report["isolation_forest_metrics"]
    assert ml_metrics["precision"] >= 0.70
    assert ml_metrics["recall"] >= 0.75
    assert ml_metrics["f1_score"] >= 0.75
    assert ml_metrics["false_positive_rate"] <= 0.15

def test_ml_detection_api_endpoints(setup_db):
    """Verify REST API endpoints for anomalies, models, evaluation, and retraining."""
    token = create_access_token(
        subject=setup_db["user_id"],
        tenant_id=setup_db["tenant_id"],
        role="admin"
    )
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Model list
    resp_models = client.get("/api/v2/models", headers=headers)
    assert resp_models.status_code == 200
    models_data = resp_models.json()
    assert len(models_data) >= 3
    model_names = [m["model_name"] for m in models_data]
    assert "IsolationForest-Multivariate" in model_names
    assert "Z-Score-Statistical" in model_names

    # 2. Benchmark evaluation endpoint
    resp_eval = client.get("/api/v2/models/evaluation", headers=headers)
    assert resp_eval.status_code == 200
    eval_data = resp_eval.json()
    assert "isolation_forest_metrics" in eval_data
    assert "static_threshold_metrics" in eval_data

    # 3. Model retrain endpoint
    resp_train = client.post("/api/v2/models/train", headers=headers)
    assert resp_train.status_code == 200
    assert resp_train.json()["status"] == "success"

    # 4. Insert an anomaly and query /api/v2/anomalies
    db = SessionLocal()
    anom = MLAnomaly(
        tenant_id=setup_db["tenant_id"],
        server_id=setup_db["server_id"],
        algorithm="isolation_forest",
        metric_name="multivariate_vector",
        observed_value=0.88,
        expected_baseline=0.35,
        deviation=0.53,
        anomaly_score=0.88,
        severity="critical",
        explanation="Multi-metric Isolation Forest outlier in high-dimensional space."
    )
    db.add(anom)
    db.commit()
    db.refresh(anom)
    anom_id = anom.id
    db.close()

    resp_anomalies = client.get("/api/v2/anomalies", headers=headers)
    assert resp_anomalies.status_code == 200
    anomalies_list = resp_anomalies.json()
    assert len(anomalies_list) >= 1
    assert any(a["id"] == anom_id for a in anomalies_list)

    # 5. Detail endpoint
    resp_detail = client.get(f"/api/v2/anomalies/{anom_id}", headers=headers)
    assert resp_detail.status_code == 200
    assert resp_detail.json()["anomaly_score"] == 0.88
