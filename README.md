# ObserVault
### Privacy-First, Secure and Automated Observability Platform

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg)](https://fastapi.tiangolo.com)
[![React 18](https://img.shields.io/badge/React-18-61dafb.svg)](https://react.dev)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind-3.4-38bdf8.svg)](https://tailwindcss.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> **Core USP:** *"ObserVault helps organisations understand what is happening across their IT infrastructure, identify why problems may be occurring, and respond faster — without sending sensitive raw operational data outside their environment."*

---

## 1. Problem Statement & Proposed Solution

Modern enterprises operating in finance, healthcare, telecommunications, and defence face a critical observability dilemma:
1. Cloud observability platforms demand full ingestion of raw logs, metrics, and network traces.
2. These raw streams frequently leak passwords, API keys, JWT access tokens, customer PII, and internal stack traces into third-party cloud data stores.
3. Network interruptions cause telemetry blackouts and lost operational data.
4. Engineers suffer from severe alert fatigue caused by un-correlated point-in-time alerts.

**The ObserVault Solution:**
ObserVault introduces a **Two-Tier Architecture**:
- **Tier 1 (Local Customer Environment):** A lightweight Python collector runs on-premises. It captures physical infrastructure metrics (`psutil`) and inspects raw operational events locally. A strict **Metadata Allow-List** strips all credentials, passwords, tokens, and sensitive fields at the edge. Outbound records are buffered in a local **SQLite database** to survive internet outages with zero data loss.
- **Tier 2 (Central SaaS Cloud):** The FastAPI backend authenticates incoming collectors using cryptographic keys, validates incoming records against a strict allow-list (forbidding unknown fields), stores approved telemetry in PostgreSQL/SQLite, executes rule-based anomaly detection, correlates related events into unified incidents, and produces human-in-the-loop recommendations on a React dashboard.

---

## 2. Project Architecture

```
+-------------------------------------------------------------------------+
|                  TIER 1: LOCAL CUSTOMER PERIMETER                       |
|                                                                         |
|  +--------------------+     +----------------------------------------+  |
|  | Hardware & Network |     | Local Privacy Engine                   |  |
|  | psutil Live Metrics| --> | - Scans for Passwords, Tokens, Secrets |  |
|  +--------------------+     | - Applies Strict Metadata Allow-List   |  |
|                             +-------------------+--------------------+  |
|                                                 |                       |
|                                                 v                       |
|  +--------------------+     +----------------------------------------+  |
|  | Secure Sender      | <-- | Local SQLite Offline Buffer            |  |
|  | X-Collector-Key    |     | - Zero Record Loss During Outages      |  |
|  +---------+----------+     | - Deduplication & Replay Queue         |  |
+------------|----------------+----------------------------------------+--+
             |
             | Authenticated TLS 1.3 Outbound (ONLY Approved Metadata)
             v
+-------------------------------------------------------------------------+
|                  TIER 2: CENTRAL SAAS PLATFORM                          |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  | FastAPI Ingestion Gateway (Strict Pydantic extra='forbid' Check)  |  |
|  +----------------------------------+--------------------------------+  |
|                                     |                                   |
|       +-----------------------------+-----------------------------+     |
|       v                                                           v     |
|  +-----------------------------+     +-------------------------------+  |
|  | Multi-Tenant Database       |     | Explainable Anomaly Detection |  |
|  | (PostgreSQL / SQLite)       |     | (Deduplicating Alert Engine)  |  |
|  +-----------------------------+     +---------------+---------------+  |
|                                                      |                  |
|                                                      v                  |
|  +-----------------------------+     +-------------------------------+  |
|  | React 18 Enterprise UI      | <-- | Incident Correlation Engine   |  |
|  | - Live HUD Overview         |     | (Multi-Signal Root Causes)    |  |
|  | - Privacy Egress Proof      |     +---------------+---------------+  |
|  | - Scenario Simulator Bar    |                     |                  |
|  +-----------------------------+                     v                  |
|                                      +-------------------------------+  |
|                                      | Actionable Advisor Engine     |  |
|                                      | (Human-Approval Protocol)     |  |
|                                      +-------------------------------+  |
+-------------------------------------------------------------------------+
```

---

## 3. Technology Stack

- **Frontend:** React 18, Vite, Tailwind CSS, Recharts, Lucide React, React Router v6
- **Backend:** Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2.0, Uvicorn, PyJWT, Bcrypt
- **Collector:** Python, `psutil`, SQLite3, `requests`
- **Databases:** PostgreSQL (production / Docker), SQLite (portable local demo & edge collector buffer)
- **Testing:** Pytest, HTTP test harness

---

## 4. Quick Start (Step-by-Step)

### Prerequisites
- Python 3.10 or higher
- Node.js 18+ and npm

### Method A: One-Command Python Orchestrator
```bash
# Clone or navigate to the repository
cd observault

# Install Python dependencies
pip install -r backend/requirements.txt
pip install -r collector/requirements.txt

# Run the unified orchestrator (seeds DB, boots backend, starts collector)
python start_demo.py
```
In a second terminal, start the React frontend:
```bash
cd frontend
npm install
npm run dev
```
Open **`http://localhost:5173`** in your browser.

---

### Method B: Docker Compose (Production-Ready)
```bash
docker compose up --build
```
- Dashboard: `http://localhost:5173`
- SaaS API: `http://localhost:8000`
- PostgreSQL: `localhost:5432`

---

## 5. Demo Login Credentials

The database comes pre-seeded with two fully isolated sample enterprise tenants:

| Organization | Email | Password | Role | Plan |
|---|---|---|---|---|
| **Acme FinTech Corp** | `admin@acme.com` | `Password123!` | SecOps Director (Admin) | Enterprise Shield |
| **Acme FinTech Corp** | `sre@acme.com` | `Password123!` | Senior SRE (Engineer) | Enterprise Shield |
| **BioHealth Global** | `admin@biohealth.com` | `Password123!` | CMIO (Admin) | Healthcare Compliance |

*Use the **Switch Tenant** button in the dashboard navigation to test multi-tenant data isolation instantly.*

---

## 6. Project Structure

```text
observault/
├── backend/
│   ├── app/
│   │   ├── api/             # REST endpoints (auth, telemetry, alerts, incidents, egress, simulator)
│   │   ├── core/            # Config, database session, JWT & hashing security
│   │   ├── detection/       # Anomaly engine with deduplication
│   │   ├── correlation/     # Incident correlator linking multi-symptom alerts
│   │   ├── recommendations/ # Human-approval remediation advisor
│   │   ├── models/          # SQLAlchemy relational models
│   │   ├── schemas/         # Strict Pydantic allow-lists (extra='forbid')
│   │   ├── main.py          # FastAPI application entrypoint
│   │   ├── seed.py          # Multi-tenant demo seeder
│   │   └── run.py           # Uvicorn runner
│   ├── Dockerfile
│   └── requirements.txt
│
├── collector/
│   ├── collectors/          # psutil physical metrics & socket network metrics
│   ├── privacy/             # Local privacy sanitiser & allow-list
│   ├── buffer/              # Local SQLite offline buffer & retry queue
│   ├── transport/           # Authenticated secure sender & heartbeat
│   ├── simulator/           # Scenario generator for benchmarks
│   ├── config/              # Collector settings
│   ├── main.py              # CLI runner (live, simulate, offline, test-privacy)
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── components/      # StatCard, StatusBadge, ChartCard, PrivacyFlowGraphic, SimulatorModal
│   │   ├── context/         # AuthContext & Multi-Tenant Switcher
│   │   ├── pages/           # 10 Enterprise SaaS dashboard pages
│   │   ├── services/        # REST API client
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── Dockerfile
│   └── package.json
│
├── database/
│   └── schema.sql           # Complete PostgreSQL DDL
│
├── tests/
│   ├── test_privacy.py           # Strict credential purge & Pydantic extra-field check
│   ├── test_tenant_isolation.py  # Cryptographic tenant data isolation
│   ├── test_anomaly_detection.py # Threshold breaching & alert deduplication
│   ├── test_buffering.py         # SQLite offline queue & duplicate prevention
│   └── test_end_to_end.py        # End-to-end telemetry pipeline verification
│
├── docs/
│   ├── ARCHITECTURE.md
│   └── DEMO_GUIDE.md
├── docker-compose.yml
├── start_demo.py
├── .env.example
└── README.md
```

---

## 7. Running the Automated Test Suite

All 6 test suites can be executed with pytest:
```bash
python -m pytest tests/ -v
```
**Test Coverage:**
- `test_privacy.py`: Asserts passwords, bearer tokens, API keys, and client IPs are completely purged; verifies backend schema rejects unapproved fields.
- `test_tenant_isolation.py`: Verifies disjoint sets for servers, collectors, and user claims between Acme and BioHealth.
- `test_anomaly_detection.py`: Verifies threshold breach detection and deduplication of recurring alerts.
- `test_buffering.py`: Validates SQLite buffer enqueue, offline persistence, delivery confirmation, and duplicate prevention.
- `test_end_to_end.py`: End-to-end validation from collector generation -> privacy filter -> ingestion -> anomaly detection -> correlation -> recommendation -> leak check.

---

## 8. Five Demonstration Scenarios

1. **Demo 1 (Normal Infrastructure):** Real live hardware metrics from `psutil` streaming into the overview dashboard.
2. **Demo 2 (Privacy Protection & Zero Cloud Leak):** Interactive playground on the **Privacy & Egress** page allows inputting fake passwords/tokens and proves they never reach cloud storage.
3. **Demo 3 (Anomaly Detection & Correlation):** Click **Simulate Anomaly** to trigger High CPU or Service Crash; observe automated alert deduplication and incident correlation.
4. **Demo 4 (Network Outage & SQLite Buffering):** Run `python collector/main.py --mode live --offline` to observe local buffer accumulation and automatic replay without duplicate records.
5. **Demo 5 (Multi-Tenant Isolation):** Click **Switch Tenant** in the top bar to verify total cryptographic separation of servers, alerts, and settings.
