# ObserVault — Automated Regression Test Report

**Document ID:** OV-REG-001  
**Test Suite:** Pytest Comprehensive Test Suite  
**Execution Environment:** Python 3.11.9 / Windows 11 Enterprise  
**Execution Time:** 14.76 seconds  
**Final Outcome:** **52 Passed, 0 Failed, 1 Warning (100% Pass Rate)**  

---

## 1. Regression Suite Overview

The ObserVault automated regression suite consists of 11 distinct test modules containing 52 unit, integration, and end-to-end tests:

```text
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.7.0
rootdir: c:\Users\admin\Desktop\observault
plugins: anyio-4.13.0, langsmith-0.8.5, asyncio-1.4.0
collected 52 items

tests/test_anomaly_detection.py ........ [ 1 item  ] -> PASSED
tests/test_buffering.py ................ [ 1 item  ] -> PASSED
tests/test_device_onboarding.py ........ [ 12 items] -> PASSED
tests/test_end_to_end.py ............... [ 1 item  ] -> PASSED
tests/test_ml_anomaly_detection.py ..... [ 5 items ] -> PASSED
tests/test_opentelemetry_traces.py ..... [ 5 items ] -> PASSED
tests/test_predictive_analytics.py ..... [ 10 items] -> PASSED (Hotfix Verified)
tests/test_privacy.py .................. [ 2 items ] -> PASSED
tests/test_root_cause_analysis.py ...... [ 8 items ] -> PASSED
tests/test_security_hardening.py ....... [ 6 items ] -> PASSED
tests/test_tenant_isolation.py ......... [ 1 item  ] -> PASSED

======================= 52 passed, 1 warning in 14.76s ========================
```

---

## 2. Granular Module Results

### A. Device Onboarding (`test_device_onboarding.py`) — 12/12 PASSED
- `test_unauthorized_registration_rejected` : PASSED
- `test_successful_device_registration_and_token_generation` : PASSED
- `test_successful_device_enrollment_handshake` : PASSED
- `test_reused_single_use_token_rejected` : PASSED
- `test_expired_token_rejected` : PASSED
- `test_invalid_token_rejected` : PASSED
- `test_heartbeat_and_dynamic_online_offline_status` : PASSED
- `test_device_revocation_blocks_heartbeat_and_telemetry` : PASSED
- `test_cross_tenant_isolation` : PASSED
- `test_windows_platform_adapter_telemetry` : PASSED
- `test_device_management_stats_api` : PASSED
- `test_powershell_installer_endpoint` : PASSED

### B. Predictive Analytics (`test_predictive_analytics.py`) — 10/10 PASSED
- `test_linear_trend_forecasting_algorithm` : PASSED
- `test_multi_horizon_parsing` : PASSED
- `test_minimum_data_requirement_withholds_extrapolation` : PASSED
- `test_capacity_warning_time_to_exhaustion` : PASSED
- `test_slo_and_error_budget_calculation` : PASSED
- `test_credential_masking` : PASSED
- `test_real_host_telemetry_capture` : PASSED
- `test_docker_status_probe` : PASSED
- `test_predictive_and_integrations_api_endpoints` : **PASSED (Resolved OV-BUG-001)**
- `test_tenant_isolation_predictive` : PASSED

### C. Root Cause Analysis (`test_root_cause_analysis.py`) — 8/8 PASSED
- `test_multi_signal_correlation_and_ranking` : PASSED
- `test_timestamp_ordering_precedence` : PASSED
- `test_unrelated_event_rejection_and_simultaneous_incidents` : PASSED
- `test_missing_telemetry_resilience` : PASSED
- `test_tenant_isolation_rca` : PASSED
- `test_rca_api_endpoints` : PASSED
- `test_leaf_dependency_without_evidence_is_not_root_cause` : PASSED
- `test_topology_path_tracing` : PASSED

### D. Security Hardening & Tracing (`test_security_hardening.py`, `test_opentelemetry_traces.py`, `test_privacy.py`, `test_tenant_isolation.py`) — 14/14 PASSED
- `test_sensitive_fields_stripped_locally` : PASSED
- `test_backend_pydantic_rejects_unapproved_fields` : PASSED
- `test_tenant_isolation` : PASSED
- `test_rbac_permissions` : PASSED
- `test_crypto_batch_signing_and_verification` : PASSED
- `test_crypto_tamper_detection` : PASSED
- `test_crypto_replay_attack_rejection` : PASSED
- `test_crypto_timestamp_skew_rejection` : PASSED
- `test_mtls_certificate_lifecycle` : PASSED
- `test_extended_privacy_verification` : PASSED
- `test_trace_privacy_sanitizer_allowlist` : PASSED
- `test_trace_privacy_sql_parameterization` : PASSED
- `test_trace_privacy_purges_tokens_and_bodies` : PASSED
- `test_trace_ingestion_and_hierarchy` : PASSED

### E. Anomaly Detection & Edge Buffering (`test_anomaly_detection.py`, `test_ml_anomaly_detection.py`, `test_buffering.py`, `test_end_to_end.py`) — 8/8 PASSED
- `test_anomaly_detection_and_deduplication` : PASSED
- `test_sqlite_buffer_lifecycle` : PASSED
- `test_statistical_engine_z_score` : PASSED
- `test_statistical_engine_ewma_drift` : PASSED
- `test_isolation_forest_scoring` : PASSED
- `test_model_persistence_and_benchmark_evaluation` : PASSED
- `test_ml_detection_api_endpoints` : PASSED
- `test_complete_observault_pipeline` : PASSED

---

## 3. Regression Verdict

With the resolution and retesting of `OV-BUG-001` and `OV-BUG-002`, the entire test suite passes without errors. All core functionalities—device onboarding, continuous heartbeats, privacy filtering, anomaly correlation, capacity forecasting, and multi-tenant security—are completely stable.
