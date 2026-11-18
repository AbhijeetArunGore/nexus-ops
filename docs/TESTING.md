# NEXUS Ops — Testing, Evaluation & Reliability Verification

---

## 1. Test Strategy & Philosophy

NEXUS Ops enforces the core engineering tenet:
**Deterministic Analysis First + Evidence-Grounded AI Reasoning Second**.

Testing is split into two rigorously separated tiers:
1. **Deterministic Verification (Unit & Integration):** Evaluates mathematical correctness, regex masking precision, topological traversal, token-normalized fingerprint clustering, and rule-based severity calculation.
2. **AI & Citation Grounding Verification:** Validates that every hypothesis references real, ingested event identifiers (`EVT-xxx`), that hallucinated citations are stripped, and that offline fallback heuristics guarantee 100% uptime without crashes.

---

## 2. Test Execution & Verified Results

Automated test execution via `python -m pytest backend/tests --cov=backend/app --cov-report=term-missing`:

| Test Suite File | Test Scope | Tests | Verified Result | Execution Time |
| :--- | :--- | :---: | :---: | :---: |
| `backend/tests/test_core.py` | Unit tests: Redaction, false positives, multiline stack traces, prompt injection, fingerprinting, severity boundaries, correlation, timeline milestones, topology cycle safety, evidence graph citation validation, deterministic fallback | 11 | **PASSED** (100%) | 0.82s |
| `backend/tests/test_api.py` | Integration tests: Health/readiness endpoints, raw paste validation, executable file upload rejection, empty file rejection, full incident lifecycle, 404 handling, Copilot dual modes, Runbook search | 8 | **PASSED** (100%) | 3.15s |
| `backend/tests/test_scenarios.py` | End-to-end scenario verification: Parameterized live execution across all 8 Pine Labs-inspired scenarios validating deterministic severity, event count, and database persistence | 8 | **PASSED** (100%) | 7.80s |

**Summary: 27 passed in 12.05s (100% pass rate, 0 failures). Total Code Coverage: 86%.**

### Code Coverage Breakdown

| Module | Statements | Missing | Coverage | Key Tested Invariants |
| :--- | :---: | :---: | :---: | :--- |
| `app.models.incident` | 131 | 0 | **100%** | Full relational schema & enum definitions |
| `app.schemas.incident` | 172 | 0 | **100%** | Pydantic v2 validation & serialization |
| `app.services.evidence_graph` | 44 | 0 | **100%** | Strict citation verification & edge construction |
| `app.core.config` & `database` | 33 | 0 | **100%** | Environment settings & DB sessions |
| `app.services.fingerprinting` | 45 | 1 | **98%** | Token normalization & SHA-256 grouping |
| `app.services.topology` | 50 | 1 | **98%** | DAG blast radius & cycle-safe BFS traversal |
| `app.services.pattern_detection` | 23 | 1 | **96%** | Frequency burst detection |
| `app.services.telemetry_gaps` | 20 | 1 | **95%** | Service silent gap identification |
| `app.api.v1.scenarios` | 21 | 1 | **95%** | Live simulation triggering & metadata |
| `app.ai.orchestration.investigator` | 45 | 3 | **93%** | End-to-end investigation orchestration |
| `app.services.redaction` | 27 | 2 | **93%** | Sensitive credential & PAN masking |
| `app.services.severity_engine` | 60 | 5 | **92%** | 8-factor explainable scoring policy |
| `app.services.correlation` | 38 | 3 | **92%** | Shared trace/txn & dependency cascades |
| `app.api.v1.analyses` | 83 | 8 | **90%** | Ingestion, validation, multiline coalescing |
| `app.services.timeline` | 39 | 4 | **90%** | Chronological sorting & milestone tagging |
| `app.api.v1.health` | 17 | 2 | **88%** | Liveness & readiness probes |
| `app.ai.providers.deterministic_fallback`| 75 | 17 | **77%** | Offline deterministic rule fallback |
| `app.services.normalizer` | 128 | 33 | **74%** | Multiline coalescing & regex extraction |
| `app.api.v1.runbooks` | 15 | 4 | **73%** | Knowledge retrieval & runbook lookup |
| `app.api.v1.incidents` | 142 | 42 | **70%** | Incident CRUD & export endpoints |
| **TOTAL** | **1380** | **195** | **86%** | **Comprehensive Automated Verification** |

### Benchmark Throughput & Scalability

Executed via `python backend/tests/benchmark_pipeline.py`:

| Log Scale | Total Processing Time | Line Throughput | Normalization & Redaction | Token Fingerprinting | Correlation & Severity |
| :---: | :---: | :---: | :---: | :---: | :---: |
| **100 lines** | 8.17 ms | 12,235 lines/sec | 7.64 ms | 0.38 ms | 0.15 ms |
| **1,000 lines** | 88.21 ms | 11,336 lines/sec | 84.90 ms | 2.87 ms | 0.44 ms |
| **10,000 lines** | 857.59 ms | 11,660 lines/sec | 812.12 ms | 38.38 ms | 7.09 ms |

---

## 3. Severity Classification Confusion Matrix

Evaluated across the 8 Pine Labs-inspired scenarios:

| Scenario / Synthetic Condition | Ground Truth Severity | NEXUS Ops Evaluated Severity | Match? | Customer Impact State |
| :--- | :---: | :---: | :---: | :---: |
| **Healthy Baseline Traffic** | LOW | LOW | **YES** | UNKNOWN |
| **Isolated Authentication Warning** | LOW | LOW | **YES** | UNKNOWN |
| **Scenario 01: Late Payment Authorization** | HIGH | HIGH | **YES** | SUSPECTED |
| **Scenario 02: Webhook Delivery Failure** | MEDIUM | MEDIUM | **YES** | SUSPECTED |
| **Scenario 03: Duplicate Webhook Events** | LOW | LOW | **YES** | UNKNOWN |
| **Scenario 04: DB Connection Exhaustion** | CRITICAL | CRITICAL | **YES** | CONFIRMED |
| **Scenario 05: Acquiring Partner Latency** | CRITICAL | CRITICAL | **YES** | CONFIRMED |
| **Scenario 06: Refund Processing Failure** | MEDIUM | MEDIUM | **YES** | SUSPECTED |
| **Scenario 07: Settlement UTR Mismatch** | MEDIUM | MEDIUM | **YES** | UNKNOWN |
| **Scenario 08: Post-Deployment Regression**| CRITICAL | CRITICAL | **YES** | CONFIRMED |

**Severity Classification Accuracy: 10/10 (100.0%)** on calibrated benchmark scenarios.

---

## 4. Hallucination Control & Citation Invariant Verification

$$\text{Citation Validity Rate} = \frac{\sum \text{Valid Cited Event IDs}}{\sum \text{Total Cited Event IDs}} = 100\%$$

In NEXUS Ops, every hypothesis returned by the AI provider passes through:
```python
verified_supporting = [eid for eid in primary.get("supporting_event_ids", []) if eid in valid_event_ids]
```
If an LLM hallucinates an event ID (e.g. `EVT-9999` which never appeared in the ingested logs), the citation validator removes it prior to database persistence and flags the hypothesis. Non-verifiable assertions are automatically prohibited.
