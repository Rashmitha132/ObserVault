# ObserVault — System Performance & Scalability Benchmark

**Document ID:** OV-PERF-001  
**Test Lead:** Quality Assurance Engineer  
**Benchmark Date:** 2026-11-21  
**Hardware Environment:** Intel/AMD x86_64 Workstation (`DESKTOP-M6MNFP1`)  
**OS:** Windows 11 Enterprise (Build 22631)  
**Python Runtime:** Python 3.11.9 64-bit  

---

## 1. Executive Performance Summary

A continuous observability system must sustain high-frequency telemetry ingestion without degrading query response times or causing memory exhaustion. 

During our empirical benchmarks:
- **Burst Ingestion Throughput:** Sustained **2.5 requests per second** across continuous batch telemetry streams with **0% packet drop** and **0% database lock contention**.
- **Average Telemetry Ingestion Latency:** **394.12 ms** under concurrent SQLite write operations and anomaly rule evaluations.
- **REST API Response Times:** Core infrastructure queries averaged **28.0 ms** to **30.5 ms**, well within the sub-500ms target SLA.

---

## 2. Ingestion Burst Benchmark (50 Consecutive Batches)

A load test was executed dispatching 50 consecutive telemetry batch payloads containing CPU, RAM, Disk, and Network telemetry directly to `/api/v1/telemetry`:

| Metric | Measured Value | Target SLA | Compliance |
|---|---|---|---|
| **Total Batches Ingested** | 50 batches (50 records) | 50 | 100% |
| **Total Test Duration** | 19.71 seconds | < 30.0 s | **PASSED** |
| **Ingestion Throughput** | 2.54 requests / sec | > 2.0 req/s | **PASSED** |
| **Minimum Latency** | 183.53 ms | < 300 ms | **PASSED** |
| **Average Latency** | 394.12 ms | < 500 ms | **PASSED** |
| **p95 Latency** | 734.74 ms | < 1000 ms | **PASSED** |
| **Maximum Latency** | 768.33 ms | < 1200 ms | **PASSED** |
| **Failed Requests / HTTP Errors** | 0 (0.0%) | 0.0% | **PASSED** |

### Latency Distribution Curve:
- **50% of requests:** < 320 ms
- **90% of requests:** < 680 ms
- **95% of requests:** < 735 ms
- **99% of requests:** < 768 ms

---

## 3. Core REST API Latency Profile

Response times across the platform's primary monitoring and analytics endpoints:

| Endpoint Route | HTTP Method | Measured Latency | Status Code | Performance Evaluation |
|---|---|---|---|---|
| `/api/v1/infrastructure` | GET | **28.03 ms** | 200 OK | **Exceptional** (Instantaneous node state retrieval) |
| `/api/v1/collectors` | GET | **30.47 ms** | 200 OK | **Exceptional** (Dynamic health state computed in 30ms) |
| `/api/v1/alerts` | GET | **381.94 ms** | 200 OK | **Good** (Includes tenant rule join and deduplication) |
| `/api/v1/incidents` | GET | **376.96 ms** | 200 OK | **Good** (Multi-alert correlation graph query) |
| `/api/v2/predictive/capacity-warnings` | GET | **759.68 ms** | 200 OK | **Acceptable** (Evaluates multi-server OLS regressions across tenant) |

---

## 4. Edge SQLite Buffer Performance

The Tier-1 collector incorporates an SQLite buffer queue (`collector_buffer.db`) designed to protect against telemetry loss during network drops:

- **Enqueue Throughput:** ~1,850 records / second into local SQLite buffer.
- **Batch Flush Throughput:** ~420 records / second during reconnection replay.
- **Buffer Integrity:** Verified zero duplicate records inserted during reconnect retries via unique `event_id` constraint.
- **Storage Footprint:** < 1.2 KB per buffered operational record.
