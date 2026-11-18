# NEXUS Ops — Technology Operations 10-Minute Demonstration Script
**Target Audience:** Pine Labs Hiring Panel / Senior Technical Evaluators  
**Candidate:** Abhijeet Arun Gore  
**Role:** Technology Operations Intern (Pune)  
**Total Allocated Time:** 10 minutes live demo + 5–10 minutes technical Q&A  

---

## Part 1: Presentation Outline & Timing (10 Minutes)

```
[00:00 - 01:30] -> Problem Framing & SRE Philosophy (Why build this?)
[01:30 - 03:30] -> Live Ingestion & Deterministic Pipeline (Scenario 01 & 04)
[03:30 - 05:30] -> Grounded AI Investigation & Evidence vs Assumptions
[05:30 - 07:00] -> Topology Blast Radius & "What Am I Missing?" Telemetry Gaps
[07:00 - 08:30] -> Ops Knowledge Copilot & Runbook Library Grounding
[08:30 - 10:00] -> Summary Export, Human Learning Loop & SRE Architecture
```

---

## Part 2: Step-by-Step Live Demonstration Walkthrough

### Step 1: Opening & Operations Dashboard (00:00 - 01:30)
- **Screen:** Open `http://localhost:5173/` (Operations Command Center).
- **Talking Points:**
  - *"In high-velocity payment architectures handling millions of daily transactions, an on-call operations engineer is inundated with fragmented, noisy logs when an incident erupts."*
  - *"Our core philosophy: **Deterministic triage first; AI only to explain and assist.** An LLM should never decide severity or trigger unreviewed destructive actions."*
  - Point to the **Synthetic Telemetry Workspace** banner: *"Notice that we are completely honest about telemetry provenance. We never claim live production connections."*
  - Show the balanced dashboard: Critical, High, Medium, and Low incidents with affected payment microservices.

### Step 2: Live Log Ingestion & Drag-and-Drop (01:30 - 03:30)
- **Screen:** Click **"New Ingestion"** or navigate to `/investigate`.
- **Action:**
  - Show both tabs: **Copy-Paste** and **File Upload**.
  - Click **"Load Sample Pine Labs Gateway Incident"** (Scenario 01: Late Payment Authorization).
  - Point out the redacting mechanism: show how card numbers (`4111222233334444`), CVVs (`890`), and Bearer tokens are redacted inline *before* persistence.
  - Click **"Run Deterministic Pipeline"**.

### Step 3: Incident Workspace & Severity Matrix (03:30 - 05:30)
- **Screen:** Lands directly on the Incident Workspace (`/incidents/:id`).
- **Talking Points:**
  - Point to the **Deterministic Severity Matrix** card: *"Notice the mathematical weight calculation (+35 pts for Tier 1, +35 pts for customer ingress timeout). Every single point is backed by observable `EVT-` citations."*
  - Highlight the **Payment Outcome** distinction: *"A 504 Gateway Timeout on ingress does NOT prove the payment failed or that customer funds were lost. We explicitly classify payment outcome as `AMBIGUOUS` or `PENDING` until ledger confirmation."*
  - Click **"Trigger AI Analysis"**:
    - Observe the **Gemini / Deterministic Fallback** provider badge.
    - Inspect the primary hypothesis: observe the separate columns for **Observed Facts (`EVT-` IDs)**, **Inferences**, **Assumptions**, and **Unknowns**.
    - Emphasize: *"No guess is presented as confirmed fact. If the AI hallucinates nonexistent IDs, our citation verification layer strips them and flags the hypothesis as speculative."*

### Step 4: Evidence Graph & "What Am I Missing?" (05:30 - 07:00)
- **Screen:** Click the **"Evidence Graph"** tab, then **"What Am I Missing?"** tab.
- **Talking Points:**
  - In Evidence Graph: show the interactive nodes linking `Event -> Hypothesis -> Recommendation -> Runbook`.
  - In "What Am I Missing?": *"Junior engineers often suffer from confirmation bias—finding one error and declaring root cause. Our system acts as an adversarial devil's advocate, identifying blindspots: e.g., 'Did we verify whether acquiring partner circuit breakers tripped?' or 'Are database connections leaking in idle transactions?'"*

### Step 5: Ops Knowledge Copilot & Runbooks (07:00 - 08:30)
- **Screen:** Click **"Ops Copilot"** tab or left-nav Copilot.
- **Action:**
  - Switch between **Learning Mode** (for junior L1 ops) and **Engineering Mode** (for senior SREs).
  - Ask: *"What is an HTTP 504 Gateway Timeout and how does it differ from a failed payment?"*
  - Show the response: grounded in local SRE runbooks (`RB-PAY-001`) with suggested diagnostic queries (`pg_stat_activity`, p99 latency checks).
  - Click the linked runbook to open the operational procedure.

### Step 6: Shareable Summary Export & Conclusion (08:30 - 10:00)
- **Screen:** Click **"Export Summary"** button in header.
- **Action:**
  - Switch between **Markdown**, **JSON**, and **Slack** formats.
  - Show the 1-click **"Copy to Clipboard"** and **"Download File"**.
  - Show how the Slack summary contains bold severity, time windows, evidence codes, and immediate next steps ready for on-call bridges.
  - Conclude: *"NEXUS Ops demonstrates that AI can be responsibly integrated into fintech operations by enforcing mathematical determinism, transparent evidentiary grounding, and human-in-the-loop safety."*

---

## Part 3: Offline Demonstration Fallback Plan

If live internet connectivity or Gemini API rate limits fail during the interview:
1. **Zero-Configuration Fallback:** The application automatically falls back to `DeterministicFallbackProvider`.
2. **Provider Transparency:** The UI displays `Deterministic Offline Fallback (Rule-Based Heuristic)`.
3. **Identical Contract:** All hypotheses, evidence codes, runbooks, and export formats generate synchronously with 0ms external latency.
