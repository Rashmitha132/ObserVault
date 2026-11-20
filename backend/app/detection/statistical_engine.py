# backend/app/detection/statistical_engine.py
"""
ObserVault Statistical & Baseline Anomaly Detection Engine.
Implements Z-Score 3-Sigma detection, Exponentially Weighted Moving Average (EWMA),
and Velocity Rate-of-Change detection with explainable reasoning.
"""

import math
from typing import List, Dict, Any, Optional, Tuple

class StatisticalAnomalyEngine:
    """
    Computes rolling baselines, standard deviations, and EWMA trend residuals.
    Detects anomalies without requiring pre-trained black-box models.
    """

    @staticmethod
    def compute_z_score(
        current_value: float,
        history: List[float],
        min_history_len: int = 5,
        z_threshold: float = 3.0
    ) -> Tuple[bool, float, float, float, Optional[str]]:
        """
        Z-Score Outlier Detection (3-Sigma Rule).
        Returns:
            (is_anomaly, z_score, expected_mean, std_dev, explanation)
        """
        if len(history) < min_history_len:
            return False, 0.0, current_value, 0.0, None

        mean = sum(history) / len(history)
        variance = sum((x - mean) ** 2 for x in history) / len(history)
        std_dev = math.sqrt(variance)

        if std_dev < 1e-4:
            # Flatline metric: any variation is notable if large
            if abs(current_value - mean) > 10.0:
                return True, 4.0, mean, std_dev, f"Metric shifted from flatline baseline {mean:.1f} to {current_value:.1f}."
            return False, 0.0, mean, std_dev, None

        z_score = abs(current_value - mean) / std_dev
        is_anomaly = z_score >= z_threshold

        explanation = None
        if is_anomaly:
            direction = "surged above" if current_value > mean else "dropped below"
            explanation = (
                f"Value {current_value:.1f} {direction} baseline mean {mean:.1f} "
                f"by {z_score:.2f} standard deviations (3-sigma threshold = {z_threshold:.1f})."
            )

        return is_anomaly, z_score, mean, std_dev, explanation

    @staticmethod
    def compute_ewma_drift(
        current_value: float,
        history: List[float],
        alpha: float = 0.25,
        drift_factor: float = 2.5
    ) -> Tuple[bool, float, float, Optional[str]]:
        """
        Exponentially Weighted Moving Average (EWMA).
        Detects creeping trends, memory leaks, and regime changes that static thresholds miss.
        Returns:
            (is_anomaly, ewma_mean, residual, explanation)
        """
        if not history:
            return False, current_value, 0.0, None

        ewma = history[0]
        residuals = []
        for val in history[1:]:
            res = abs(val - ewma)
            residuals.append(res)
            ewma = (alpha * val) + ((1.0 - alpha) * ewma)

        current_residual = abs(current_value - ewma)
        avg_residual = (sum(residuals) / len(residuals)) if residuals else 1.0

        is_drift = current_residual > (drift_factor * max(avg_residual, 2.0))
        explanation = None
        if is_drift:
            explanation = (
                f"Persistent trend divergence: Current value {current_value:.1f} diverged "
                f"from smoothed moving average {ewma:.1f} with residual {current_residual:.1f} "
                f"(expected variance {avg_residual:.1f})."
            )

        return is_drift, round(ewma, 2), round(current_residual, 2), explanation

    @staticmethod
    def compute_velocity_spike(
        current_value: float,
        previous_value: Optional[float],
        time_delta_seconds: float = 15.0,
        max_rate_per_sec: float = 3.0
    ) -> Tuple[bool, float, Optional[str]]:
        """
        Velocity Rate-of-Change Detection.
        Flags sudden rapid acceleration (e.g., CPU ramping 50% in 10 seconds).
        Returns:
            (is_anomaly, rate_of_change, explanation)
        """
        if previous_value is None or time_delta_seconds <= 0:
            return False, 0.0, None

        delta = current_value - previous_value
        rate = abs(delta) / time_delta_seconds
        is_spike = rate >= max_rate_per_sec

        explanation = None
        if is_spike:
            direction = "accelerated" if delta > 0 else "collapsed"
            explanation = (
                f"Rapid rate of change: Metric {direction} by {abs(delta):.1f} units in "
                f"{time_delta_seconds:.0f}s ({rate:.2f}/sec vs safe velocity {max_rate_per_sec:.1f}/sec)."
            )

        return is_spike, round(rate, 2), explanation
