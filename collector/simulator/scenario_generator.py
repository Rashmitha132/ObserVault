# collector/simulator/scenario_generator.py
import uuid
import random
from datetime import datetime, timezone
from typing import Dict, Any

class ScenarioGenerator:
    """
    Generates labelled simulated telemetry scenarios for demonstration and benchmarking.
    All outputs strictly flag `is_simulated = True`.
    """
    def __init__(self, server_id: str = "srv-sim-cluster-01", hostname: str = "sim-cluster-01"):
        self.server_id = server_id
        self.hostname = hostname

    def generate(self, scenario_name: str = "normal") -> Dict[str, Any]:
        now_iso = datetime.now(timezone.utc).isoformat()
        scenario_name = scenario_name.lower()

        base = {
            "event_id": str(uuid.uuid4()),
            "timestamp": now_iso,
            "server_id": self.server_id,
            "hostname": self.hostname,
            "is_simulated": True
        }

        if scenario_name == "high_cpu":
            # High CPU breach scenario
            base.update({
                "cpu_percent": round(random.uniform(93.0, 98.5), 1),
                "memory_percent": round(random.uniform(75.0, 84.0), 1),
                "disk_percent": 55.0,
                "network_latency_ms": round(random.uniform(130.0, 165.0), 1),
                "packet_loss_percent": 0.0,
                "network_status": "connected",
                "failed_login_count": 0,
                "service_status": "degraded"
            })
        elif scenario_name == "network_failure":
            # Heavy latency & packet loss
            base.update({
                "cpu_percent": 35.0,
                "memory_percent": 48.0,
                "disk_percent": 42.0,
                "network_latency_ms": round(random.uniform(250.0, 480.0), 1),
                "packet_loss_percent": round(random.uniform(8.5, 22.0), 1),
                "network_status": "degraded",
                "failed_login_count": 0,
                "service_status": "degraded"
            })
        elif scenario_name == "security_event":
            # Repeated failed login attacks containing fake raw passwords to test local sanitizer!
            base.update({
                "event_type": "failed_login",
                "failed_attempt_count": random.randint(5, 12),
                "cpu_percent": 65.0,
                "memory_percent": 58.0,
                "disk_percent": 50.0,
                "network_latency_ms": 32.0,
                "packet_loss_percent": 0.0,
                "network_status": "connected",
                "service_status": "up",
                # SENSITIVE FIELDS IN RAW EVENT (WILL BE STRIPPED BY LOCAL SANITIZER):
                "username": "root_admin",
                "password": "FakePassword99!DoNotLeak",
                "auth_token": "bearer_jwt_secret_fake_token_xyz123",
                "api_key": "sk_live_fake_test_key_abc456",
                "raw_request_payload": "POST /api/v1/auth/login HTTP/1.1 {user: admin}"
            })
        elif scenario_name == "application_failure":
            # Application crash / disk full
            base.update({
                "cpu_percent": 18.0,
                "memory_percent": 30.0,
                "disk_percent": 94.5,
                "network_latency_ms": 500.0,
                "packet_loss_percent": 30.0,
                "network_status": "disconnected",
                "failed_login_count": 0,
                "service_status": "down"
            })
        else:
            # Normal operating conditions
            base.update({
                "cpu_percent": round(random.uniform(22.0, 45.0), 1),
                "memory_percent": round(random.uniform(40.0, 60.0), 1),
                "disk_percent": round(random.uniform(45.0, 58.0), 1),
                "network_latency_ms": round(random.uniform(15.0, 35.0), 1),
                "packet_loss_percent": 0.0,
                "network_status": "connected",
                "failed_login_count": 0,
                "service_status": "up"
            })

        return base
