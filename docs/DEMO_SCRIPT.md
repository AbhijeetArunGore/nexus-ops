# NEXUS Ops — 7-Minute Product Demonstration Script

> **Product:** NEXUS Ops (Payment Reliability & Incident Intelligence Platform)  
> **Target Audience:** Engineering Leads, SRE Directors, Principal Architects, Fintech Evaluators

---

## Part 1: Problem & System Identity (1 Minute)
1. **Show:** Operations Overview Dashboard (`/`)
2. **Talking Points:**
   - "Good morning. In modern fintech enterprises like Pine Labs, Technology Operations and SRE teams manage millions of critical transactions across microservices, databases, and third-party bank partners."
   - "During an incident, engineers are inundated with fragmented signals: raw logs, timeouts, and alerting noise. Diagnosing cross-service failures manually is slow and error-prone."
   - "NEXUS Ops converts raw operational signals into explainable incident intelligence. Our core engineering principle is: **Deterministic Analysis First + Evidence-Grounded AI Reasoning Second**."
   - "Notice the top banner: **SIMULATED ENVIRONMENT — NO PRODUCTION CONNECTION**. This prototype uses synthetic telemetry inspired by public Pine Labs developer documentation."

---

## Part 2: Payment Reliability Lab Simulation (2 Minutes)
1. **Navigate to:** `/lab` (Payment Reliability Lab)
2. **Talking Points:**
   - "To demonstrate the platform, let's navigate to the Payment Reliability Lab. Here we have modeled 8 realistic payment scenarios: late authorization responses, webhook delivery retries, database connection exhaustion, and acquiring bank latency spikes."
   - "Let's click **Run Live Simulation** on **Scenario 04: Database Connection Pool Exhaustion & Cascade**."
   - "Notice what happens: The system is NOT showing hardcoded fake results. It streams the raw logs directly through our backend ingestion, redaction, normalization, fingerprinting, and deterministic severity engines!"
3. **Action:** Click "Run Live Simulation" on Scenario 04 -> System redirects to the Incident Workspace (`/incidents/<id>`).

---

## Part 3: Incident Workspace & Deterministic Severity (2 Minutes)
1. **Show:** Overview Tab
   - "Notice the incident summary ribbon: Evaluated as **CRITICAL** with Customer Impact **CONFIRMED**."
   - "How was this severity determined? Scroll down to the **Deterministic Severity Policy Matrix**. We did not ask an LLM to guess a severity. Our deterministic engine evaluated 8 explicit rules: +40 pts for Tier 1 core service impact (`order-db`), +35 pts for customer HTTP 5xx errors, and +30 pts for database pool saturation."
   - "Every rule displays exact citation links to the supporting events (`EVT-0001`, `EVT-0002`)."
2. **Show:** Sensitive Data Redaction
   - "Inspect the Normalized Telemetry Log Stream. Any credit card PAN, CVV, or Bearer token is automatically redacted with `[REDACTED]` before reaching the database or AI layer, preventing PCI-DSS and PII leaks."
3. **Show:** Reconstructed Timeline Tab
   - "Click the Timeline tab. The engine automatically tags:
     - **First Observed Event** (`EVT-0001`: HikariPool active connections 98/100)
     - **Earliest Underlying Cause** (`EVT-0002`: remaining connection slots reserved)
     - **First Customer Impact** (`EVT-0005`: Customer checkout payment initiation rejected HTTP 500)."

---

## Part 4: Evidence Graph & Blast Radius (1 Minute)
1. **Show:** Blast Radius Tab
   - "In distributed payment systems, a database failure causes cascading latency. Our Blast Radius Analyzer traverses the service dependency DAG in NetworkX."
   - "It cleanly separates **OBSERVED IMPACT** (`order-db`, `payment-orchestrator`, `payment-api`) from **POTENTIAL BLAST RADIUS** (upstream services exposed to timeout propagation)."
2. **Show:** Evidence Graph Tab
   - "Click Evidence Graph. Here we see the **Bipartite Attribution Graph**: AI Hypotheses linked to verifiable Ingested Event IDs, triggering Mitigations and Runbooks."
   - "If an LLM attempts to hallucinate an event citation that does not exist in the ingested logs, our citation validator strips it automatically."

---

## Part 5: 'What Am I Missing?' & Ops Copilot (1 Minute)
1. **Show:** 'What Am I Missing?' Tab
   - "Engineers frequently suffer from confirmation bias. We built the **'What Am I Missing?'** adversarial audit engine. It challenges the diagnosis, highlights unexamined failure modes (e.g. database locks vs slow queries), and audits telemetry blindspots."
2. **Show:** Ops Knowledge Copilot Tab
   - "Finally, our embedded Ops Copilot features a **Dual Explanation Engine**."
   - "In **LEARNING Mode**, it explains concepts like 504 Gateway Timeouts, connection pools, and idempotency to junior engineers using clear analogies."
   - "In **ENGINEERING Mode**, it provides senior SREs with precise PostgreSQL `pg_stat_activity` diagnostic queries and circuit-breaker tuning advice."
3. **Conclusion:** "NEXUS Ops demonstrates how deterministic engineering and grounded AI work together to deliver reliable, explainable, and secure payment operations."
