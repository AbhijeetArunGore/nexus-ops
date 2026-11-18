# NEXUS Ops — Master Requirement Traceability Matrix & Defect Backlog
**Document Version:** 2.0.0-FINAL  
**Auditor / Roles:** Principal Software Architect, Senior SRE, Fintech Systems Engineer, QA Automation Engineer  
**Evaluation Standard:** Pine Labs Practical AI Assignment 1 (AI-Powered Incident Analyzer) + Technology Operations Intern Job Description  

---

## 1. Executive Summary & Verification Contract

This document provides a line-by-line traceability mapping of the NEXUS Ops platform against:
1. **The 6 Mandatory Assignment Requirements** (Assignment Brief).
2. **The 5 Deliverables** (Prototype, Source Code, Short README, Presentation, Q&A).
3. **The 7 Evaluation Focus Criteria** (Grounding, Evidence vs Assumption, Determinism, etc.).
4. **The Job Description Core Functions** (L1, L2, L3, Infra, DevOps/Cloud, Card Issuing / Parameter Validation).
5. **The Verified Defect Backlog** identified during independent code inspection of `AbhijeetArunGore/nexus-ops`.

---

## 2. Mandatory Assignment Requirements Traceability Matrix

| Req # | Verbatim Assignment Requirement | Frontend Location | Backend Route & Module | Test ID / File | Status | Technical Gap / Fix Action |
| :---: | :--- | :--- | :--- | :--- | :---: | :--- |
| **REQ-1** | **Log Ingestion:** Interface accepts logs via upload or copy-paste. Supports sample application logs. | `features/investigator/LogInvestigator.tsx` | `POST /api/v1/analyses/paste`<br>`POST /api/v1/analyses/upload`<br>`app/services/normalizer.py` | `test_api.py::test_api_paste_ingestion_success_and_empty`<br>`test_api.py::test_api_upload_multipart` | **PARTIAL** | **Gaps:** Streaming upload size guard missing (reads full bytes before limit); CSV parsing treats lines as text rather than structured columns; multiline JSON array parsing unsupported.<br>**Fix:** Implement bounded streaming, true CSV parser, multiline JSON/JSONL support. |
| **REQ-2** | **Error Summarization & Pattern Detection:** Summarize key errors, identify patterns, repeated failures, affected services, error frequency. | `features/incidents/tabs/IncidentOverviewTab.tsx`<br>`features/incidents/tabs/ErrorPatternsTab.tsx` | `app/services/fingerprinting.py`<br>`app/services/pattern_detection.py` | `test_core.py::test_fingerprinting_and_patterns`<br>`test_core.py::test_pattern_detector_burst_and_retry` | **DONE** | Validated. Needs frequency sparkline / burst indicator in Simple overview card. |
| **REQ-3** | **Likely Cause Identification (Evidence vs Assumptions):** Suggest likely cause based on logs, clearly distinguishing evidence from assumptions. Never present guesses as confirmed facts. | `features/incidents/tabs/AIInvestigationTab.tsx`<br>`features/incidents/tabs/EvidenceGraphTab.tsx` | `POST /api/v1/incidents/{id}/investigate`<br>`app/ai/orchestration/investigator.py`<br>`app/ai/providers/*` | `evaluate_ai_quality.py`<br>`test_core.py` | **PARTIAL** | **P0 Flaw:** If AI cites no valid events, `investigator.py` silently attaches the first 3 error events and marks confidence HIGH. Hypotheses drop `missing_evidence` and `assumptions`.<br>**Fix:** Never manufacture citations. Mark uncited hypotheses as `UNSUPPORTED/ASSUMPTION`. Create explicit facts/inferences/assumptions schema and UI columns. |
| **REQ-4** | **Incident Severity Classification:** Classify Critical, High, Medium, Low with clear explanation of reason. | `components/common/SeverityBadge.tsx`<br>`features/incidents/tabs/IncidentOverviewTab.tsx` | `app/services/severity_engine.py`<br>`app/schemas/incident.py` | `test_core.py::test_deterministic_severity_engine`<br>`test_golden_scenarios.py` | **PARTIAL** | **P0 Flaw:** A single payment-api HTTP 504 scores +40 (Tier 1) + 35 (5xx) = 75 (CRITICAL) and sets `customer_impact="CONFIRMED"`. Conflates technical timeout with financial outcome.<br>**Fix:** Decouple operational severity, customer experience impact, and payment transaction outcome (`AUTHORIZATION_REQUESTED`, `FAILED`, `AMBIGUOUS`). Require frequency/duration threshold for Critical. |
| **REQ-5** | **Troubleshooting & Escalation Guidance:** Practical troubleshooting steps (what to check first) and indicate when escalation is required and to whom. | `features/incidents/tabs/TroubleshootingTab.tsx`<br>`features/incidents/tabs/RunbooksTab.tsx` | `app/services/knowledge_service.py`<br>`app/api/v1/runbooks.py` | `test_api.py::test_runbooks_endpoint` | **PARTIAL** | **Gap:** Recommendations are not strictly ordered by "check first" (priority); escalation guidance lacks explicit team routing (L1/L2/L3/DBA/NOC) and time-boxed SLAs (e.g. 15 min ack).<br>**Fix:** Enrich recommendations with priority order, diagnostic commands (safe read-only), escalation routing, and trigger conditions. |
| **REQ-6** | **Shareable Incident Summary:** Concise incident summary for operations/engineering teams. | `features/incidents/tabs/IncidentOverviewTab.tsx` (needs export) | `GET /api/v1/incidents/{id}/export`<br>`app/api/v1/incidents.py` | Missing | **MISSING** | **P0 Flaw:** README lists `GET /api/v1/incidents/{id}/export`, but the endpoint is NOT implemented in `incidents.py`. UI has no Copy for Slack/Email/Markdown or Download buttons.<br>**Fix:** Implement `/export` supporting Markdown, JSON, and Slack text; add one-click copy and download buttons. |

---

## 3. Assignment Deliverables Traceability

| Deliverable | Requirement | Location / Artifact | Verification Method | Status |
| :--- | :--- | :--- | :--- | :---: |
| **Working Prototype** | Reproducible, locally runnable web application with backend + frontend. | `http://localhost:8000` (FastAPI)<br>`http://localhost:5173` (Vite) | Playwright E2E (`backend/tests/test_browser_e2e.py`) | **PARTIAL** (Fails on fresh clone without `nexus_ops.db`) |
| **Source Code** | Clean, modular, well-structured repository. | `https://github.com/AbhijeetArunGore/nexus-ops` | Git status, clean commit history | **DONE** |
| **Short README** | Max ~150 lines: approach, AI models, assumptions, testing, limitations, candidate contribution. | `README.md` | Line count audit, link audit | **DEFECT** (Currently 1,060 lines, bloated, needs concise root README + linked deep docs) |
| **10-Min Presentation** | Timed slide outline + live demo script for Pine Labs panel. | `docs/DEMO_SCRIPT.md` | Step-by-step timed demo script | **TO COMPLETE** |
| **Q&A Preparation** | 30-40 likely technical interview questions and defensible answers. | `docs/QA_PREP.md` | Comprehensive Q&A bank | **TO COMPLETE** |

---

## 4. Prioritized Defect Backlog

### Priority 0: Core Correctness & Reviewer Showstoppers (Must Fix First)
1. **Fresh Clone Test Suite Failure:** 12 tests fail with `sqlite3.OperationalError: no such table: incidents` when `nexus_ops.db` is missing because `TestClient` is initialized without lifespan context.
   - *Fix:* Create `backend/tests/conftest.py` with session-scoped temp SQLite database and lifespan dependency override.
2. **AI Analysis Not Executed in Main Flow:** `POST /analyses/paste` and `upload` only run deterministic rules; incident lands with empty hypotheses and recommendations until manual "Trigger AI" button click.
   - *Fix:* Create orchestrated analysis endpoint or automatic pipeline execution with progress indicator and offline fallback.
3. **Over-Escalating Severity Engine:** Single HTTP 504 triggers CRITICAL and CONFIRMED customer impact.
   - *Fix:* Decouple operational severity, customer impact (`CONFIRMED`/`SUSPECTED`/`UNKNOWN`), and payment outcome (`AUTHORIZED`/`CAPTURED`/`DECLINED`/`FAILED`/`AMBIGUOUS`). Require multi-event thresholds for Critical.
4. **Fabricated Grounding in Investigator:** Missing AI event IDs cause silent fallback to the first 3 errors marked HIGH confidence.
   - *Fix:* Reject invalid IDs, mark hypothesis `UNSUPPORTED/ASSUMPTION`, never auto-attach unlinked events.
5. **Missing Separation of Evidence vs Assumptions:** Hypotheses drop `missing_evidence` and `assumptions`.
   - *Fix:* Update schemas and UI with explicit columns: Facts (observed `EVT-` IDs), Inferences, Assumptions, Unknowns.
6. **Missing Shareable Export Feature:** `/export` endpoint advertised in README is not implemented; no Copy/Download buttons in UI.
   - *Fix:* Implement `GET /api/v1/incidents/{id}/export` (Markdown, JSON, Slack text) and UI Export Modal.
7. **Service Ingestion Defaults to `payment-api`:** Logs without `[service]` brackets default to `payment-api`, skewing severity.
   - *Fix:* Log-format-agnostic parser extracting service from JSON, k8s, Java loggers, syslog, or fallback to `unknown`.

### Priority 1: Ingestion, Copilot & Knowledge Retrieval
8. **Real CSV & Multiline JSON Parsing:** Ingest true CSV format with headers and pretty-printed multiline JSON arrays.
9. **Streaming File Upload Guard:** Enforce 10MB limit during streaming before reading into memory.
10. **Ops Knowledge Copilot Grounding:** Wire `RUNBOOK_CATALOG` retrieval into `ask_copilot` route. Remove claims of training on proprietary Pine Labs data.
11. **Dashboard Telemetry Accuracy:** Change "LIVE TELEMETRY" to "SIMULATED INCIDENT DATA"; fix service error count double-counting.
12. **Incident Lifecycle & Status Management:** Enforce valid state transitions (`OPEN` -> `INVESTIGATING` -> `MITIGATED` -> `RESOLVED`), requiring resolution verification notes.

### Priority 2: Job Description Coverage & Operational Tools
13. **Prometheus `/metrics` Endpoint:** Request counts, latency histogram, fallback ratios.
14. **CI/CD Workflow:** `.github/workflows/ci.yml` for lint, test, and typecheck.
15. **Card Issuing & Parameter Validation Module:** Synthetic UAT vs PROD parameter validation for bank onboarding.
16. **L1 Command Center & L2/L3 Views:** Service health tiles, MTTA/MTTR, escalation routing.
17. **Consolidate & Shorten Documentation:** Concise 150-line root `README.md`, moving deep architectural notes to `docs/architecture/`.

---
*Generated and verified against repository source code on 2026-11-18.*
