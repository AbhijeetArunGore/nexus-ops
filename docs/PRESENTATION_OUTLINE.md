# NEXUS Ops — 10-Minute Technical Presentation Outline

---

## Slide 1: Title & Tagline
- **Title:** NEXUS Ops — Payment Reliability & Incident Intelligence Platform
- **Tagline:** From Operational Signals to Explainable Incident Intelligence
- **Presenter:** Computer Engineering Student / Applied AI & SRE Systems
- **Domain:** Fintech, Payment Reliability, Technology Operations, SRE

---

## Slide 2: The Fintech Problem — The Incident Firehose
- **The Challenge:** Payment gateways process millions of transactions daily across microservices, databases, and banking partners.
- **The Reality:** When an outage occurs, on-call engineers face a firehose of disjointed signals: timeouts, 500 errors, connection leaks, and webhook failures.
- **The Cost:** Downtime in payments causes direct revenue loss, merchant dissatisfaction, and regulatory scrutiny.

---

## Slide 3: Core Philosophy — Deterministic First, AI Second
- **Why Naive LLM Tooling Fails:** Sending raw logs to an LLM produces hallucinations, non-reproducible severity, privacy violations (PCI/PII leaks), and high latency.
- **The NEXUS Ops Solution:**
  1. **Deterministic Layer (Facts):** Normalizes, redacts, fingerprints, groups bursts, reconstructs the timeline, and computes severity using deterministic policy rules.
  2. **AI Layer (Reasoning):** Accepts a compact, pre-structured Investigation Package with real event IDs.
  3. **Verification Invariant:** Non-existent citations are rejected automatically.

---

## Slide 4: System Architecture (Modular Monolith)
- **Frontend:** React 18, TypeScript, Vite, Tailwind CSS, Recharts.
- **Backend:** FastAPI, Pydantic v2, SQLAlchemy (SQLite & PostgreSQL).
- **Core Pipelines:** Ingestion, Redaction, Fingerprinting, Correlation, Topology (NetworkX), Severity, Evidence Graph.
- **AI Integration:** Google Gemini Flash with offline deterministic fallback.

---

## Slide 5: Live Demonstration — Scenario 04 (DB Connection Pool Exhaustion)
- **Action:** Open Payment Reliability Lab (`/lab`) -> Click "Run Live Simulation" on Scenario 04.
- **Key Highlights:**
  - Ingestion processes 8 raw logs in under 50ms.
  - Redaction strips sensitive secrets.
  - Deterministic Severity Policy Matrix scores 95 pts -> **CRITICAL** with customer impact **CONFIRMED**.
  - Reconstructed Timeline highlights First Observed vs Earliest Underlying vs Customer Impact.

---

## Slide 6: Creative Differentiator 1 — Evidence Graph & Citation Grounding
- **The Bipartite Graph:** Hypotheses -> Ingested Facts (`EVT-xxx`) -> Mitigations -> Runbooks.
- **Interactive Traceability:** Click "Why This Conclusion?" to view exact supporting events.
- **Hallucination Prevention:** The citation validator guarantees 100% citation grounding.

---

## Slide 7: Creative Differentiator 2 — 'What Am I Missing?' Adversarial Audit
- **The Concept:** Combats engineer confirmation bias.
- **Functionality:** Second-pass analysis that actively searches for contradicting evidence, alternative causes, and telemetry blindspots.

---

## Slide 8: Creative Differentiator 3 — Ops Knowledge Copilot
- **Dual Explanation Engine:**
  - **LEARNING Mode:** Educational explanations with analogies for L1 operators.
  - **ENGINEERING Mode:** Deep telemetry queries (`pg_stat_activity`), circuit breakers, and network socket inspection for L2/L3 SREs.

---

## Slide 9: Enterprise Security & Compliance Mapping
- **PCI-DSS & PII Redaction:** Regex-based masking of Card PANs, CVVs, API tokens, and credentials.
- **OWASP LLM Top 10 Mitigation:** Delimited XML boundaries `<untrusted_telemetry_observations>`, JSON schema enforcement, zero execution agency.

---

## Slide 10: Conclusion & Engineering Takeaway
- **Summary:** NEXUS Ops bridges the gap between raw telemetry and actionable, explainable incident intelligence.
- **Key Takeaway:** AI is most effective when bounded by deterministic engineering and rigorous evidence handling.
- **Q&A:** Open for questions.
