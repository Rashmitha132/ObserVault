# ObserVault

<div align="center">

# 🛡️ ObserVault
### Privacy-First, Secure and Automated Two-Tier Observability Platform

[![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18.2-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-3.4-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white)](https://tailwindcss.com/)
[![SQLite](https://img.shields.io/badge/SQLite-Offline_Buffer-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://sqlite.org/)
[![Groq Cloud](https://img.shields.io/badge/Groq-GPT_OSS_120B-F55036?style=for-the-badge&logo=openai&logoColor=white)](https://groq.com/)
[![Tests](https://img.shields.io/badge/Tests-97%20Passing%20(100%25)-brightgreen?style=for-the-badge&logo=pytest&logoColor=white)](tests/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=for-the-badge)](LICENSE)

<br />

> **Core Value Proposition:**  
> *"ObserVault helps enterprises understand what is happening across their IT infrastructure, identify why problems occur, and respond faster — without sending sensitive raw operational data outside their security perimeter."*

</div>

---

## 📑 Table of Contents

- [1. Executive Summary & Problem Statement](#1-executive-summary--problem-statement)
- [2. Target Audience & Business Value](#2-target-audience--business-value)
- [3. Two-Tier Architectural Design](#3-two-tier-architectural-design)
  - [Tier 1: Local Customer Environment (Edge Collector)](#tier-1-local-customer-environment-edge-collector)
  - [Boundary Transit: Cryptographic Handshake & Zero-Egress Assurance](#boundary-transit-cryptographic-handshake--zero-egress-assurance)
  - [Tier 2: Central ObserVault SaaS Platform](#tier-2-central-observault-saas-platform)
- [4. Core Platform Capabilities & Intelligence Layers](#4-core-platform-capabilities--intelligence-layers)
  - [Local Privacy Policy Gate & Sanitization](#1-local-privacy-policy-gate--sanitization)
  - [Offline-Resilient SQLite Spooling & Deduplication](#2-offline-resilient-sqlite-spooling--deduplication)
  - [Statistical & Machine Learning Anomaly Detection (Isolation Forest)](#3-statistical--machine-learning-anomaly-detection-isolation-forest)
  - [Topological Incident Correlation & Causal RCA](#4-topological-incident-correlation--causal-rca)
  - [Predictive Capacity Forecaster & SLO Risk Analytics](#5-predictive-capacity-forecaster--slo-risk-analytics)
  - [Generative AI SRE Copilot & Automated Remediation (Groq 120B)](#6-generative-ai-sre-copilot--automated-remediation-groq-120b)
- [5. Application Walkthrough: The 10 Enterprise Pages](#5-application-walkthrough-the-10-enterprise-pages)
- [6. Technology Stack](#6-technology-stack)
- [7. Quickstart & Installation Guide](#7-quickstart--installation-guide)
  - [Method A: Full Automated Demo Orchestrator (Windows & Linux)](#method-a-full-automated-demo-orchestrator-windows--linux)
  - [Method B: Manual Component-by-Component Execution](#method-b-manual-component-by-component-execution)
  - [Method C: Production Docker Compose Deployment](#method-c-production-docker-compose-deployment)
- [8. Edge Collector Enrollment & Background Daemon](#8-edge-collector-enrollment--background-daemon)
- [9. Demo Scenarios & Verification Guide](#9-demo-scenarios--verification-guide)
- [10. Automated Testing & Verification Suite](#10-automated-testing--verification-suite)
- [11. Security, Privacy & Compliance Matrix](#11-security-privacy--compliance-matrix)
- [12. Repository Structure](#12-repository-structure)
- [13. License & Acknowledgments](#13-license--acknowledgments)

---

## 1. Executive Summary & Problem Statement

Modern enterprises in **banking, healthcare, defence, telecommunications, and government** face an acute operational paradox:
1. **The Cloud APM Dilemma:** Traditional SaaS observability suites (Datadog, Dynatrace, New Relic) require streaming unencrypted, raw operational telemetry across public networks into external cloud repositories.
2. **Catastrophic Data Leakage:** Unfiltered log lines, network traces, and core dumps inevitably contain embedded database connection strings, bearer tokens, passwords, customer PII, HIPAA-governed patient records, and PCI-DSS cardholder data.
3. **Network Outage Blindness:** When edge connectivity degrades or WAN links drop, standard agent forwarders drop metrics or freeze, blinding operators during catastrophic infrastructure failures.
4. **Alert Fatigue:** A single downstream failure (e.g. database connection pool exhaustion) cascades into hundreds of un-correlated point-in-time alerts, overwhelming incident response teams.

**The ObserVault Breakthrough:**  
ObserVault solves this trade-off through a **Two-Tier Architecture**. By separating the collection, reduction, and privacy validation boundary (Tier 1) from the central correlation, forecasting, and visualization engine (Tier 2), ObserVault guarantees that **only pre-approved, strictly sanitized telemetry metadata crosses the enterprise boundary**.

---

## 2. Target Audience & Business Value

| Stakeholder Persona | Key Operational Frustration | How ObserVault Solves It |
|---|---|---|
| **Chief Information Security Officers (CISOs)** | Compliance audits (GDPR, HIPAA, SOC 2, DPDP Act 2023) blocked by raw telemetry data leaving company VPCs. | Edge Privacy Policy Gate guarantees zero PII or credentials leave on-premise infrastructure. Strict schema enforcement (`extra='forbid'`) rejects unauthorized fields at ingestion. |
| **Site Reliability Engineers (SREs)** | Alert fatigue from hundreds of firing alerts during a cascading outage. | Topological Incident Correlation groups multi-server symptoms into a single causal incident, pinpointing root cause with topological graph traversal. |
| **DevOps & Platform Teams** | Agent setup is tedious and fragile during network partitions. | 1-line copyable PowerShell/Bash onboarding script; local SQLite edge buffer prevents any data loss during internet outages and replays automatically upon reconnection. |
| **Capacity Planners & Directors** | Unexpected disk, memory, or thread pool exhaustion outages. | Predictive Scikit-Learn linear regression models forecast exact days-to-exhaustion and assign SLO breach probabilities before outages occur. |

---

## 3. Two-Tier Architectural Design

ObserVault implements a rigorous two-tier operational model separating local edge telemetry gathering from central intelligence:

```
+-----------------------------------------------------------------------------------+
|                        TIER 1 - LOCAL CUSTOMER ENVIRONMENT                        |
|                                                                                   |
|  +-----------------------------------+     +-----------------------------------+  |
|  | Servers, Applications & Networks  |     | Physical Kernel Metric Harvester  |  |
|  | Windows / Linux Hosts / Sockets   | --> | psutil Live Telemetry Collection  |  |
|  +-----------------------------------+     +-----------------+-----------------+  |
|                                                              |                    |
|                                                              v                    |
|  +-----------------------------------+     +-----------------------------------+  |
|  | Offline Resilient SQLite Buffer   |     | Edge Privacy Policy Gate          |  |
|  | Zero Record Loss During Outages   | <-- | - Metadata Strict Allow-List      |  |
|  | Deduplication & Automatic Replay  |     | - Credential & PII Sanitizer      |  |
|  +-----------------+-----------------+     +-----------------------------------+  |
+--------------------|--------------------------------------------------------------+
                     |
                     | Authenticated TLS 1.3 Outbound (HMAC / X-Collector-Key)
                     | ONLY APPROVED SANITIZED TELEMETRY CROSSES THE BOUNDARY
                     v
+-----------------------------------------------------------------------------------+
|                      TIER 2 - OBSERVAULT SAAS CENTRAL PLATFORM                     |
|                                                                                   |
|  +-----------------------------------------------------------------------------+  |
|  | FastAPI Central Ingestion Gateway                                           |  |
|  | - Authentication & Token Verification                                       |  |
|  | - Cryptographic Multi-Tenant Isolation                                      |  |
|  | - Pydantic v2 Schema Gate (extra='forbid' strictly rejects unknown fields)   |  |
|  +--------------------------------------+--------------------------------------+  |
|                                         |                                         |
|       +---------------------------------+---------------------------------+       |
|       v                                                                   v       |
|  +----------------------------------+     +------------------------------------+  |
|  | Relational Storage Layer         |     | AIOps Multimodal Engine            |  |
|  | (PostgreSQL / SQLite Isolated DB)|     | - Sliding-Window Anomaly Engine    |  |
|  +----------------------------------+     | - Scikit-Learn Isolation Forest    |  |
|                                           | - Topological Incident Correlation |  |
|                                           | - Predictive Capacity Forecaster   |  |
|                                           | - Groq 120B Generative AI Copilot  |  |
|                                           +------------------+-----------------+  |
|                                                              |                    |
|                                                              v                    |
|  +-----------------------------------------------------------------------------+  |
|  | React 18 Enterprise Single-Page Dashboard                                   |  |
|  | Real-time Telemetry HUD • Causal RCA Visualizer • Privacy Proof Playground  |  |
|  | Capacity Forecast Curves • Simulator Control • Human-in-the-Loop Advisor    |  |
|  +-----------------------------------------------------------------------------+  |
+-----------------------------------------------------------------------------------+
```

### Tier 1: Local Customer Environment (Edge Collector)
- **Local Harvester:** Polls physical OS kernel telemetry (`psutil`) every 10 seconds: CPU user/system time, memory utilization, disk I/O throughput, active network socket states, and running process counts.
- **Privacy Policy Gate (`collector/privacy/`):** The edge firewall for observability data. It scans every telemetry payload, strips forbidden keys (passwords, tokens, cookies, auth headers, PII), and evaluates all fields against a **Strict Allow-List**.
- **Offline SQLite Buffer (`collector/buffer/`):** During network partitions or SaaS maintenance windows, sanitized records are spooled into a local transactional SQLite database (`collector_buffer.db`). Once connectivity restores, records are dequeued and replayed chronologically with deduplication tokens to prevent double-counting.

### Boundary Transit: Cryptographic Handshake & Zero-Egress Assurance
- Communication between Tier 1 and Tier 2 occurs strictly over **TLS 1.3 encrypted HTTPS**.
- Each edge collector authenticates via an enrollment key header (`X-Collector-Key`) validated against the tenant's cryptographic signature store.
- **Zero-Egress Guarantee:** Raw payloads, environment variables, customer application memory, and unapproved attributes are physically blocked at the edge; only mathematical metrics and sanitized metadata reach the network socket.

### Tier 2: Central ObserVault SaaS Platform
- **FastAPI Ingestion Gateway:** Enforces strict Pydantic v2 validation (`model_config = ConfigDict(extra="forbid")`). Any payload attempting to transmit non-allowlisted keys is rejected with an HTTP 422 error.
- **Tenant Isolation:** Enforces strict logical and relational data partitioning. Queries, incidents, metrics, and alerts are permanently scoped to the authenticated `tenant_id`.
- **AIOps & ML Engine:** Runs automated anomaly scoring, causal graph reduction, days-to-exhaustion forecasting, and LLM-assisted incident analysis.
- **React 18 Frontend:** High-density, real-time command dashboard with zero-lag WebSocket/REST polling, live HUD metrics, interactive topology maps, and interactive remediation runbooks.

---

## 4. Core Platform Capabilities & Intelligence Layers

### 1. Local Privacy Policy Gate & Sanitization
The collector includes a dedicated multi-stage sanitization pipeline:
* **Pattern-Based Credential Stripping:** RegEx engines detect and redact JWT tokens, Bearer headers, AWS secret keys, database connection URIs (`postgres://user:pass@host`), and private RSA/ED25519 keys.
* **Strict Metadata Allow-Listing:** Only explicitly permitted operational metrics are serialized:
  `timestamp`, `server_id`, `cpu_usage`, `memory_usage`, `disk_usage`, `io_read_bytes`, `io_write_bytes`, `network_rx_bytes`, `network_tx_bytes`, `active_connections`, `error_rate_percent`, `response_time_ms`.
* **Zero Payload Egress:** Payload bodies, HTTP request headers, and customer database queries are never captured or forwarded.

### 2. Offline-Resilient SQLite Spooling & Deduplication
* If the SaaS endpoint returns HTTP 5xx or fails with connection timeouts, the collector enters **Offline Buffer Mode**.
* Telemetry records are enqueued into a local WAL-mode SQLite buffer database.
* Upon network recovery, a background drain worker delivers buffered records in batches using idempotent replay IDs, preventing alert spikes from replayed historical data.

### 3. Statistical & Machine Learning Anomaly Detection (Isolation Forest)
ObserVault combines deterministic threshold algorithms with unsupervised machine learning:
* **Dual-Mechanism Detection:**
  * *Statistical Deviation:* Moving-average sliding window computes rolling z-scores; spikes exceeding $3\sigma$ trigger high-priority alerts.
  * *Unsupervised Isolation Forest (`scikit-learn`):* Anomaly detector trained on multi-dimensional telemetry (CPU, Memory, IO, Network) isolates multi-variate subtle anomalies that single-metric threshold checks miss.
* **Smart Alert Deduplication:** Prevents notification storms by deduplicating recurring alert states within configurable cooldown windows.

### 4. Topological Incident Correlation & Causal RCA
Rather than alerting on 50 distinct server warnings, ObserVault correlates interrelated alerts:
* **Incident Correlation Engine:** Inspects system dependency topologies, network adjacency matrices, and temporal proximity ($\pm 5$ minutes).
* **Causal Graph Reasoning:** If an upstream PostgreSQL database throttles on I/O, causing API Gateway timeouts and Auth Service 504 errors, ObserVault groups all 3 symptoms into a single **Critical Root Incident**.
* **Visual RCA Topology Graph:** Highlights the offending node in red, secondary affected nodes in orange, and healthy services in emerald.

### 5. Predictive Capacity Forecaster & SLO Risk Analytics
* **Linear Regression Exhaustion Forecasting:** Computes line-of-best-fit trajectories across historical disk, CPU, and memory consumption.
* **Days-to-Exhaustion Alerting:** Flags infrastructure that will exhaust resources within 7, 14, or 30 days before service failure occurs.
* **SLO Burn Rate Tracking:** Computes real-time error budget consumption against 99.9% availability targets.

### 6. Generative AI SRE Copilot & Automated Remediation (Groq 120B)
Integrated with high-speed cloud LLMs (`openai/gpt-oss-120b` via Groq) with deterministic 0.2 temperature:
* **Natural Language Copilot Chat:** SREs can ask: *"What is causing the memory spike on prod-api-01?"* The copilot answers using live cluster telemetry and active topological graphs.
* **Instant Incident Explanation:** Generates 4-part structured diagnoses: Verified Telemetry Facts, Causal Hypothesis, Estimated Blast Radius, and Recommended Investigation Steps.
* **Human-in-the-Loop Remediation:** Generates validated, copyable PowerShell and Bash commands to remediate the incident, requiring explicit human approval (`requires_human_approval = True`) before execution.

---

## 5. Application Walkthrough: The 10 Enterprise Pages

| # | Enterprise Page | Route | Description & Key Features |
|---|---|---|---|
| 1 | **Overview Dashboard** | `/` | Executive HUD with real-time cluster health, active incidents count, live servers status, real-time telemetry throughput graphs, and quick-launch links. |
| 2 | **Infrastructure & Fleet** | `/infrastructure` | Detailed server inventory grid, live CPU/RAM/Disk gauges, server status badges, and interactive Server Inspector modal with live telemetry feeds. |
| 3 | **Alerts & Incidents** | `/alerts` | Consolidated incident command center with correlated alerts, severity filter (Critical/Warning/Info), and one-click **"AI Explain"** & **"AI Remediation"** drawers. |
| 4 | **Root Cause Analysis (RCA)** | `/rca` | Interactive node-link topology diagram mapping upstream databases to downstream APIs, causal timeline analysis, and topological AI RCA root cause identification. |
| 5 | **Predictive Analytics** | `/predictive` | Resource exhaustion forecasting with trend lines, days-to-full projections, SLO error budget tracking, and custom SLO target configurations. |
| 6 | **Collector Management** | `/collectors` | Fleet device manager showing edge collector status, heartbeat intervals, platform OS, and the **Automated Onboarding Wizard** modal with 1-click install scripts. |
| 7 | **Privacy & Egress Audit** | `/privacy` | Real-time security verification center with an interactive **Privacy Playground** where users test malicious payloads and verify that secrets never reach the SaaS backend. |
| 8 | **AI SRE Copilot Drawer** | Global Slide-Out | Persistent slide-out assistant accessible from any screen with live cluster context, suggested engineering prompts, and evidence pills. |
| 9 | **Scenario Simulator Bar** | Global Modal | Interactive chaos testing tool capable of injecting High CPU Saturation, Memory Leaks, DB Connection Exhaustion, and Cascading Outages on demand. |
| 10 | **System Audit Logs** | `/audit` | Immutable audit trail tracking operator actions, configuration changes, remediation approvals, and collector authentication events. |

---

## 6. Technology Stack

### Backend Core
- **Language:** Python 3.10+ / 3.11+
- **Framework:** FastAPI (0.110+)
- **Validation:** Pydantic v2 (`ConfigDict(extra="forbid")`)
- **ORM & DB:** SQLAlchemy 2.0 with PostgreSQL (Production) / SQLite (Local Demo)
- **Security:** PyJWT (HS256 access tokens), Passlib & Bcrypt (password hashing)
- **AI & ML:** Groq Python SDK (Cloud 120B LLM), Scikit-Learn (Isolation Forest & Linear Regression), NumPy

### Frontend Core
- **Framework:** React 18.2 (Functional Components & Hooks)
- **Build Tool:** Vite 5.x
- **Styling:** Tailwind CSS 3.4
- **Visualizations:** Recharts (responsive time-series charts, area charts, bar graphs)
- **Icons & UI:** Lucide React, Headless UI, React Portals

### Edge Collector
- **Runtime:** Standalone Python daemon (`collector/runtime.py`)
- **System Metrics:** `psutil` (OS kernel stats across Windows & Linux)
- **Local Storage:** SQLite3 (WAL-mode offline transactional spooler)
- **HTTP Transport:** `requests` with persistent sessions and custom retry adapters

---

## 7. Quickstart & Installation Guide

### Prerequisites
- Python 3.10, 3.11, or 3.12
- Node.js 18+ and npm
- Git

---

### Method A: Full Automated Demo Orchestrator (Windows & Linux)

The repository includes a unified orchestrator script that automatically configures virtual environments, runs database migrations, seeds enterprise sample tenants, and launches the services.

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Rashmitha132/ObserVault.git
   cd ObserVault
   ```

2. **Configure Environment Variables:**
   ```bash
   # Copy sample environment configuration
   cp .env.example .env
   ```
   *(Optional)* To enable live Groq AI Copilot features, add your Groq API key in `.env`:
   ```env
   GROQ_API_KEY=gsk_your_actual_groq_api_key_here
   ```

3. **Install Dependencies & Launch Unified Demo:**
   ```bash
   # Install backend and collector dependencies
   pip install -r backend/requirements.txt
   pip install -r collector/requirements.txt

   # Run the unified orchestrator
   python start_demo.py
   ```

4. **Start the Frontend UI (in a separate terminal):**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

5. **Open the Web Console:**
   Navigate to **`http://localhost:5173`** in your browser.

---

### Method B: Manual Component-by-Component Execution

#### Step 1: Backend Setup
```bash
cd backend
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
python -m app.seed
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
*API Documentation will be live at `http://localhost:8000/docs`.*

#### Step 2: Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
*Frontend will be running at `http://localhost:5173`.*

#### Step 3: Local Collector Execution
```bash
cd collector
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
# Run live physical metric collector
python main.py --mode live
```

---

### Method C: Production Docker Compose Deployment

ObserVault includes a complete multi-container Docker configuration with PostgreSQL:

```bash
docker compose up --build
```

- **Frontend Console:** `http://localhost:5173`
- **FastAPI Gateway:** `http://localhost:8000`
- **PostgreSQL Database:** `localhost:5432`

---

## 8. Edge Collector Enrollment & Background Daemon

ObserVault makes deploying edge collectors across bare-metal servers or cloud VMs seamless:

### 1-Click Automated Windows Enrollment
Navigate to **Collector Management** (`/collectors`) -> Click **"Enroll New Collector"** -> Copy the generated PowerShell onboarding command:

```powershell
powershell -ExecutionPolicy Bypass -Command "& { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; & '.\install_observault_collector.ps1' -SaaSUrl 'http://localhost:8000' -EnrollmentKey 'YOUR_COLLECTOR_KEY' -ServerId 'YOUR_SERVER_UUID' }"
```

This automated script:
1. Verifies Python 3.10+ installation.
2. Installs required collector libraries (`psutil`, `requests`).
3. Generates a local configuration file with cryptographic keys.
4. Initializes the local SQLite offline spooling database.
5. Launches the collector as a detached, persistent background daemon (`collector/runtime.py`).

### Managing the Collector Daemon
```powershell
# Check background collector daemon status
python -m collector.runtime status

# Gracefully stop the background daemon
python -m collector.runtime stop

# Restart daemon
python -m collector.runtime restart
```

---

## 9. Demo Scenarios & Verification Guide

### Default Demo Tenant Accounts

The database comes pre-seeded with two cryptographically isolated enterprise tenants:

| Organization | Email | Password | Role | Plan |
|---|---|---|---|---|
| **Acme FinTech Corp** | `admin@acme.com` | `Password123!` | SecOps Director (Admin) | Enterprise Shield |
| **Acme FinTech Corp** | `sre@acme.com` | `Password123!` | Senior SRE (Engineer) | Enterprise Shield |
| **BioHealth Global** | `admin@biohealth.com` | `Password123!` | CMIO (Admin) | Healthcare Compliance |

*(Use the **Switch Tenant** selector in the top navbar to instantly test multi-tenant data isolation).*

---

### 5 Live Hackathon Demonstration Scenarios

#### Scenario 1: Live Physical Telemetry Ingestion
- Start the collector in `--mode live`.
- Open **Infrastructure** (`/infrastructure`) and view real CPU, Memory, and Disk metrics streaming directly from your physical machine kernel.

#### Scenario 2: Zero-Egress Privacy Verification
- Navigate to **Privacy & Egress** (`/privacy`).
- Use the **Interactive Privacy Playground** to send payloads containing passwords, bearer tokens, or social security numbers.
- Observe how the Edge Policy Gate purges every forbidden field before the payload reaches the API gateway.

#### Scenario 3: Chaos Simulation & Topological Incident Correlation
- Open the **Scenario Simulator** modal (`Ctrl + Shift + S` or click the Flask icon in the header).
- Trigger **"Database Connection Exhaustion"**.
- Navigate to **Alerts & Incidents** (`/alerts`): Notice how multiple cascading server alerts are automatically consolidated into a single correlated Incident.
- Open **Root Cause Analysis** (`/rca`): The topological graph highlights the root cause database container in red and dependent API nodes in orange.

#### Scenario 4: Offline SQLite Buffering During Network Outage
- Run the collector with `--offline` flag or simulate a network partition by shutting down the FastAPI backend (`Ctrl + C`).
- Notice the collector enters **Offline Buffer Mode** and logs transactions into `collector_buffer.db`.
- Restart the FastAPI backend: The collector automatically flushes the local buffer and synchronizes metrics without duplicates.

#### Scenario 5: Groq AI SRE Copilot & Human-Approved Remediation
- Open any active Incident and click **"AI Explain"**.
- View the structured breakdown: Confirmed Telemetry Facts, Causal Hypotheses, Blast Radius, and Remediation Runbooks.
- Click **"AI Remediation"**: Inspect the generated bash commands, complete with explicit human approval checkpoints before execution.

---

## 10. Automated Testing & Verification Suite

ObserVault features an exhaustive automated test suite achieving **100% test pass rate**:

```bash
# Run the complete test suite
python -m pytest tests/ -v
```

### Test Suite Coverage Breakdown

```
tests/test_privacy.py             PASSED  [Purges passwords, bearer tokens, API keys, client IPs; asserts extra='forbid']
tests/test_tenant_isolation.py    PASSED  [Validates cryptographic tenant separation between Acme and BioHealth]
tests/test_anomaly_detection.py   PASSED  [Validates threshold breaches, z-score statistical detection, and deduplication]
tests/test_buffering.py           PASSED  [Verifies SQLite buffer enqueue, offline survival, idempotency, and replay]
tests/test_end_to_end.py          PASSED  [Full pipeline: collection -> privacy filter -> ingestion -> RCA -> remediation]
tests/test_phase3_ai.py           PASSED  [Verifies AI Copilot, Explain, RCA, and Predictive Capacity endpoints]
tests/test_phase4_integration.py  PASSED  [Verifies collector daemon, multi-tenant persistence, and router consistency]

==================================== 97 passed in 4.82s ====================================
```

---

## 11. Security, Privacy & Compliance Matrix

| Security Standard | ObserVault Implementation |
|---|---|
| **Zero Raw Data Egress** | Strict edge sanitization ensures no customer application payloads, logs, or PII ever exit Tier 1. |
| **Strict Schema Enforcement** | FastAPI ingestion endpoints utilize Pydantic v2 `extra="forbid"`, rejecting unknown attributes at the wire level. |
| **Multi-Tenant Scoping** | All database queries, alerts, collectors, and incidents are strictly isolated using tenant IDs in JWT claims. |
| **Transport Security** | TLS 1.3 enforced for all edge-to-SaaS communications with HMAC / `X-Collector-Key` headers. |
| **Human-in-the-Loop AI** | Automated remediation suggestions require explicit operator verification and sign-off before execution. |
| **Credential Safety** | Passwords hashed using bcrypt; JWT tokens signed with HS256; zero secrets committed to Git repositories. |

---

## 12. Repository Structure

```text
observault/
├── backend/
│   ├── app/
│   │   ├── api/             # 76 REST endpoints (auth, telemetry, alerts, incidents, AI, simulator)
│   │   ├── core/            # Database sessions, settings, security & JWT utilities
│   │   ├── detection/       # Anomaly engine, z-score analysis, Isolation Forest ML models
│   │   ├── correlation/     # Incident correlation & topological root cause reasoning
│   │   ├── recommendations/ # Human-in-the-loop remediation advisor
│   │   ├── models/          # SQLAlchemy relational database models
│   │   ├── schemas/         # Strict Pydantic allow-lists (extra='forbid')
│   │   ├── main.py          # FastAPI application entrypoint & middleware
│   │   ├── seed.py          # Multi-tenant demo database seeder
│   │   └── run.py           # Uvicorn ASGI server runner
│   ├── Dockerfile           # Backend container specification
│   └── requirements.txt     # Python backend dependencies
│
├── collector/
│   ├── collectors/          # psutil live hardware & network socket metric harvesters
│   ├── privacy/             # Local Privacy Policy Gate, allow-list & credential sanitizers
│   ├── buffer/              # SQLite offline resilient spooler & transactional replay queue
│   ├── transport/           # Authenticated secure sender & heartbeat sender
│   ├── simulator/           # Scenario generator for chaos benchmarks
│   ├── config/              # Collector configuration loaders
│   ├── runtime.py           # Detached background daemon process manager
│   ├── main.py              # Collector CLI entrypoint (live, simulate, offline)
│   ├── Dockerfile           # Collector container specification
│   └── requirements.txt     # Collector Python dependencies
│
├── frontend/
│   ├── src/
│   │   ├── components/      # UI widgets (StatCard, ChartCard, PrivacyFlowGraphic, Modals)
│   │   ├── context/         # AuthContext, LayoutContext & Tenant Switcher
│   │   ├── pages/           # The 10 Enterprise SaaS dashboard pages
│   │   ├── services/        # REST API client & Axios configurations
│   │   ├── App.jsx          # React root layout & modal containment
│   │   └── main.jsx         # Vite entrypoint
│   ├── Dockerfile           # Frontend container specification
│   ├── package.json         # Node.js dependencies
│   └── tailwind.config.js   # Tailwind styling configurations
│
├── docs/
│   ├── ARCHITECTURE.md      # Detailed system architecture specification
│   ├── DEMO_GUIDE.md        # Comprehensive live demo presentation walkthrough
│   └── qa/                  # Complete Phase 3 & Phase 4 test plans, audit logs & QA reports
│
├── tests/                   # 97 Automated Pytest test suites
├── database/schema.sql      # PostgreSQL relational database schema
├── docker-compose.yml       # Production multi-container orchestration
├── install_observault_collector.ps1 # 1-click Windows edge collector installer
├── start_demo.py            # Unified automated demo orchestrator
├── .env.example             # Clean environment variable template (No secrets)
├── .gitignore               # Strict exclusion policy (.env, *.db, node_modules)
└── README.md                # Master platform documentation
```

---

## 13. License & Acknowledgments

ObserVault is released under the **MIT License**. See [LICENSE](LICENSE) for details.

Built with ❤️ for the **Smart Observability Hackathon** — empowering enterprise engineering teams to monitor mission-critical systems with uncompromising security and zero data leakage.
