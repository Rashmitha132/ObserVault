# ObserVault — Formal QA Defect Reports

**Repository:** `c:\Users\admin\Desktop\observault`  
**QA Lead:** Quality Assurance & Testing Engineer  
**Report Date:** 2026-11-21  

---

## Defect Summary Tracker

| Defect ID | Module | Severity | Summary | Status | Resolution |
|---|---|---|---|---|---|
| **OV-BUG-001** | Predictive Analytics | High | `OverflowError` in `linear_trend_forecast` when metric slope approaches zero | **Closed (Verified)** | Added 10-year planning cap (`3650.0` days) preventing astronomical `timedelta` |
| **OV-BUG-002** | Anomaly Detection | High | `TypeError` in `run_anomaly_detection` when `failed_login_count` is `None` | **Closed (Verified)** | Null-coalesced `record.failed_login_count` to `0` defensively |
| **OV-BUG-003** | Windows Collector Installer | High | PowerShell installer completes enrollment but fails to start background daemon | **Open** | Installer script must invoke `python collector/runtime.py start` upon success |
| **OV-BUG-004** | Dashboard API | Low | Endpoint `/api/v1/dashboard/summary` returns 404 Not Found | **Closed (Verified)** | Added `@router.get("/summary")` and `@router.get("")` alias decorators to `dashboard.py`. Returns HTTP 200. |
| **OV-BUG-005** | Onboarding Wizard | Medium | Copy command lacks project directory `cd`, causing `ModuleNotFoundError: No module named 'collector'` when run from home directory | **Open** | Include `cd C:\Users\admin\Desktop\observault` in generated PowerShell command |

---

### Defect Report: OV-BUG-001

**Bug ID:** OV-BUG-001  
**Module:** Module 4 – Predictive Analytics & Capacity Forecasting  
**Feature:** Linear Trend Capacity Forecasting  
**Severity:** High  

**Test Environment:**
- OS: Windows 11 Enterprise (Build 22631)
- Python Version: 3.11.9
- ObserVault Version: 1.0.0
- Test Date: 2026-11-21

**Steps to Reproduce:**
1. Populate historical telemetry records for a server with stable disk metrics (slope ~ `0.00000001`% per day).
2. Execute capacity warning evaluation via `PredictiveEngine.evaluate_active_capacity_warnings(db, tenant_id)` or call REST endpoint `GET /api/v2/predictive/capacity-warnings`.
3. Observe backend exception trace during `linear_trend_forecast`.

**Expected Result:**  
Servers with flat or stable utilization should reflect infinite/indefinite runway without raising exceptions, setting `projected_breach_date = None`.

**Actual Result:**  
System crashed with `OverflowError: Python int too large to convert to C int` at line 229:
```text
backend\app\detection\predictive_engine.py:229: in linear_trend_forecast
    breach_dt = utc_now() + timedelta(days=days_to_threshold)
E   OverflowError: Python int too large to convert to C int
```

**Developer Notes / Root Cause:**  
When `slope_per_day` is positive but minuscule, `needed_increase / slope_per_day` computes billions of days, which overflows Python's C-level `timedelta` representation.

**Fix Applied:**
```python
if slope_per_day > 0 and current_y < threshold_value:
    needed_increase = threshold_value - current_y
    raw_days = needed_increase / slope_per_day
    if raw_days > 3650.0:  # Runway > 10 years considered stable
        days_to_threshold = None
        projected_breach_date = None
    else:
        days_to_threshold = round(raw_days, 1)
        breach_dt = utc_now() + timedelta(days=days_to_threshold)
        projected_breach_date = breach_dt.isoformat()
```

**Retest Result:**  
**VERIFIED PASSED**. Re-ran `tests/test_predictive_analytics.py::test_predictive_and_integrations_api_endpoints` and QA verification harness. 63 capacity warnings evaluated smoothly with zero errors.

---

### Defect Report: OV-BUG-002

**Bug ID:** OV-BUG-002  
**Module:** Module 4 – Anomaly Detection  
**Feature:** Multi-Signal Threshold Anomaly Engine  
**Severity:** High  

**Test Environment:**
- OS: Windows 11 Enterprise
- Python Version: 3.11.9
- Test Date: 2026-11-21

**Steps to Reproduce:**
1. Ingest or construct a `TelemetryRecord` where `failed_login_count` is not explicitly set (defaults to `None` in SQL ORM).
2. Invoke `run_anomaly_detection(db, record, tenant, server)`.
3. Observe exception during threshold evaluation.

**Expected Result:**  
Missing counter values should be safely treated as zero failed logins, generating no false alert.

**Actual Result:**  
Engine crashes with unhandled exception:
```text
File "backend/app/detection/anomaly_engine.py", line 108, in run_anomaly_detection
    if record.failed_login_count >= tenant.failed_login_threshold:
TypeError: '>=' not supported between instances of 'NoneType' and 'int'
```

**Developer Notes / Root Cause:**  
Missing null-safety guard when evaluating integer counter fields against tenant policy thresholds.

**Fix Applied:**
```python
fl_count = record.failed_login_count if record.failed_login_count is not None else 0
fl_thresh = tenant.failed_login_threshold if getattr(tenant, "failed_login_threshold", None) is not None else 3
if fl_count >= fl_thresh:
...
```

**Retest Result:**  
**VERIFIED PASSED**. Anomaly engine successfully evaluates records with null counters without exceptions.

---

### Defect Report: OV-BUG-003

**Bug ID:** OV-BUG-003  
**Module:** Module 1 & 2 – Windows Collector Installer  
**Feature:** Automatic Background Daemon Provisioning  
**Severity:** High  

**Test Environment:**
- OS: Windows 11 Enterprise
- PowerShell Version: 5.1 / 7.x
- Test Date: 2026-11-21

**Steps to Reproduce:**
1. Open PowerShell and run the one-line onboarding command:
   ```powershell
   & .\install_observault_collector.ps1 -EnrollmentToken "ov_enroll_..."
   ```
2. Observe successful enrollment message printed to console:
   `">>> SUCCESS: Windows Collector successfully enrolled! View live status in ObserVault dashboard."`
3. Observe that PowerShell prompt immediately exits and returns to user.
4. Wait 60 seconds without running any manual python command.
5. Query `GET /api/v1/collectors` or observe Collector Health in React UI.

**Expected Result:**  
The installer should either start the continuous collector daemon in the background (`python collector/runtime.py start`) or register a Windows Scheduled Task, keeping the collector continuously transmitting heartbeats every 15 seconds. The dashboard status should remain **Online**.

**Actual Result:**  
The installer exits after saving `collector_config.json`. No continuous process is launched. After the 60-second heartbeat timeout elapses (`HEARTBEAT_TIMEOUT_SECONDS = 60`), the backend dynamically changes the collector status to **Offline**.

**Developer Notes / Recommended Resolution:**  
Append daemon execution to the final step of `install_observault_collector.ps1`:
```powershell
Write-Host "[*] Launching ObserVault continuous collector daemon..." -ForegroundColor Yellow
Start-Process python -ArgumentList "collector\runtime.py start" -WorkingDirectory $PSScriptRoot -WindowStyle Hidden
```

**Status:** Open / Recommended Fix Submitted.

---

### Defect Report: OV-BUG-004

**Bug ID:** OV-BUG-004  
**Module:** Frontend / Dashboard API  
**Feature:** Overview Page Telemetry Aggregates  
**Severity:** Low  

**Test Environment:**
- Backend API Router: `backend/app/api/dashboard.py`

**Steps to Reproduce:**
1. Send authenticated GET request to `/api/v1/dashboard/summary`.
2. Observe HTTP 404 response.

**Expected Result:**  
Returns high-level summary KPIs (Active Servers, Open Alerts, Incidents, Privacy Purged Records).

**Actual Result:**  
HTTP 404 Not Found because the FastAPI router mounts the endpoint at `/api/v1/dashboard` (the root prefix), not `/summary`.

**Fix Applied:**
Added `@router.get("/summary")` and `@router.get("")` alias route decorators in `backend/app/api/dashboard.py`:
```python
@router.get("/overview")
@router.get("/summary")
@router.get("")
def get_dashboard_overview(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
```

**Retest Result:**  
**VERIFIED PASSED**. Re-ran test harness against `GET /api/v1/dashboard/summary`. Successfully returned HTTP 200 with complete tenant summary payload in `122.03ms`.

**Status:** Closed (Verified)

---

### Defect Report: OV-BUG-005

**Bug ID:** OV-BUG-005  
**Module:** Module 1 – Windows Device Onboarding  
**Feature:** Copyable PowerShell Enrollment Command  
**Severity:** Medium  

**Test Environment:**
- OS: Windows 11 Enterprise
- Terminal: Windows PowerShell 5.1 (`PS C:\Users\admin>`)
- Test Date: 2026-11-21

**Steps to Reproduce:**
1. In the Web UI, click `+ Add New Device`, enter `BioHealth-Win11-Node`, and generate an enrollment token.
2. Click the Copy button on Step 2 to copy the PowerShell command.
3. Open a default Windows PowerShell prompt (which defaults to `C:\Users\admin>`).
4. Paste and execute the copied command:
   ```powershell
   $env:OBSERVAULT_ENROLL_TOKEN='ov_enroll_...'; $env:OBSERVAULT_BACKEND_URL='http://127.0.0.1:8000'; python -m collector.enroll
   ```

**Expected Result:**  
The enrollment script executes successfully regardless of the initial shell directory.

**Actual Result:**  
Python raises:
```text
Error while finding module specification for 'collector.enroll' (ModuleNotFoundError: No module named 'collector')
```

**Developer Notes / Root Cause:**  
The `collector` module is located in `c:\Users\admin\Desktop\observault\collector`. When run from `C:\Users\admin`, Python's `sys.path` does not include the project folder.

**Fix Applied / Recommendation:**  
Prefix the generated PowerShell command with directory navigation:
```powershell
cd "c:\Users\admin\Desktop\observault"; $env:OBSERVAULT_ENROLL_TOKEN='...'; ...
```

