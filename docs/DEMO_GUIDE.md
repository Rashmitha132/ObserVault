# ObserVault Hackathon Demonstration Guide

This guide walks judges and evaluators through the five required demonstration scenarios.

---

## DEMO 1: Normal Infrastructure & Live Updates
1. Log in as **Acme FinTech Corp** (`admin@acme.com` / `Password123!`).
2. Navigate to **Overview** and **Infrastructure**.
3. View real system metrics updating live from the local collector daemon (`psutil`).
4. Inspect an individual server node (e.g., `prod-payment-svc`) to review its historical CPU and memory charts.

---

## DEMO 2: Privacy Protection & Zero-Leak Verification
1. Navigate to **Privacy & Egress Proof** from the left navigation.
2. Review the **Two-Tier Architecture Data Flow** diagram.
3. Scroll to the **Live Interactive Privacy Demonstration Playground**.
4. Notice the preloaded dirty raw JSON containing:
   - `password`: `"SuperSecretPassword123!DoNotLeak"`
   - `auth_token`: `"bearer_jwt_prod_api_token_abc789"`
   - `api_key`: `"sk_live_master_key_secret_456"`
5. Click **Execute Privacy Filter & Leak Test**.
6. **Result**:
   - The right panel shows the approved outbound metadata conforming to the allow-list.
   - The sensitive fields are flagged and stripped.
   - The backend runs a live database search and confirms **ZERO occurrences** of the secret exist in the cloud database.

---

## DEMO 3: Automated Anomaly Detection & Incident Correlation
1. Click the **Simulate Anomaly** button in the top navigation bar.
2. Select **High CPU Resource Spike** or **Critical Service Crash** and click to trigger.
3. Open **Alerts & Incidents**:
   - The Anomaly Engine detects the breach (>90% threshold).
   - An alert is generated and deduplicated.
   - The Incident Correlation Engine correlates the high CPU with elevated latency into a unified incident (e.g. `INC-ACM-RES`).
   - A probable cause, supporting evidence, and confidence score (~91%) are presented.
4. Click **Recommendations** to review the human-approval remediation protocol.

---

## DEMO 4: Network Interruption & Offline SQLite Buffering
1. Run the local collector in offline mode:
   ```bash
   python collector/main.py --mode live --offline
   ```
2. Watch the collector output:
   - Records are collected and passed through the privacy filter.
   - Instead of dropping data, records enter the local SQLite buffer (`collector_buffer.db`).
   - Pending buffer count increments (e.g., `Buffer: 5 pending, 0 delivered`).
3. Terminate offline mode and run normal mode:
   ```bash
   python collector/main.py --mode live
   ```
4. **Result**:
   - The collector connects to the SaaS backend.
   - All pending records are flushed in FIFO order and acknowledged.
   - SaaS dashboard receives all queued metrics with **zero lost records** and **zero duplicates**.

---

## DEMO 5: Multi-Tenant Data Isolation
1. In the top navigation bar, click the **Switch Tenant** button (or log out and log in as `admin@biohealth.com` / `Password123!`).
2. Observe the interface:
   - Tenant name updates to **BioHealth Global**.
   - Server list shows only BioHealth nodes (`genomics-pipeline-01`, `clinical-portal-01`).
   - Acme's servers, alerts, and incidents are completely invisible.
3. Tenant isolation is enforced cryptographically on the FastAPI backend using JWT claims and collector token hashing.
