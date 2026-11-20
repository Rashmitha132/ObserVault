# backend/app/api/ml_detection.py
"""
ObserVault Machine Learning & Statistical Anomaly Detection Endpoints.
Provides anomaly listing, explainable baseline comparison, model versioning,
and benchmark evaluation reports.
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.models import User, Server, Tenant, MLAnomaly, ModelMetadata
from app.detection.ml_engine import ml_detector

router = APIRouter(prefix="/v2", tags=["Machine Learning Anomaly Detection"])

@router.get("/anomalies")
def list_ml_anomalies(
    server_id: Optional[str] = Query(None),
    algorithm: Optional[str] = Query(None),  # isolation_forest, z_score, ewma_residual
    severity: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns list of anomalies detected via Statistical (Z-Score/EWMA) and Machine Learning (IsolationForest) engines.
    """
    query = db.query(MLAnomaly).filter(MLAnomaly.tenant_id == current_user.tenant_id)
    if server_id:
        query = query.filter(MLAnomaly.server_id == server_id)
    if algorithm:
        query = query.filter(MLAnomaly.algorithm == algorithm)
    if severity:
        query = query.filter(MLAnomaly.severity == severity)

    anomalies = query.order_by(MLAnomaly.created_at.desc()).limit(limit).all()

    results = []
    for a in anomalies:
        srv = db.query(Server).filter(Server.id == a.server_id).first()
        results.append({
            "id": a.id,
            "server_id": a.server_id,
            "server_name": srv.display_name if srv else "Unknown Host",
            "algorithm": a.algorithm,
            "metric_name": a.metric_name,
            "observed_value": a.observed_value,
            "expected_baseline": a.expected_baseline,
            "deviation": a.deviation,
            "anomaly_score": a.anomaly_score,
            "severity": a.severity,
            "explanation": a.explanation,
            "created_at": a.created_at.isoformat()
        })
    return results

@router.get("/anomalies/{anomaly_id}")
def get_anomaly_detail(
    anomaly_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns deep explainable anomaly details including baseline deviation.
    """
    anomaly = db.query(MLAnomaly).filter(
        MLAnomaly.id == anomaly_id,
        MLAnomaly.tenant_id == current_user.tenant_id
    ).first()

    if not anomaly:
        raise HTTPException(status_code=404, detail="Anomaly ID not found")

    srv = db.query(Server).filter(Server.id == anomaly.server_id).first()
    return {
        "id": anomaly.id,
        "server_id": anomaly.server_id,
        "server_name": srv.display_name if srv else "Unknown Host",
        "algorithm": anomaly.algorithm,
        "metric_name": anomaly.metric_name,
        "observed_value": anomaly.observed_value,
        "expected_baseline": anomaly.expected_baseline,
        "deviation": anomaly.deviation,
        "anomaly_score": anomaly.anomaly_score,
        "severity": anomaly.severity,
        "explanation": anomaly.explanation,
        "created_at": anomaly.created_at.isoformat()
    }

@router.get("/models")
def list_models(
    current_user: User = Depends(get_current_user)
):
    """
    Returns active models, version tags, and feature configurations.
    """
    return [
        {
            "model_name": "IsolationForest-Multivariate",
            "version": ml_detector.version,
            "algorithm": "IsolationForest",
            "status": "active",
            "contamination": 0.04,
            "n_estimators": 100,
            "features": [
                "cpu_percent",
                "memory_percent",
                "disk_percent",
                "network_latency_ms",
                "packet_loss_percent",
                "failed_login_count"
            ],
            "description": "Multi-metric subspace anomaly isolation across 6-dimensional operational vector."
        },
        {
            "model_name": "Z-Score-Statistical",
            "version": "1.0.0",
            "algorithm": "3-Sigma",
            "status": "active",
            "threshold": 3.0,
            "description": "Rolling mean and standard deviation outlier detection."
        },
        {
            "model_name": "EWMA-Trend-Detector",
            "version": "1.0.0",
            "algorithm": "ExponentiallyWeightedMovingAverage",
            "status": "active",
            "alpha": 0.25,
            "description": "Trend divergence and slow resource creep detection."
        }
    ]

@router.get("/models/evaluation")
def get_model_evaluation(
    current_user: User = Depends(get_current_user)
):
    """
    Returns actual evaluated benchmark metrics (Precision, Recall, F1, False Positive Rate)
    comparing Isolation Forest against Phase 1 static thresholds on ground-truth dataset.
    """
    return ml_detector.evaluate_model_benchmark()

@router.post("/models/train")
def retrain_model(
    current_user: User = Depends(get_current_user)
):
    """
    Triggers model retraining on fresh baseline profile.
    """
    meta = ml_detector.train_baseline_model()
    return {
        "status": "success",
        "message": f"Successfully retrained IsolationForest v{meta['version']}",
        "metadata": meta
    }
