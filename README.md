# NEXUS Ops — Payment Reliability & Incident Intelligence Platform
> **Practical AI Assignment 1: AI-Powered Incident Analyzer**  
> Candidate: **Abhijeet Arun Gore** | Target Role: **Technology Operations Intern (Pune)**  
> Architecture: **Deterministic Rules-First Triage + Grounded LLM Explanation**  

---

> [!IMPORTANT]
> **SIMULATED ENVIRONMENT NOTICE:** NEXUS Ops operates exclusively on synthetic payment telemetry and simulated microservice architectures. It does not connect to live production payment gateways, customer bank accounts, or cardholder data environments.

---

## 1. Problem & Operational Solution

When payment services experience timeouts or database exhaustion, Technology Operations engineers face hundreds of disparate log lines across distributed services. NEXUS Ops provides an intelligent triage workspace that:
1. Ingests heterogeneous application logs via **drag-and-drop or copy-paste** (.log, .txt, .json, .jsonl, .csv).
2. **Masks sensitive payment credentials inline** (card PANs with Luhn check, CVVs, Bearer tokens).
3. Evaluates a **deterministic, explainable severity matrix** (Critical, High, Medium, Low) independent of LLMs.
4. Distinguishes **technical timeouts from financial outcomes** (`AMBIGUOUS`, `PENDING`, `CAPTURED`).
5. Generates **evidence-grounded hypotheses** where facts (`EVT-` IDs), inferences, and assumptions remain strictly separated.
6. Exports **shareable incident reports** in Markdown, JSON, and Slack bridge formats with one click.

---

## 2. Core Architecture Pipeline

```
[Raw Log Input] -> [Inline Redaction] -> [Normalization] -> [Fingerprinting]
       |                                                         |
       v                                                         v
[Service Inference] -> [Deterministic Severity Matrix] -> [Topology Blast Radius]
       |                                                         |
       +----------------------------> [Grounded AI Orchestrator] <+
                                               |
                                     (Citation Guard Gate)
                                               |
                              [Verified Incident Workspace & Export]
```

---

## 3. Quick Start Guide (Windows / Linux / macOS)

### Prerequisites
- Python 3.11+
- Node.js 18+ & npm

### Quick Setup Commands
```bash
# 1. Clone repository
git clone https://github.com/AbhijeetArunGore/nexus-ops.git
cd nexus-ops

# 2. Setup backend
cd backend
python -m venv venv
# Windows: venv\Scripts\activate | Unix: source venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env
# Optional: add your GEMINI_API_KEY to .env (defaults to 100% offline fallback)

# 3. Setup frontend
cd ../frontend
npm ci
npm run build

# 4. Seed clean demo data & start
cd ..
python scripts/seed_demo.py
# In terminal 1 (backend):
python -m uvicorn backend.app.main:app --port 8000 --reload
# In terminal 2 (frontend):
npm --prefix frontend run dev
```
Open **`http://localhost:5173`** to access the Operations Command Center.

---

## 4. Approach & Engineering Decisions

1. **Deterministic-First Severity:** Operational severity (Critical, High, Medium, Low) is computed via an explainable point policy based on Tier-1 core degradation, customer 5xx ingress velocity, and cascading depth. Severity is **never delegated to an LLM**.
2. **Separation of Evidence vs Assumptions:** Hypotheses are structured into observed facts (with clickable `EVT-` citations), logical inferences, and unconfirmed assumptions. Non-existent citations are stripped by the citation guard.
3. **Log-Format-Agnostic Ingestion:** Service names are extracted via JSON keys, container metadata, bracketed tags, or Java logger packages—never defaulting to `payment-api`.
4. **Reliable Offline Fallback:** If Gemini API credentials are absent, the application transparently activates the `DeterministicFallbackProvider`, providing instant local analysis with full provenance.

---

## 5. Candidate Contribution vs AI-Assisted Work

- **Individual Engineering Contribution (Abhijeet):**
  - Designed the deterministic severity matrix, separating technical errors from payment transaction states.
  - Architected the two-tier citation verification gate to prevent hallucinated evidence IDs.
  - Authored the 8 realistic payment scenarios inspired by Pine Labs payment architectures.
  - Established pytest session fixtures guaranteeing reproducible fresh-clone test runs.
  - Conducted end-to-end browser verification, defect triage, and documentation synchronization.
- **AI-Assisted Tools (Antigravity / Gemini):**
  - Accelerated initial FastAPI boilerplate endpoints and Tailwind UI styling.
  - Assisted in generating standard regex patterns for log timestamp and Luhn validation.
  - Formatted technical postmortem outlines and initial runbook drafts.

---

## 6. Automated Testing Evidence

Every reported capability is validated by automated test suites executable on a fresh clone:
```bash
# Run 42 backend regression & scenario agreement tests
python -m pytest backend/tests/test_api.py backend/tests/test_core.py backend/tests/test_scenarios.py backend/tests/test_golden_scenarios.py -v

# Run AI Answer Quality & Citation Attribution evaluation
python backend/tests/evaluate_ai_quality.py

# Run frontend TypeScript typecheck
npm --prefix frontend run type-check
```
- **Backend Tests:** 42/42 Passed (100%) in 1.4s.
- **AI Evaluation:** 8/8 Evaluation categories passed (97.5% mean accuracy).
- **Frontend Typecheck:** 0 TypeScript errors.

---

## 7. Known Limitations

1. **Batch Telemetry Ingestion:** Processes log batches up to 10MB via HTTP upload/paste rather than streaming Kafka topics.
2. **Local Storage:** SQLite is the primary verified local test database. PostgreSQL models and Alembic migrations are implemented but require a running PostgreSQL instance.
3. **Synthetic Topology:** Service dependencies represent a simulated payment mesh rather than dynamic eBPF network discovery.

---

## 8. Detailed Documentation Links

- [Requirements Traceability Matrix](docs/FINAL_REQUIREMENT_TRACEABILITY.md)
- [10-Minute Demonstration Script](docs/DEMO_SCRIPT.md)
- [Technical Q&A Preparation Bank](docs/QA_PREP.md)
- [Payment Scenario Catalog](docs/SCENARIOS.md)
- [System Architecture & Subsystems](docs/ARCHITECTURE.md)
- [AI Engineering & Grounding Design](docs/AI_ENGINEERING.md)
