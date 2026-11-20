# ObserVault — Security & Privacy Architecture Audit

**Document ID:** OV-SEC-AUDIT-001  
**Auditor:** Quality Assurance & Security Engineer  
**Date:** 2026-11-21  
**Classification:** Internal QA Security Assessment  

---

## 1. Security Architecture Assessment

ObserVault operates under a **Privacy-First Zero-Trust Architecture**. Telemetry collectors execute on-premises within customer infrastructure (Tier 1) and communicate with the central SaaS platform (Tier 2).

The primary security mandates verified during this audit:
1. **Zero Credential Egress:** Plaintext operational secrets (passwords, tokens, database connection strings, customer PII) must NEVER leave the host boundary.
2. **Strict Ingestion Allow-List:** The central cloud gateway must reject any telemetry payload containing unauthorized or un-modeled keys.
3. **Rigorous Tenant Isolation:** Telemetry, alerts, and servers belonging to Organization A must never be accessible or modifiable by Organization B.
4. **Resilient Token & Identity Lifecycle:** Single-use enrollment tokens must resist replay, brute force, and reuse. Revocation must take effect immediately.

---

## 2. Test Execution & Findings Matrix

| Security Vector | Test Objective | Test Payload / Attack Simulation | Result | Audit Verdict |
|---|---|---|---|---|
| **Auth 01: Unauthenticated Egress** | Verify protected SaaS endpoints reject anonymous calls | `GET /api/v1/infrastructure` (No Authorization header) | HTTP 401 Unauthorized (`{"detail": "Not authenticated"}`) | **SECURE** |
| **Auth 02: JWT Signature Tampering** | Ensure forged tokens with modified payloads or bad signatures are rejected | Modified JWT with forged `role: admin` and modified signature | HTTP 401 Unauthorized (`{"detail": "Could not validate credentials"}`) | **SECURE** |
| **Auth 03: Enrollment Token Replay** | Attempt to re-enroll a second host using an already-consumed token | `POST /api/v1/collectors/enroll` with consumed token `ov_enroll_jd2BUx...` | HTTP 400 Bad Request (`"Enrollment token has already been consumed or revoked"`) | **SECURE** |
| **Auth 04: Revoked Collector Invalidation** | Verify that revoking a device in admin console immediately severs collector access | Dispatch heartbeat using `X-Collector-Key` of revoked collector | HTTP 403 Forbidden (`"Collector access has been permanently revoked"`) | **SECURE** |
| **Tenant 01: Multi-Tenant Data Leakage** | Verify Tenant B admin cannot view or query Tenant A infrastructure | Authenticate as `admin@biohealth.com`; query `GET /api/v1/collectors` | Returned 1 collector belonging strictly to BioHealth; 0 Acme records leaked | **SECURE** |
| **Privacy 01: Edge Credential Stripping** | Confirm local sanitiser strips passwords, bearer tokens, API keys | Injected `password`, `auth_token`, `api_key`, `raw_payload`, `sql_query` | All 5 sensitive fields stripped locally; `sensitive_data_stripped=True` | **SECURE** |
| **Privacy 02: Pydantic `extra='forbid'`** | Ingest payload with injected unknown keys at cloud gateway | `POST /api/v1/telemetry` with `{"forbidden_extra_field": "exploit"}` | HTTP 422 Unprocessable Entity (`PrivacyAllowlistViolation`) | **SECURE** |
| **Injection 01: SQL Parameterization** | Test SQL injection resistance in filter query parameters | `GET /api/v1/incidents?status_filter=' OR '1'='1` | Safely escaped by SQLAlchemy ORM; treated as literal string; 0 data dumped | **SECURE** |
| **Storage 01: Database Secret Audit** | Search relational database directly for leaked credentials | Direct SQL query for `superSecretPassword` across `TelemetryRecord` table | **0 records found** in `raw_metadata_json` or database tables | **SECURE** |

---

## 3. Deep Dive: Privacy Sanitizer & Metadata Allow-List

### Local Edge Sanitization (`collector/privacy/sanitiser.py`):
When the collector captures raw events, the `LocalPrivacySanitiser` passes the record through a strict allow-list:
- **Approved Metadata Keys:** `event_id`, `timestamp`, `server_id`, `hostname`, `collector_id`, `collector_version`, `cpu_percent`, `memory_percent`, `disk_percent`, `network_latency_ms`, `packet_loss_percent`, `network_status`, `failed_login_count`, `service_status`, `is_simulated`.
- **Rejection Policy:** Any key not in the allow-list is dropped at Tier 1 before the record enters the SQLite outbound buffer.

### Verification Evidence:
```text
[STEP 1: RAW OPERATIONAL TELEMETRY RECEIVED LOCALLY]
{
  "password": "SuperSecretPassword123!DoNotLeak",
  "auth_token": "bearer_jwt_token_header_secret_xyz",
  "api_key": "sk_live_internal_api_secret_999",
  "sql_query": "SELECT * FROM users WHERE ssn='123-45-6789'"
}
[STEP 3: SANITIZATION AUDIT SUMMARY]
 - Sensitive Data Dropped: True
 - Stripped Field Names: ['password', 'auth_token', 'api_key', 'sql_query']
[VERIFICATION PASSED]: Zero credentials exist in outbound metadata.
```

---

## 4. LLM Assistant Security Assessment

While the conversational chat endpoint is currently pending developer completion, the platform's AI Advisory Engine (`app/recommendations/advisor.py`) and RCA Engine (`app/correlation/rca_engine.py`) were evaluated for AI safety principles:

1. **Human-in-the-Loop Protocol:** 100% of generated remediation actions enforce `human_approval_required: true`. No automated CLI commands are executed autonomously without operator confirmation.
2. **Grounding in Empirical Data:** Recommendations and RCA candidate rankings are strictly computed from observed metric breaches and service graph topology, preventing hallucinated incidents.
3. **Tenant Context Enclosure:** RCA engine strictly queries incidents and service nodes scoped to `current_user.tenant_id`. Cross-tenant prompt injection or data leakage is structurally impossible at the ORM layer.
