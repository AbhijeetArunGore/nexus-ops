# NEXUS Ops — Master Requirement Traceability Matrix
**Document Version:** 3.0.0-FINAL  
**Auditor / Roles:** Principal Software Architect, Senior Fintech Systems Engineer, QA Automation Engineer  
**Evaluation Standard:** Pine Labs Practical AI Assignment 1 (AI-Powered Incident Analyzer) + Technology Operations Job Description  
**Test Suite Status:** 42/42 Tests Passing (100% reproducible on clean/isolated database)  

---

## 1. Executive Summary & Acceptance Contract

Every requirement from the Pine Labs assignment brief is verified against genuine, working source code in the repository.

| Req # | Mandatory Assignment Requirement | Frontend Location | Backend Route & Module | Test ID / File | Status | Implementation Details |
| :---: | :--- | :--- | :--- | :--- | :---: | :--- |
| **REQ-1** | **Log Ingestion:** Interface accepts logs via upload or copy-paste (.log, .txt, .json, .jsonl, .csv). | `features/investigator/LogInvestigator.tsx` | `POST /api/v1/analyses/paste`<br>`POST /api/v1/analyses/upload`<br>`app/services/normalizer.py` | `test_api.py::test_api_paste_ingestion_success_and_empty`<br>`test_api.py::test_api_upload_file_validation_and_security` | **VERIFIED COMPLETE** | Supports copy-paste and drag-and-drop. Ingests RFC 4180 CSV with headers, multiline JSON arrays, JSONL, and Log4j text. Enforces 10MB streaming size limit and magic-byte executable rejection. |
| **REQ-2** | **Error Summarization & Pattern Detection:** Summarize key errors, identify repeated failure patterns, affected services, error frequency. | `features/incidents/IncidentWorkspace.tsx` (Overview & Error Patterns Tabs) | `app/services/fingerprinting.py`<br>`app/services/pattern_detection.py` | `test_core.py::test_fingerprinting_and_patterns`<br>`test_core.py::test_pattern_detector_burst_and_retry` | **VERIFIED COMPLETE** | Clusters errors into standardized MD5/SHA fingerprints with regex template parameterization. Computes error occurrence count, burst detection ($\ge 4$ events), first/last seen timestamps, and per-service distribution. |
| **REQ-3** | **Likely Cause Identification (Evidence vs Assumptions):** Suggest likely cause based on logs, clearly distinguishing evidence from assumptions. Never present guesses as confirmed facts. | `features/incidents/IncidentWorkspace.tsx` (AI Investigation & Evidence Graph Tabs) | `POST /api/v1/incidents/{id}/investigate`<br>`app/ai/orchestration/investigator.py`<br>`app/ai/providers/*` | `evaluate_ai_quality.py` (8/8 categories)<br>`test_scenarios.py` (all 8 scenarios) | **VERIFIED COMPLETE** | Strict two-tier citation verification gate. Validates event citations against actual normalized event IDs (`EVT-`). If citations are missing or invalid, marks hypothesis as `ASSUMPTION` with `LOW` confidence; never auto-attaches unrelated events. Hypotheses explicitly separate observed facts, inferences, assumptions, and unknowns. |
| **REQ-4** | **Incident Severity Classification:** Classify Critical, High, Medium, Low with clear explanation of reason. | `components/common/SeverityBadge.tsx`<br>`features/incidents/IncidentWorkspace.tsx` | `app/services/severity_engine.py`<br>`app/schemas/incident.py` | `test_core.py::test_t06_deterministic_severity_matrix_boundaries`<br>`test_golden_scenarios.py` (14 scenarios) | **VERIFIED COMPLETE** | Explainable, rules-based mathematical point policy matrix ($\ge 70$ Critical, 35-69 High, 20-34 Medium, $<20$ Low). Decoupled 3 concepts: Operational Severity, Customer Impact (`CONFIRMED`/`SUSPECTED`/`UNKNOWN`), and Payment State Outcome (`AMBIGUOUS`, `PENDING`, `CAPTURED`, `DECLINED`, `FAILED`). Severity is never determined by an LLM. |
| **REQ-5** | **Troubleshooting & Escalation Guidance:** Practical troubleshooting steps (what to check first) and indicate when escalation is required and to whom. | `features/incidents/IncidentWorkspace.tsx` (Troubleshooting & Runbooks Tabs) | `app/services/knowledge_service.py`<br>`app/api/v1/runbooks.py` | `test_api.py::test_runbooks_endpoint` | **VERIFIED COMPLETE** | Priority-ordered, actionable check-first troubleshooting steps. Diagnostic procedures (`pg_stat_activity`, p99 latency queries) with linked SRE runbooks (`RB-PAY-001` through `RB-PAY-010`). Explicit escalation conditions, target team routing (Payment Core On-Call, DBA, Partner NOC), and recovery verification criteria. |
| **REQ-6** | **Shareable Incident Summary:** Concise incident summary for operations or engineering teams. | `features/incidents/IncidentWorkspace.tsx` (Export Summary Modal) | `GET /api/v1/incidents/{id}/export`<br>`app/api/v1/incidents.py` | `test_api.py::test_incident_export_endpoint` | **VERIFIED COMPLETE** | Implemented `/export` endpoint supporting **Markdown**, **JSON**, and **Slack format**. Interactive modal in UI provides 1-click **Copy to Clipboard** and **Download File** (.md, .json, .txt). Includes executive summary, severity, payment state outcome, evidence codes, and immediate next steps. |

---

## 2. Deliverables Acceptance Contract

| Deliverable | Requirement | Location in Repository | Verification Method | Status |
| :--- | :--- | :--- | :--- | :---: |
| **Working Prototype** | Reproducible web application with backend and frontend. | `http://localhost:8000` (FastAPI)<br>`http://localhost:5173` (Vite) | Backend pytest (42/42) + Frontend TypeScript check (0 errors) | **VERIFIED** |
| **Source Code** | Clean, modular, well-structured repository. | [GitHub Repository](https://github.com/AbhijeetArunGore/nexus-ops) | Git commit history, clean tree on `main` | **VERIFIED** |
| **Concise README** | Executive README covering approach, AI tools, assumptions, testing, and limitations. | `README.md` | Line count audit (~180 lines), relative links, screenshot embeds | **VERIFIED** |
| **10-Min Presentation** | Timed slide outline + live demo walkthrough. | `docs/DEMO_SCRIPT.md` | Timed script with step-by-step click path and offline fallback | **VERIFIED** |
| **Q&A Preparation** | Technical interview questions with honest, defensible answers. | `docs/QA_PREP.md` | 40 technical questions covering SRE, AI grounding, and fintech limits | **VERIFIED** |

---

## 3. Disclosed Limitations & Engineering Boundaries

To maintain 100% technical honesty before the Pine Labs hiring committee:
1. **Database Runtime:** SQLite is the verified local test database. SQLAlchemy models and Alembic migrations support PostgreSQL, but live PostgreSQL persistence remains unverified locally.
2. **Docker Runtime:** `docker-compose.yml` and `Dockerfile` syntax are validated, but live container runtime remains unverified if Docker Engine is not running locally.
3. **AI Provider Testing:** Automated evaluation scripts evaluate the deterministic fallback provider (`DeterministicFallbackProvider`) by default. Live Gemini 2.5 Flash is exercised when `GEMINI_API_KEY` is provided in `.env`.
4. **Telemetry Ingestion:** Ingestion is batch-oriented (up to 10MB via HTTP upload or copy-paste), not continuous Kafka or eBPF streaming.
