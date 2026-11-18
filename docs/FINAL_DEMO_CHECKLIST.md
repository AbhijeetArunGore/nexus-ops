# NEXUS Ops — Final Evaluator Demonstration Checklist
### Step-by-Step Live Technical Demonstration Guide

---

> **CRITICAL NOTICE FOR EVALUATORS:**  
> **SIMULATED ENVIRONMENT — NO PRODUCTION SYSTEM CONNECTION.**  
> NEXUS Ops operates completely in a self-contained local environment using synthetic payment telemetry.

---

## 1. PRE-DEMO SYSTEM STARTUP

### Step 1: Terminal 1 — Start the FastAPI Backend
```powershell
cd c:\Users\abhis\Desktop\Pine\backend
$env:PYTHONPATH='.'
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
- Verify Health: Open `http://localhost:8000/api/v1/health` in your browser.
- Expected Response: `{"status":"UP","system":"NEXUS Ops",...}`

### Step 2: Terminal 2 — Start the React Frontend
```powershell
cd c:\Users\abhis\Desktop\Pine\frontend
npm run dev
```
- Open Application: `http://localhost:5173`
- Verify that the top navigation bar displays:  
  `SIMULATED ENVIRONMENT — NO PRODUCTION CONNECTION` and `SYS: HEALTHY`.

---

## 2. AUTOMATED VERIFICATION IN ONE COMMAND

To run the complete automated test suite before starting the interactive demo:

```powershell
cd c:\Users\abhis\Desktop\Pine

# 1. Run Complete Automated Pytest Suite (41 tests, 86% coverage)
python -m pytest backend/tests --cov=backend/app --cov-report=term-missing

# 2. Run Headless Playwright Browser Suite (10 interactive browser tests)
python backend/tests/test_browser_e2e.py

# 3. Run AI Quality & Hallucination Evaluation (6 categories)
python backend/tests/evaluate_ai_quality.py

# 4. Run Throughput Benchmark (100, 1,000, 10,000 lines)
python backend/tests/benchmark_pipeline.py
```

---

## 3. SEVEN-MINUTE INTERACTIVE LIVE DEMONSTRATION WALKTHROUGH

### Minute 0:00 – 1:00 | Executive Overview & Platform Philosophy
- **Screen:** Navigate to `http://localhost:5173/` (**Operations Command Center**).
- **Action:** Point out the real-time incident summary cards, service error distribution chart, and the top disclaimer badge.
- **Talking Point:**  
  *"In payment operations, an outage generates thousands of confusing signals across API gateways, databases, and banking partners. NEXUS Ops solves this through a strict engineering principle: Deterministic Analysis First, Evidence-Grounded AI Reasoning Second."*

### Minute 1:00 – 2:30 | Live Scenario Simulation
- **Screen:** Click sidebar link **Payment Reliability Lab** (`/lab`).
- **Action:** Show the 8 synthetic scenarios inspired by Pine Labs payment workflows.
- **Trigger:** On **Scenario 04: Database Connection Pool Exhaustion**, click **"Run Live Simulation"**.
- **Observation:** The application instantly executes a REST call, processes the synthetic log stream, computes deterministic severity, and navigates into the Incident Workspace (`/incidents/{id}`).

### Minute 2:30 – 3:30 | Deterministic Severity & Timeline Milestones
- **Screen:** On the Incident Workspace **Overview** tab:
  - Severity badge displays **CRITICAL** (Score: 95).
  - Review the **Deterministic Severity Policy Matrix** grid showing exact rule weights (+40 TIER_1, +35 CUSTOMER, +30 DB_EXHAUSTION).
- **Screen:** Switch to **Timeline** tab:
  - Note the milestones: `★ EARLIEST UNDERLYING EVENT` on `order-db` HikariPool saturation versus `★ FIRST CUSTOMER IMPACT` on `payment-api` HTTP 500.

### Minute 3:30 – 4:30 | Evidence Graph & Blast Radius
- **Screen:** Switch to **Evidence Graph** tab:
  - Highlight that every hypothesis links directly to concrete, ingested `EVT-xxx` fact nodes. Non-existent IDs are strictly prohibited.
- **Screen:** Switch to **Service Blast Radius** tab:
  - Observe the NetworkX dependency DAG displaying `order-db` as root cause, with `payment-orchestrator` and `payment-api` highlighted as affected callers.

### Minute 4:30 – 5:30 | Adversarial Audit & SRE Blindspots
- **Screen:** Switch to **What Am I Missing?** tab:
  - Show the second-pass adversarial audit checking connection pool wait queues, transaction hold durations, and database CPU.
- **Screen:** Switch to **Telemetry Gaps** tab:
  - Show the missing signal detector highlighting database connection acquisition metrics and the recommended instrumentation fix.

### Minute 5:30 – 6:15 | Ops Knowledge Copilot (Dual Mode)
- **Screen:** Navigate to **Ops Knowledge Copilot** (`/copilot`).
- **Learning Mode Demonstration:**
  - Select **LEARNING MODE**.
  - Type: `"What is HTTP 504 in payments?"` -> Click **Ask Copilot**.
  - Shows plain-language concept explanation for L1 operators.
- **Engineering Mode Demonstration:**
  - Select **ENGINEERING MODE**.
  - Type: `"Which PostgreSQL database metrics and queries establish connection pool saturation?"` -> Click **Ask Copilot**.
  - Shows SRE diagnostic procedure with exact `pg_stat_activity` queries and connection slot analysis.

### Minute 6:15 – 7:00 | Human-in-the-Loop Feedback & Export
- **Screen:** Return to the incident -> Switch to **Learning & Review** tab.
- **Action:** In the *Engineer Verified Root Cause* field, enter:  
  `"Confirmed HikariPool connection starvation caused by long-running unindexed query on order ledger."`
- Click **Commit Verified Outcome** -> Green confirmation appears: `✓ Recorded to verified learning store!`.
- Click **Postmortem** tab -> Click **Draft Postmortem Now** -> Instant structured post-mortem with preventive action items.

---

## 4. OFFLINE / FALLBACK DEMONSTRATION INSTRUCTIONS

If internet access is unavailable or `GEMINI_API_KEY` is not provided:
1. Navigate to **System Settings** (`/settings`).
2. Review the **AI & Model Orchestration Layer** card:
   - Notice: `Offline Fallback Provider Active`.
   - Notice: `Citation Invariant: Enforced (Zero-Hallucination)`.
3. Run any scenario or query Copilot:
   - The platform operates with **100% functionality** using deterministic heuristic fallback rules.
   - Outputs are explicitly stamped with `is_fallback: True` and `"provider_name": "deterministic_fallback"`.
   - No crashes, no timeouts, and zero fake AI claims.
