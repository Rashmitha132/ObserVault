# backend/app/core/config.py
import os
from pathlib import Path
from pydantic import BaseModel
from typing import List

# Use absolute path so the DB location is invariant to the working directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_DB_FILE = BASE_DIR / "observault_saas.db"
DEFAULT_DB_URL = f"sqlite:///{DEFAULT_DB_FILE.as_posix()}"

def _load_dotenv_if_present():
    """Reliably loads environment variables from .env if present without assuming automatic loading."""
    candidates = [
        BASE_DIR / ".env",
        BASE_DIR.parent / ".env",
        Path.cwd() / ".env"
    ]
    for p in candidates:
        if p.exists() and p.is_file():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#") or "=" not in line:
                            continue
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip("'\"")
                        if k and k not in os.environ:
                            os.environ[k] = v
            except Exception:
                pass
            break

_load_dotenv_if_present()

class Settings(BaseModel):
    PROJECT_NAME: str = "ObserVault SaaS Backend"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "observault-insecure-dev-secret-key-change-in-prod-2026")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
    # Database (Absolute path default)
    DATABASE_URL: str = os.getenv("DATABASE_URL", DEFAULT_DB_URL)
    
    # CORS
    CORS_ORIGINS: List[str] = ["*"]
    
    # Collector heartbeat timeout (seconds)
    HEARTBEAT_TIMEOUT_SECONDS: int = 60
    
    # Anomaly Thresholds defaults
    DEFAULT_CPU_THRESHOLD: float = 90.0
    DEFAULT_MEMORY_THRESHOLD: float = 90.0
    DEFAULT_DISK_THRESHOLD: float = 85.0
    DEFAULT_LATENCY_THRESHOLD_MS: float = 120.0
    DEFAULT_PACKET_LOSS_THRESHOLD: float = 5.0
    DEFAULT_FAILED_LOGIN_THRESHOLD: int = 3

    # Groq AI Intelligence Configuration (Phase 3)
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    GROQ_TIMEOUT_SECONDS: float = float(os.getenv("GROQ_TIMEOUT_SECONDS", "15.0"))
    GROQ_MAX_TOKENS: int = int(os.getenv("GROQ_MAX_TOKENS", "1024"))
    GROQ_TEMPERATURE: float = float(os.getenv("GROQ_TEMPERATURE", "0.2"))

settings = Settings()
