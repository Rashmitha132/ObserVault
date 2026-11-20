# ObserVault Architecture Documentation

## 1. System Overview

ObserVault is an enterprise-grade, privacy-first intelligent observability platform structured around a **Two-Tier Architecture**:

```
+-----------------------------------------------------------+
|               TIER 1: LOCAL CUSTOMER ENVIRONMENT          |
|                                                           |
|   +-------------------+        +----------------------+   |
|   | Host & Network    |        | Local Privacy Engine |   |
|   | psutil Metrics    | -----> | Explicit Allow-List  |   |
|   +-------------------+        | Sanitizer / Purger   |   |
|                                +----------+-----------+   |
|                                           |               |
|                                           v               |
|   +-------------------+        +----------------------+   |
|   | Secure Sender     | <----- | Local SQLite Buffer  |   |
|   | X-Collector-Key   |        | Zero-Data-Loss Queue |   |
|   +---------+---------+        +----------------------+   |
+-------------|---------------------------------------------+
              | Authenticated TLS 1.3 Transmission
              v (ONLY Approved Metadata)
+-----------------------------------------------------------+
|               TIER 2: CENTRAL SAAS OBSERVABILITY          |
|                                                           |
|   +---------------------------------------------------+   |
|   | FastAPI Ingestion Gate & Header Authenticator     |   |
|   +-------------------------+-------------------------+   |
|                             |                             |
|       +---------------------+---------------------+       |
|       v                                           v       |
|   +-------------------+                   +-----------+   |
|   | Multi-Tenant      |                   | Anomaly   |   |
|   | Database Storage  |                   | Detection |   |
|   | PostgreSQL/SQLite |                   +-----+-----+   |
|   +-------------------+                         |         |
|                                                 v         |
|   +-------------------+                   +-----------+   |
|   | React 18 SaaS     | <---------------- | Incident  |   |
|   | Vite Dashboard    |   Alerts, Causes, | Correlator|   |
|   +-------------------+   Recommendations +-----+-----+   |
|                                                 |         |
|                                                 v         |
|                                           +-----------+   |
|                                           | Actionable|   |
|                                           | Advisor   |   |
|                                           +-----------+   |
+-----------------------------------------------------------+
```

## 2. Key Components

### Tier 1: Local On-Premises Collector Daemon
- **Metric Collection**: Leverages `psutil` for actual CPU, memory, and disk counters. Real socket round-trip timing for TCP latency.
- **Privacy Engine**: Applies `APPROVED_OUTBOUND_KEYS` allow-list. Automatically scrubs passwords, authorization tokens, API keys, client IPs, usernames, and query payloads.
- **SQLite Offline Buffer**: Local table `buffered_events` ensures zero data loss during network outages with deduplication and FIFO retry.
- **Secure Transport**: Outbound HTTPS/HTTP requests authenticated via `X-Collector-Key` header with HMAC SHA-256 validation.

### Tier 2: Central SaaS Cloud
- **Ingestion & Strict Validation**: Pydantic schema with `extra="forbid"` rejects any unapproved field. Tenant identity is resolved strictly from collector cryptographic key.
- **Anomaly Detection**: Evaluates tenant-configurable thresholds (CPU, Memory, Disk, Latency, Packet Loss, Failed Logins, Service Status). Includes deduplication to prevent alert fatigue.
- **Incident Correlator**: Groups co-occurring multi-signal symptoms within 15-minute windows into unified incidents with confidence scores and evidence summaries.
- **Intelligent Advisor**: Generates structured, human-in-the-loop recommendations. Automatic destructive actions are explicitly prohibited.
- **Multi-Tenant Dashboard**: Desktop-first React 18 interface with Recharts visualization, live privacy proof inspector, and scenario simulation controller.
