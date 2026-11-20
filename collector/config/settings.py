# collector/config/settings.py
import os
import json
import socket
from pathlib import Path

class CollectorSettings:
    def __init__(self):
        self.load()

    def load(self):
        # 1. Attempt to load from enrolled collector_config.json if present
        config_data = {}
        candidate_paths = [
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "ObserVault", "Collector", "collector_config.json"),
            str(Path(__file__).parent / "collector_config.json"),
            "/etc/observault/collector_config.json"
        ]
        for p in candidate_paths:
            if p and os.path.exists(p):
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        config_data = json.load(f)
                    break
                except Exception:
                    pass

        # Collector Identification
        self.COLLECTOR_ID: str = os.getenv("COLLECTOR_ID", config_data.get("collector_id", "col-acme-edge-01"))
        self.COLLECTOR_NAME: str = os.getenv("COLLECTOR_NAME", config_data.get("collector_name", "Acme On-Prem Core Collector"))
        self.COLLECTOR_VERSION: str = "1.0.0"
        
        # Server / Host Identification
        self.HOSTNAME: str = os.getenv("HOSTNAME", socket.gethostname())
        self.SERVER_ID: str = os.getenv("SERVER_ID", config_data.get("server_id", f"srv-{socket.gethostname().lower()}"))
        
        # Backend Connectivity
        self.BACKEND_URL: str = os.getenv("OBSERVAULT_BACKEND_URL", config_data.get("backend_url", "http://127.0.0.1:8000"))
        self.COLLECTOR_KEY: str = os.getenv("OBSERVAULT_COLLECTOR_KEY", config_data.get("collector_key", "ov_col_acme_production_secret_key_2026"))
        
        # Timing
        self.COLLECTION_INTERVAL_SECONDS: int = int(os.getenv("COLLECTION_INTERVAL", str(config_data.get("collection_interval", 5))))
        self.HEARTBEAT_INTERVAL_SECONDS: int = int(os.getenv("HEARTBEAT_INTERVAL", str(config_data.get("heartbeat_interval", 15))))
        
        # Local SQLite Buffer Storage
        self.BUFFER_DB_PATH: str = str(Path(__file__).parent.parent / "collector_buffer.db")
        self.MAX_BUFFER_RECORDS: int = 10000

settings = CollectorSettings()
