# ObserVault Phase 4: Production Deployment & Operations Guide

**Document ID:** OV-DOC-P4-004  
**Status:** Approved  
**Date:** 2026-11-21  
**Version:** 1.0.0  
**Target Environments:** On-Premises, Hybrid Cloud, Virtualized Windows/Linux  

---

## 1. System Requirements & Prerequisites

### 1.1 Backend Server
- **Operating System:** Windows Server 2019/2022, Windows 10/11, or Linux (Ubuntu 22.04 LTS / RHEL 9)
- **Python:** Version 3.10 to 3.14 (Verified on Python 3.14.0)
- **Database:** SQLite (Default / Lightweight) or PostgreSQL 14+ (Recommended for enterprise multi-tenant production)
- **Hardware Minimums:** 2 vCPU, 4 GB RAM, 20 GB SSD storage

### 1.2 Frontend Web Server
- **Node.js:** Node.js 18.x or 20.x LTS
- **Package Manager:** npm 9+ or pnpm
- **Web Server:** Nginx 1.20+, Caddy 2, or Cloudflare Pages

### 1.3 Monitored Host (Collector Agent)
- **Production Verified:** Windows Server 2016+, Windows 10/11 (PowerShell 5.1+, Python 3.10+)
- **Experimental / Unverified Runtime:** Linux distributions with Python 3.10+ (requires manual testing on target host)
- **Network Access:** Outbound HTTPS (Port 443 or custom API port) to ObserVault backend. No inbound ports required.

---

## 2. Environment Configuration

Create a production `.env` file in the project root based on `.env.example`:

```ini
# ==============================================================================
# ObserVault Production Environment Configuration
# ==============================================================================

# Core Application Settings
PROJECT_NAME="ObserVault SaaS Observability Platform"
VERSION="1.0.0"
API_V1_STR="/api/v1"
SECRET_KEY="REPLACE_WITH_A_SECURE_RANDOM_256_BIT_SECRET_KEY"
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Database Connection (SQLite or PostgreSQL)
# PostgreSQL Example: postgresql://user:password@localhost:5432/observault_prod
DATABASE_URL="sqlite:///./observault_saas.db"

# CORS Configuration (Restrict to your actual frontend domain)
CORS_ORIGINS='["https://observault.yourdomain.com", "http://localhost:5173"]'

# Groq AI Intelligence Engine Configuration
GROQ_API_KEY="gsk_your_real_groq_api_key_here"
GROQ_MODEL="openai/gpt-oss-120b"
GROQ_TIMEOUT_SECONDS=45.0
GROQ_MAX_TOKENS=3500
GROQ_TEMPERATURE=0.2

# Collector Heartbeat & Health Thresholds
HEARTBEAT_TIMEOUT_SECONDS=90
OFFLINE_ALERT_THRESHOLD_SECONDS=180
```

> [!CAUTION]
> Never commit `.env` containing real API keys or secrets to version control. The repository `.gitignore` explicitly excludes `.env`.

---

## 3. Database Setup & Initialization

ObserVault automatically handles table creation and schema patching on startup:

1. **Automatic Initialization:**
   When the FastAPI backend starts, `Base.metadata.create_all(bind=engine)` creates all necessary tables (`tenants`, `users`, `servers`, `collectors`, `telemetry_records`, `alerts`, `incidents`, `trace_spans`, `recommendations`, etc.).
2. **Dynamic Schema Patching:**
   `patch_database_schema(engine)` verifies that all required columns (e.g., `collector_id`, `evidence_summary`, `incident_code`) exist and applies non-destructive schema adjustments.
3. **Seed Data:**
   Default tenant (`acme-fintech`) and initial administrator credentials (`admin@acmefintech.io`) are seeded automatically if the database is newly initialized.

---

## 4. Backend Deployment

### 4.1 Installing Dependencies
From the repository root, install backend requirements:
```powershell
# Windows PowerShell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
```

### 4.2 Running the Backend (Production Uvicorn)
```powershell
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --workers 4 --proxy-headers
```

### 4.3 Running with Docker Compose
```bash
docker-compose up -d backend
```

### 4.4 Nginx Reverse Proxy Configuration (Recommended)
```nginx
server {
    listen 80;
    server_name observault.yourdomain.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name observault.yourdomain.com;

    ssl_certificate /etc/ssl/certs/observault.crt;
    ssl_certificate_key /etc/ssl/private/observault.key;

    # Frontend Static SPA
    location / {
        root /var/www/observault/dist;
        try_files $uri $uri/ /index.html;
    }

    # Backend API Routing (handles /api/v1/dashboard/summary and /overview cleanly)
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Health Check
    location /health {
        proxy_pass http://127.0.0.1:8000/health;
        proxy_set_header Host $host;
    }
}
```

---

## 5. Frontend Production Build & Deployment

### 5.1 Building the Bundle
Navigate to the `frontend/` directory and run the production build:
```powershell
cd frontend
npm install
npm run build
```
The compiled static assets will be output to `frontend/dist/`.

### 5.2 Deployment
Copy the contents of `frontend/dist/` to your web server document root (e.g., `/var/www/observault/dist`).

---

## 6. Monitored Host Collector Deployment

### 6.1 Step 1: Generate Enrollment Token
In the ObserVault UI:
1. Navigate to **Collector Management** (`/collectors`).
2. Click **Generate New Token**.
3. Copy the token or the one-line automated installation command.

### 6.2 Step 2: Automated Windows Installation
On the target Windows Server, open an elevated PowerShell prompt (Run as Administrator) and execute:
```powershell
# One-line automated enrollment and daemon startup:
.\install_observault_collector.ps1 -BackendUrl "https://observault.yourdomain.com" -EnrollmentToken "YOUR_ENROLLMENT_TOKEN"
```

The script will:
- Validate Python and dependencies (`psutil`, `requests`).
- Perform cryptographic enrollment handshake (`POST /api/v1/collectors/enroll`).
- Store the device JWT securely in `collector/config/collector_config.json`.
- Initialize the local SQLite offline buffer (`collector/collector_buffer.db`).
- Register and launch the collector background service.

### 6.3 Step 3: Managing the Collector Service
- Check Status: `.\status_collector.ps1`
- Stop Daemon: `.\stop_collector.ps1`
- Start Daemon: `.\start_collector.ps1`
- Register Windows Service: `.\register_windows_service.ps1`
- Unregister Windows Service: `.\unregister_windows_service.ps1`

### 6.4 Offline Buffering & Resiliency
If network connectivity between the target host and the ObserVault backend drops:
- The collector automatically diverts telemetry batches into the local SQLite database (`collector/collector_buffer.db`).
- Metrics continue recording locally every 10 seconds without dropping data.
- The dashboard indicates the collector as `offline` when heartbeats stop for $> 90\text{ seconds}$.
- Once connectivity is restored, the collector automatically flushes buffered batches in chronological order with exponential backoff on retries.

---

## 7. Verification & Operational Health Check

### 7.1 Backend Health
Verify the backend service is healthy:
```bash
curl -X GET https://observault.yourdomain.com/health
# Expected Output:
# {"status":"healthy","service":"ObserVault SaaS Backend","version":"1.0.0","privacy_enforcement":"strict_allowlist_active"}
```

### 7.2 AI Service Availability Check
Check the Groq AI gateway status:
```bash
curl -X GET https://observault.yourdomain.com/api/v1/ai/status -H "Authorization: Bearer <TOKEN>"
# Expected Output:
# {"status":"available","model":"openai/gpt-oss-120b","configured":true,"masked_key":"gsk_...","timeout_seconds":45.0}
```

### 7.3 Operational Runbook & Troubleshooting

| Symptom | Probable Cause | Corrective Action |
|---------|----------------|-------------------|
| Collector shows `offline` in UI | Collector process terminated or firewall blocking port 443/8000. | Check collector logs on target host (`collector/logs/collector.log`). Run `.\status_collector.ps1`. Verify egress HTTPS access. |
| AI Copilot returns HTTP 503 | `GROQ_API_KEY` is missing or placeholder. | Verify `.env` file on backend contains a valid Groq API key and restart backend. |
| AI queries return HTTP 404 for incident | Incident belongs to a different tenant. | Verify the authenticated user's tenant ID matches the incident's tenant ID. Cross-tenant access is strictly denied. |
| Dashboard returns 404 for `/summary` | Outdated backend routing. | Verify `backend/app/api/dashboard.py` contains the OV-BUG-004 fix with `@router.get("/summary")`. |
