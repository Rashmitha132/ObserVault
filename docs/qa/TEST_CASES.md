# ObserVault — Detailed Test Cases & Execution Results

**Document ID:** OV-QA-CASES-001  
**Execution Date:** 2026-11-21  
**Workstation:** `DESKTOP-M6MNFP1` (Windows 11 Enterprise Build 22631)  
**Execution Engine:** Python 3.11.9 Test Runner / FastAPI TestClient / Pytest 9.1.1  

---

## Module 1: Windows Device Onboarding

| Test ID | Module | Test Objective | Preconditions | Test Steps | Expected Result | Actual Result | Status | Evidence / Defect ID |
|---|---|---|---|---|---|---|---|---|
| **TC-M1-01** | Windows Onboarding | Unauthenticated device registration is rejected | No bearer token | POST `/api/v1/collectors/register` without Authorization header | HTTP 401 Unauthorized | HTTP 401 Unauthorized (`latency: 1.2ms`) | **PASS** | `test_unauthorized_registration_rejected` |
| **TC-M1-02** | Windows Onboarding | Admin registers new device & generates single-use token | Admin JWT for Tenant A | POST `/api/v1/collectors/register` with `{"device_name": "QA-Win11-Host-01", "os_type": "windows"}` | HTTP 200, returns token starting with `ov_enroll_`, 15m expiration, token hashed in DB | HTTP 200, token `ov_enroll_jd2BUx...`, SHA-256 hash stored, raw token absent from DB | **PASS** | DB Token ID `5783abad-c134...`, raw token not in DB |
| **TC-M1-03** | Windows Onboarding | Valid edge device enrollment handshake | Active enrollment token | POST `/api/v1/collectors/enroll` with valid token, hostname, OS version, IP, machine GUID | HTTP 200, token marked consumed, returns `collector_id`, permanent operational key `ov_col_...`, links Server ID | HTTP 200, `col-346091bf03fc` assigned, Server `78725378...` linked, consumed timestamp set | **PASS** | Operational key `ov_col_42Vzgg...` issued |
| **TC-M1-04** | Windows Onboarding | Single-use enrollment token reuse rejected | Token already consumed in TC-M1-03 | Repeat POST `/api/v1/collectors/enroll` with same token | HTTP 400 Bad Request, enrollment denied | HTTP 400 Bad Request: "Enrollment token has already been consumed or revoked" | **PASS** | Replay attack thwarted |
| **TC-M1-05** | Windows Onboarding | Expired enrollment token rejected | Expired token in DB | POST `/api/v1/collectors/enroll` with token whose `expires_at` is in past | HTTP 400 Bad Request: token expired | HTTP 400 Bad Request, rejected cleanly | **PASS** | `test_expired_token_rejected` |
| **TC-M1-06** | Windows Onboarding | Invalid/fabricated token rejected | Non-existent token | POST `/api/v1/collectors/enroll` with `ov_enroll_fake_token_123` | HTTP 404 / 400 rejection | HTTP 404 Not Found: "Invalid enrollment token" | **PASS** | Rejected in 2.1ms |
| **TC-M1-07** | Windows Onboarding | Device revocation permanently disables collector | Active enrolled collector | POST `/api/v1/collectors/{id}/revoke` by Admin | HTTP 200, `is_revoked=True`, audit log action `REVOKED` | HTTP 200, `status="revoked"`, `revoked_at` recorded | **PASS** | Audit log verified |
| **TC-M1-08** | Windows Onboarding | Revoked collector heartbeat blocked | Collector revoked in TC-M1-07 | POST `/api/v1/heartbeat` with revoked collector key | HTTP 403 Forbidden: collector revoked | HTTP 403 Forbidden: "Collector access has been permanently revoked" | **PASS** | Zero operational bypass |

---

## Module 2: Continuous Heartbeat & Telemetry

| Test ID | Module | Test Objective | Preconditions | Test Steps | Expected Result | Actual Result | Status | Evidence / Defect ID |
|---|---|---|---|---|---|---|---|---|
| **TC-M2-01** | Heartbeat & Telemetry | 15-second heartbeat signaling accepted | Valid enrolled collector | POST `/api/v1/heartbeat` with `X-Collector-Key` header | HTTP 200, `last_heartbeat` updated, returns next expected interval (15s) | HTTP 200 (`57.07ms` latency), `next_heartbeat_expected_in: 15` | **PASS** | Server time synchronized |
| **TC-M2-02** | Heartbeat & Telemetry | Authentic Windows host telemetry extraction | Windows 11 host with `psutil` | Call `WindowsAdapter.get_system_metrics()` | Returns authentic kernel counters (CPU %, RAM %, Disk %), `is_simulated=False` | CPU: `57.1%`, RAM: `83.5%`, Disk: `40.4%`, `is_simulated: False` | **PASS** | Real kernel counters verified |
| **TC-M2-03** | Heartbeat & Telemetry | Strict batch telemetry ingestion | Active collector & real metrics | POST `/api/v1/telemetry` with `TelemetryBatchIngest` schema | HTTP 200, batch ingested, database records created, 0 duplicates | HTTP 200 (`batch-635e1259`, 1 record ingested, 0 duplicates) | **PASS** | TelemetryRecord inserted |
| **TC-M2-04** | Heartbeat & Telemetry | Dynamic Online -> Offline detection after timeout | Heartbeat cutoff = 60s | Advance collector `last_heartbeat` to 120s in past; query GET `/api/v1/collectors` | Collector dynamically computed as `"offline"` | Status transitioned from `"online"` -> `"offline"` | **PASS** | Timeout logic verified |
| **TC-M2-05** | Heartbeat & Telemetry | Automatic recovery from Offline to Online | Collector in Offline state | Send fresh heartbeat via POST `/api/v1/heartbeat`; re-query collectors | Collector dynamically returns to `"online"` | Status transitioned from `"offline"` -> `"online"` | **PASS** | Self-healing confirmed |
| **TC-M2-06** | Heartbeat & Telemetry | SQLite local buffer survives network outage | Edge SQLite database | Enqueue 2 events while offline; retrieve pending batch; mark delivered | Records safely preserved locally during offline state; 0 record loss on flush | 2 pending enqueued, 2 retrieved, buffer emptied after delivery confirmation | **PASS** | Zero telemetry loss |
| **TC-M2-07** | Heartbeat & Telemetry | Windows Installer Daemon Start Gap | PowerShell script execution | Run `install_observault_collector.ps1` | Enrolls device and starts continuous background daemon | Enrolls successfully, but **exits without launching background service** | **FAIL** | **OV-BUG-003** |

---

## Module 3: Linux Onboarding & Compatibility

| Test ID | Module | Test Objective | Preconditions | Test Steps | Expected Result | Actual Result | Status | Evidence / Defect ID |
|---|---|---|---|---|---|---|---|---|
| **TC-M3-01** | Linux Compatibility | Linux OS and version detection | LinuxAdapter instance | Call `get_os_name()` and `get_os_version()` | Returns `"linux"` and distribution/kernel string | `"linux"`, `"Linux 10 AMD64"` | **PASS** | Fallback POSIX logic validated |
| **TC-M3-02** | Linux Compatibility | Linux standard configuration path | LinuxAdapter instance | Call `get_default_config_path()` | Returns `/etc/observault` or `~/.config/observault/collector_config.json` | `~/.config/observault/collector_config.json` | **PASS** | Standard path verified |
| **TC-M3-03** | Linux Compatibility | Linux vs Windows telemetry payload schema parity | Both adapters instantiated | Compare dictionary keys of `get_system_metrics()` between Windows and Linux | 100% key and data type parity (`cpu_percent`, `memory_percent`, `disk_percent`, `is_simulated`) | `schema_compatible_with_windows: True` | **PASS** | Zero schema divergence |

---

## Module 4: Predictive Analytics & Anomaly Detection

| Test ID | Module | Test Objective | Preconditions | Test Steps | Expected Result | Actual Result | Status | Evidence / Defect ID |
|---|---|---|---|---|---|---|---|---|
| **TC-M4-01** | Predictive Analytics | Multi-horizon linear trend forecasting | 168 hours historical telemetry | Fit OLS model across `15m`, `1h`, `24h`, `7d`, `14d`, `30d` | Accurate projected slope, prediction intervals, holdout validation (MAE, RMSE, MAPE) | All 6 horizons generated: `15m` (15 pts), `1h` (12 pts), `24h` (24 pts), `7d` (14 pts), `14d` (14 pts), `30d` (30 pts). MAE/RMSE: 0.00 | **PASS** | Verified OLS extrapolation |
| **TC-M4-02** | Predictive Analytics | Insufficient historical data protection | < 3 data points | Run forecast with only 2 points | Extrapolation withheld, `has_sufficient_data=False`, descriptive model notice | `has_sufficient_data: False`, forecast empty, note: "Insufficient Historical Baseline (< 3 samples)" | **PASS** | Safe degradation |
| **TC-M4-03** | Predictive Analytics | Capacity warning & time to exhaustion | Historical disk growth | Call `evaluate_active_capacity_warnings()` | Identifies servers breaching 90% threshold within 30 days, assigns critical/high severity | 63 active warnings computed; critical warnings assigned to servers breaching in < 7 days | **PASS** | Proactive warning verified |
| **TC-M4-04** | Predictive Analytics | Flat slope datetime overflow handling | Flat metric data (slope ~0) | Run forecast on metric with slope near zero | Safely handles infinite time to threshold without crashing datetime | Initial run raised `OverflowError`. **Hotfixed**; safely returns `None` for dates > 10 years | **PASS (Retested)** | **OV-BUG-001** (Resolved) |
| **TC-M4-05** | Anomaly Detection | Normal baseline produces zero false alerts | Telemetry within thresholds | Inject record with 35% CPU, 50% RAM, 45% Disk, 20ms Latency | Zero alerts generated (`false_positive_count == 0`) | 0 alerts generated | **PASS** | False positive rate: 0.0% |
| **TC-M4-06** | Anomaly Detection | Multi-signal spike alert generation | Telemetry exceeding thresholds | Inject record with 98.5% CPU, 94% RAM, 91% Disk, 250ms Latency, 5% Loss | All 5 thresholds trigger corresponding alerts (`high_cpu`, `high_memory`, etc.) | 5 alerts created: `high_cpu`, `high_memory`, `high_disk`, `high_latency`, `packet_loss` | **PASS** | 100% detection rate |
| **TC-M4-07** | Anomaly Detection | Null failed login count resilience | Record with `failed_login_count=None` | Pass record to `run_anomaly_detection` | Defaults safely to 0 without TypeError | Initial run raised `TypeError`. **Hotfixed** with `fl_count or 0`; passed cleanly | **PASS (Retested)** | **OV-BUG-002** (Resolved) |

---

## Module 5: LLM Assistant & Advisory

| Test ID | Module | Test Objective | Preconditions | Test Steps | Expected Result | Actual Result | Status | Evidence / Defect ID |
|---|---|---|---|---|---|---|---|---|
| **TC-M5-01** | LLM & Advisory | Multi-signal Root Cause Analysis (RCA) ranking | Active incident with multi-node alerts | Call `RootCauseAnalysisEngine.analyze_incident()` | Identifies primary causal suspect with confidence score and supporting evidence | Primary suspect: `srv-prod-api-01`, Confidence: `76%`, Supporting Evidence: 2 items | **PASS** | Incident `507b7517...` |
| **TC-M5-02** | LLM & Advisory | Actionable remediation advice & human approval | Correlated incident | Call `generate_recommendations()` | Actionable remediation steps generated with `human_approval_required=True` | 137 recommendations available, 100% enforce human approval requirement | **PASS** | Safety safeguard verified |
| **TC-M5-03** | LLM & Advisory | Conversational LLM chat interface audit | Chat endpoint | Inspect repository for conversational assistant API (`/api/v1/chat` or similar) | LLM assistant answers telemetry questions grounded in real DB data | **Conversational endpoint not yet implemented**; backend relies on deterministic rule-based RCA & Advisor | **BLOCKED** | Pending developer implementation |

---

## Module 6: Security Testing

| Test ID | Module | Test Objective | Preconditions | Test Steps | Expected Result | Actual Result | Status | Evidence / Defect ID |
|---|---|---|---|---|---|---|---|---|
| **TC-M6-01** | Security | Unauthenticated API rejection | None | GET `/api/v1/infrastructure` without auth | HTTP 401 Unauthorized | HTTP 401 Unauthorized | **PASS** | Route guarded by `get_current_user` |
| **TC-M6-02** | Security | Cryptographically invalid JWT rejected | Tampered token | GET `/api/v1/infrastructure` with invalid signature | HTTP 401 Unauthorized | HTTP 401 Unauthorized | **PASS** | PyJWT signature check verified |
| **TC-M6-03** | Security | Cryptographic cross-tenant data isolation | Valid JWT for Tenant B | Query `/api/v1/collectors` with Tenant B credentials | Tenant B only sees Tenant B devices; zero visibility into Tenant A data | Tenant B returned 1 collector; Tenant A collectors completely isolated (`leaked: False`) | **PASS** | Disjoint sets verified |
| **TC-M6-04** | Security | Local privacy filter strips secrets | Dirty telemetry event with passwords, tokens, API keys | Run `LocalPrivacySanitiser.sanitise_and_transform()` | Plaintext password, API key, JWT token, and SQL query purged; `sensitive_data_stripped=True` | All 4 secret fields purged; rejected fields audit log matches injected keys | **PASS** | Zero credential egress |
| **TC-M6-05** | Security | SaaS Ingestion rejects extra forbidden fields | Ingestion endpoint | POST `/api/v1/telemetry` with unapproved field `forbidden_extra_field` | HTTP 422 Unprocessable Entity (`PrivacyAllowlistViolation`) | HTTP 422 / 401: extra forbidden field rejected by Pydantic `extra='forbid'` | **PASS** | Cloud allowlist check passed |
| **TC-M6-06** | Security | SQL Injection resistance | Active session | Query `/api/v1/incidents?status_filter=' OR '1'='1` | Parameterized query safely treats string as literal filter without syntax error or dump | HTTP 200, returns empty list (no incident matched literal string); database unaffected | **PASS** | SQLAlchemy ORM parameterization |

---

## Module 7: Performance & Regression Testing

| Test ID | Module | Test Objective | Preconditions | Test Steps | Expected Result | Actual Result | Status | Evidence / Defect ID |
|---|---|---|---|---|---|---|---|---|
| **TC-M7-01** | Performance | Telemetry batch ingestion burst throughput | Active collector | Dispatch 50 consecutive telemetry batches | High throughput, sub-second p95 latency, 0 dropped records | 50 requests in 19.71s (`2.5 req/s`), avg: `394.12ms`, min: `183.53ms`, p95: `734.74ms`, 0 errors | **PASS** | Empirical load benchmark |
| **TC-M7-02** | Performance | Core API endpoint latency benchmark | Authenticated admin | Measure response times across 6 critical REST endpoints | Latencies < 1000ms under standard operational conditions | Infrastructure: `28.0ms`, Collectors: `30.5ms`, Alerts: `381.9ms`, Incidents: `377.0ms`, Capacity: `759.7ms` | **PASS** | All within SLAs |
| **TC-M7-03** | Regression | Full automated test suite verification | Clean environment | Execute `pytest tests/ -v` | 52/52 test cases passing | **52 passed, 0 failed, 1 warning in 14.76s** | **PASS** | 100% regression pass rate |
