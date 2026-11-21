# backend/app/run.py
import os
import sys
from pathlib import Path
import uvicorn

# Ensure backend root is on sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.seed import seed_database

if __name__ == "__main__":
    # Ensure database is seeded with demo organizations
    seed_database()
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    print(f"Starting ObserVault SaaS Backend on http://{host}:{port} ...")
    uvicorn.run("app.main:app", host=host, port=port, reload=False)
