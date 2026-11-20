# ObserVault – Complete Device Onboarding & Edge Collector Guide (Phase 2F)

## 1. Overview & Architecture

ObserVault Phase 2F introduces **Complete Device & Edge Collector Onboarding**, enabling organization administrators to securely register physical or virtual machines, enroll local collectors via cryptographic single-use tokens, and stream authentic OS kernel telemetry (`psutil`) into the ObserVault SaaS platform with zero credential leakage.

```
+-----------------------------------------------------------------------------------+
|                            ORGANIZATION ADMINISTRATOR                             |
|                                                                                   |
|  1. Accesses ObserVault Web Console (/collectors)                                 |
|  2. Fills "Add New Device" Wizard (Device Name, OS: Windows, Environment: Prod)   |
|  3. SaaS Backend generates cryptographically secure, single-use token:           |
|     `ov_enroll_********************************` (Expires in 15 minutes)          |
+----------------------------------------+------------------------------------------+
                                         |
                                         | Displays copyable PowerShell command
                                         v
+-----------------------------------------------------------------------------------+
|                            TARGET WINDOWS HOST MACHINE                            |
|                                                                                   |
|  4. Administrator / DevOps engineer executes PowerShell onboarding command:       |
|     `$env:OBSERVAULT_ENROLL_TOKEN='ov_enroll_...'; python -m collector.enroll`    |
|                                                                                   |
|  5. Collector Platform Adapter gathers OS metadata (Win32, GUID, Hostname, IP)    |
|  6. Performs HTTPS Handshake with SaaS Backend (POST /api/v1/collectors/enroll)   |
+----------------------------------------+------------------------------------------+
                                         |
                                         | Handshake & Token Exchange
                                         v
+-----------------------------------------------------------------------------------+
|                             OBSERVAULT SAAS BACKEND                               |
|                                                                                   |
|  7. Verifies token hash, checks 15-minute expiration & single-use policy          |
|  8. Permanently consumes enrollment token (prevents reuse)                        |
|  9. Issues operational API key: `ov_col_********************************`         |
| 10. Links Collector & Server records to Tenant in PostgreSQL / SQLite             |
| 11. Records cryptographic audit trail in `device_audit_logs`                       |
+----------------------------------------+------------------------------------------+
                                         |
                                         | Operational Key & Settings Returned
                                         v
+-----------------------------------------------------------------------------------+
|                        ENROLLED LOCAL COLLECTOR DAEMON                            |
|                                                                                   |
| 12. Stores operational key in `%LOCALAPPDATA%\ObserVault\collector_config.json`   |
| 13. Begins sending authenticated heartbeats every 15s (POST /api/v1/heartbeat)    |
| 14. Reads real CPU, RAM & Disk metrics via `psutil` (is_simulated = false)        |
| 15. Passes metrics through Local Privacy Sanitiser (stripping unapproved keys)    |
| 16. Streams batches or buffers in local SQLite (`collector_buffer.db`) on drop    |
| 17. Dashboard instantly transitions device status to "Online Active"              |
+-----------------------------------------------------------------------------------+
```

---

## 2. Windows Prerequisites

Before installing the ObserVault Windows Collector on a Windows 10 or Windows 11 host:

1. **Operating System**: Windows 10 (Build 19041+) or Windows 11 (64-bit).
2. **Python Runtime**: Python 3.10, 3.11, 3.12, 3.13, or 3.14 installed with `Add python.exe to PATH` checked.
3. **PowerShell**: Windows PowerShell 5.1 or PowerShell 7+ with script execution enabled:
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```
4. **Network Connectivity**: Outbound HTTPS/HTTP access to the ObserVault SaaS endpoint (e.g. `http://127.0.0.1:8000` or `https://app.observault.io`).
5. **Permissions**: Standard user permissions (Administrator privileges are **not** required for user-level telemetry collection).

---

## 3. Step-by-Step Enrollment Sequence

### Step 1: Device Registration in SaaS Console
1. Navigate to `/collectors` in the ObserVault Web Console.
2. Click **Add New Device**.
3. Provide:
   - **Device Name**: e.g. `Win11-Prod-Edge-01`
   - **Target OS**: `Windows 10 / 11`
   - **Environment**: `Production`, `Staging`, or `Development`
4. Click **Generate Enrollment Token**.
5. The backend generates a high-entropy token (`ov_enroll_<random_hex_32>`), stores its SHA-256 hash in the database, and binds it strictly to your tenant ID.

### Step 2: One-Line Windows Installation & Enrollment
Copy the PowerShell command displayed in the console:

```powershell
# Set enrollment environment variable and run one-line installer
$env:OBSERVAULT_ENROLL_TOKEN='ov_enroll_REPLACE_WITH_YOUR_TOKEN'; `
$env:OBSERVAULT_BACKEND_URL='http://127.0.0.1:8000'; `
python -m collector.enroll
```

*Or via PowerShell download:*
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/collectors/install.ps1" | Invoke-Expression
```

### Step 3: Automated Handshake Verification
The installer automatically:
1. Validates the local Python runtime.
2. Provisions `%LOCALAPPDATA%\ObserVault\Collector\`.
3. Performs the HTTP POST to `/api/v1/collectors/enroll`.
4. Exchanges the single-use token for a permanent operational key (`ov_col_...`).
5. Stores the configuration in `%LOCALAPPDATA%\ObserVault\Collector\collector_config.json`.
6. Sends an immediate verification heartbeat and authentic `psutil` telemetry sample.

### Step 4: Live Verification
In the ObserVault UI, the "Listening for Device..." waiting room detects the check-in and immediately transitions the device to **Online**.

---

## 4. Security Controls & Zero-Trust Architecture

| Security Threat | ObserVault Defense Mechanism |
| :--- | :--- |
| **Token Theft / Leakage** | Single-use policy: token is invalidated the moment it is consumed. 15-minute strict expiration window. Only SHA-256 hashes are persisted in the database. |
| **Cross-Tenant Attack** | The registration endpoint extracts the tenant directly from the server-side JWT session (`current_user.tenant_id`). Client-supplied tenant IDs are rejected. |
| **Credential Egress Leak** | Local Privacy Engine (`LocalPrivacySanitiser`) strips passwords, bearer tokens, connection strings, and unapproved metadata *before* egress. |
| **Replay Attacks** | Ingested telemetry batches require cryptographic HMAC signatures (`X-Signature`), nonces (`X-Nonce`), and timestamp freshness checks (`X-Timestamp`). |
| **Rogue / Compromised Host** | Immediate one-click revocation: revoking a device invalidates its operational token in the database, instantly rejecting future heartbeats and telemetry with `HTTP 403 Forbidden`. |

---

## 5. Telemetry & Heartbeat Data Flow

1. **Heartbeat Signaling (Every 15s)**:
   - Header: `X-Collector-Key: ov_col_...`
   - Payload: Collector status (`online`), version, buffered record count, transmission error count.
   - Timeout Policy: If no heartbeat arrives within 60 seconds, the backend dynamically marks the device as `offline`.
2. **Kernel Telemetry Collection (Every 5s)**:
   - Module: `collector/platform_adapter.py` (`WindowsAdapter`).
   - Extractors: `psutil.cpu_percent(interval=0.1)`, `psutil.virtual_memory()`, `psutil.disk_usage('C:\\')`.
   - Network Probing: Real socket handshake latency to backend target.
   - Provenance: Marked strictly with `is_simulated = False`.
3. **Local SQLite Buffering**:
   - If the network connection drops, records are staged in `collector_buffer.db`.
   - When connection is restored, records are transmitted in FIFO order without duplicate ingestion.

---

## 6. Device Revocation & Lifecycle Management

Administrators can revoke devices directly from the `/collectors` interface:
1. Click **View Details & Telemetry** on any device.
2. Under Danger Zone, click **Revoke Device Access**.
3. Confirmation prompt prevents accidental clicks.
4. Upon confirmation:
   - `Collector.is_revoked` is set to `True`.
   - `Collector.enrollment_status` is set to `revoked`.
   - Active tokens for the device are invalidated.
   - An entry is appended to `device_audit_logs`.
   - Any further API request bearing that collector key is blocked with `403 Forbidden`.

---

## 7. Linux-Ready Architecture (Future Roadmap)

The collector is architected around the abstract `BasePlatformAdapter`:
- `WindowsAdapter` (Active): Uses Win32 APIs, Windows Registry GUID, `C:\` disk mapping, and `psutil`.
- `LinuxAdapter` (Ready): Implements standard POSIX `/proc`, `/etc/machine-id`, `/` root filesystem metrics, and systemd service descriptors.
- Adding full Linux support requires zero changes to the core engine, backend database schema, or communication protocols.

---

## 8. Troubleshooting & FAQ

**Q: Enrollment fails with "Enrollment token has already been consumed".**
> A: Enrollment tokens are single-use by design. If you need to re-enroll a machine, generate a new token from the dashboard.

**Q: Device status remains "Pending" in the dashboard.**
> A: Ensure the Windows host has outbound HTTP/HTTPS access to the SaaS backend on port 8000 and that `python -m collector.enroll` was run without errors.

**Q: Device transitioned to "Offline".**
> A: Check if the collector process is running on the host. Verify network connectivity between the host and the SaaS backend. The moment the daemon resumes heartbeats, the status will automatically recover to "Online".
