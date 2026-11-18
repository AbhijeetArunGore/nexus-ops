# NEXUS Ops — 40 Technical Interview Q&A & SRE Evaluation Defense
**Candidate:** Abhijeet Arun Gore  
**Role:** Technology Operations Intern (Pine Labs)  
**Preparation Scope:** System Architecture, SRE Practices, Fintech Mechanics, AI Evidentiary Grounding, and Honest Limitations  

---

## Category 1: AI Integration & Evidentiary Grounding

#### Q1: Why didn't you let the LLM determine incident severity directly?
> **Answer:** In high-consequence financial infrastructure, severity classification drives automated escalations, on-call paging, and contractual customer SLAs. LLMs are probabilistic, meaning identical inputs can occasionally produce different severity tiers or be manipulated by adversarial log lines (prompt injection). We enforce an explainable, deterministic rules-based policy engine for severity and reserve the LLM strictly for natural-language synthesis, hypothesis explanation, and runbook drafting.

#### Q2: Can deterministic severity rules still fail or misclassify?
> **Answer:** Yes. A rules-based policy engine is only as good as its configured thresholds. If an unexpected failure pattern emerges that was not anticipated in the policy rules (e.g. an obscure network partition without explicit error keywords), the score may stay Low or Medium. That is why our platform includes a "What Am I Missing?" adversarial analysis and human-in-the-loop review to continually tune thresholds.

#### Q3: How do you prevent hallucinations in AI hypotheses?
> **Answer:** We implement a **Two-Tier Citation Verification Gate**:
> 1. *Citation Validation:* Every hypothesis returned by the model must cite valid, existing `EVT-` IDs present in that incident's normalized stream. Non-existent IDs are stripped.
> 2. *Honesty Guard:* If the model returns no valid event citations, we do NOT manufacture artificial citations. We mark the hypothesis as `UNSUPPORTED / ASSUMPTION` with confidence `LOW` and display it in a separate Assumptions column.
> Event citation validation confirms that the cited logs exist, but does not mathematically prove causality; it provides an auditable basis for human review.

#### Q4: How do you handle LLM rate limits or network outages?
> **Answer:** The system implements an automatic **Deterministic Fallback Provider**. If `GEMINI_API_KEY` is missing, expired, or times out, the backend transparently falls back to local heuristic reasoning. The UI surfaces a visible provider badge (`Deterministic Fallback`), ensuring zero downtime during operations.

#### Q5: How is sensitive payment data (card numbers, secrets) protected from LLM prompts?
> **Answer:** Redaction occurs at ingestion step 1 *before* events are stored in the database or passed to model prompts. We apply inline regex masking with Luhn checksum validation for card PANs, 3-digit CVV masks, Bearer token strippers, and credential masking (`****`).

---

## Category 2: Payment Domain & Fintech Mechanics

#### Q6: What is the semantic difference between an HTTP 504 Gateway Timeout and a failed payment?
> **Answer:** An HTTP 504 Gateway Timeout simply means the payment gateway's socket timed out waiting for the acquiring bank's response. The acquiring bank may have already debited the customer and approved the transaction. Therefore, a 504 indicates an `AMBIGUOUS` or `PENDING` payment outcome requiring reconciliation, NOT a confirmed transaction failure.

#### Q7: How do you distinguish notification failure from payment processing failure?
> **Answer:** In Scenario 02 (Webhook Dispatch Failure), the transaction is already captured successfully in the orchestrator database. The failure is strictly in downstream asynchronous webhook delivery to the merchant. Classifying this as Critical would be incorrect; it is a Medium severity issue with `SUSPECTED` customer impact because the money moved successfully.

#### Q8: Why are idempotency keys critical in payment webhook retries?
> **Answer:** Webhooks operate under *at-least-once* delivery semantics over unreliable networks. If a network socket drops before an ACK is received, the dispatcher retransmits the event. Without idempotency checking on unique event IDs or transaction IDs, the merchant system could process duplicate credits or duplicate fulfillments.

#### Q9: How does database connection pool exhaustion cause cascading failures across payment microservices?
> **Answer:** Payment orchestrators hold database connections to persist transaction state and execute row locks. When slow queries or unclosed sessions saturate the pool, worker threads block waiting for connections. The caller (`payment-api`) times out waiting for the orchestrator, and client checkouts time out waiting for the API. This turns a localized database slowdown into an ingress gateway outage.

---

## Category 3: System Architecture & Testing Methodology

#### Q10: How was the test suite structured to ensure fresh-clone reproducibility?
> **Answer:** We implemented a pytest `conftest.py` with session-scoped isolated SQLite databases and FastAPI `TestClient` context managers. Tables are created explicitly during test initialization and torn down cleanly. 42 automated tests validate API routes, deterministic scoring boundaries, golden scenario agreements, and data redactors without depending on pre-existing local database files.

#### Q11: What are the disclosed limitations of NEXUS Ops today?
> **Answer:** 
> 1. Telemetry ingestion is batch-oriented via HTTP paste/upload (up to 10MB) rather than a continuous Kafka or OpenTelemetry gRPC stream.
> 2. The local database tested is SQLite; while SQLAlchemy models support PostgreSQL, live PostgreSQL runtime was not exercised.
> 3. Topology relationships are synthetic directed acyclic graphs representing a standard payment mesh rather than live eBPF service discovery.

---

## Category 4: Candidate Contribution vs AI Tools

#### Q12: What was your individual contribution vs the AI tools used during development?
> **Answer:** 
> - **Individual Engineering Contribution (Abhijeet):** Designed the core deterministic severity policy matrix; established the payment-state outcome separation (`AUTHORIZATION_REQUESTED`, `AMBIGUOUS`, `CAPTURED`); authored the 8 realistic payment scenarios; architected the citation verification rules; and conducted end-to-end testing and defect audits.
> - **AI Tools Used (Antigravity / Gemini):** Assisted in generating boilerplate FastAPI routers, styling Tailwind components, authoring regex patterns, and drafting technical documentation. Every piece of logic and architecture was verified and tested directly.
