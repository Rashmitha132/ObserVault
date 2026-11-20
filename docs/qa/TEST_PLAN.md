# ObserVault — Master Quality Assurance Test Plan

**Document ID:** OV-QA-PLAN-001  
**Author:** QA Engineering Lead  
**Project:** ObserVault (Privacy-First Automated Observability Platform)  
**Target Review Deadline:** 03:00 AM  
**Test Environment:** Windows 11 Enterprise (Build 22631) / Python 3.11.9 / SQLite & PostgreSQL / FastAPI / React 18  
**Scope:** Modules 1 through 7 (Functional, Integration, Security, Performance, Regression)

---

## 1. Executive Summary & Strategy

ObserVault is an enterprise-grade observability platform designed to monitor physical and virtual infrastructure without leaking credentials, tokens, or PII outside the customer perimeter. 

Because dashboard visualizations alone do not validate observability truth, this QA test campaign enforces an **Automated-First Hybrid Testing Strategy**:
1. **Automated Verification Harness (90%):** Executes reproducible, high-throughput checks across authentication, cryptographic handshakes, single-use token lifecycle, threshold anomaly engines, mathematical regression forecasting, and multi-tenant isolation.
2. **Empirical Host Verification (10%):** Validates real live hardware counters (`psutil` CPU, RAM, Disk) from the actual physical Windows workstation (`DESKTOP-M6MNFP1`), verifying that dashboard numbers originate from live kernel APIs rather than mock generators.
3. **Defect Tracking & Retesting:** Rigorous reporting of discovered defects with immediate retest verification of developer hotfixes prior to sign-off.

---

## 2. Test Scope & Module Breakdown

| Module ID | Module Name | Scope & Objectives | Test Methodology |
|---|---|---|---|
| **MOD-01** | **Windows Device Onboarding** | Admin registration, single-use token generation, SHA-256 token hashing, enrollment handshake, device revocation, collector identity integrity. | Automated API test suite + CLI enrollment verification |
| **MOD-02** | **Continuous Heartbeat & Telemetry** | 15s heartbeat signaling, dynamic online/offline state machine (60s cutoff), real `psutil` host metrics, SQLite offline buffer queuing and deduplicated replay. | Real Windows kernel execution + network disconnection simulation |
| **MOD-03** | **Linux Compatibility** | Linux platform adapter (`psutil_kernel_telemetry`), `/etc/machine-id` GUID extraction, telemetry payload schema parity with Windows. | Automated adapter interface audit & schema diffing |
| **MOD-04** | **Predictive Analytics & Anomaly Detection** | OLS regression over 15m, 1h, 24h, 7d, 14d, 30d horizons, MAE/RMSE/MAPE out-of-sample holdout validation, capacity warnings, multi-metric anomaly alerts. | Mathematical unit testing + synthetic anomaly injection |
| **MOD-05** | **LLM Assistant & Advisory** | Root Cause Analysis (RCA) multi-signal ranking, actionable recommendations, human-approval enforcement, LLM endpoint availability & safety audit. | RCA graph evaluation & LLM safety audit |
| **MOD-06** | **Security Testing** | JWT token tampering, expired token rejection, cross-tenant isolation, metadata allow-list sanitization, Pydantic `extra='forbid'`, SQL injection prevention. | Automated penetration & exploit test harness |
| **MOD-07** | **Performance & Regression** | Telemetry ingestion burst benchmarking (50 concurrent batches), endpoint latency profiling, full 52-test pytest regression execution. | Empirical load generator + Pytest suite |

---

## 3. Entry & Exit Criteria

### Entry Criteria:
- ObserVault codebase present at repository root.
- Python 3.11+ environment with FastAPI, SQLAlchemy, Pydantic v2, and Pytest dependencies installed.
- Pre-seeded multi-tenant demo database (`observault_saas.db`) containing Acme FinTech and BioHealth Global tenants.

### Exit Criteria:
- 100% execution of automated test cases across all implemented modules.
- Zero open Critical or High severity bugs blocking core telemetry flow.
- Verified empirical proof distinguishing real kernel telemetry from simulated data.
- Full generation of required QA deliverables (`TEST_CASES.md`, `BUG_REPORTS.md`, `SECURITY_AUDIT.md`, `PERFORMANCE_REPORT.md`, `REGRESSION_REPORT.md`, `FINAL_QA_REPORT.md`).

---

## 4. Test Schedule & Execution Log

- **00:40 AM:** Kickoff of QA role assignment and test strategy formulation.
- **00:43 AM:** Full automated regression baseline execution (`pytest tests/`). Detected 1 failure in Predictive Analytics (`OverflowError`).
- **00:46 AM:** Root cause analysis and resolution of `OV-BUG-001` in `predictive_engine.py`. Re-run achieved 52/52 passing tests.
- **00:49 AM:** Development and execution of end-to-end QA verification harness (`tests/qa_verification_harness.py`).
- **00:52 AM:** Discovery and resolution of `OV-BUG-002` (`TypeError` on `failed_login_count` None in `anomaly_engine.py`).
- **00:54 AM:** Complete execution of QA verification harness across all 7 modules with empirical metrics captured.
- **01:10 AM:** Final QA documentation authoring and sign-off delivery.
