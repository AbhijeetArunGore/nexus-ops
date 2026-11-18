# NEXUS Ops — 40 Evaluation & Technical Interview Q&A
**Candidate:** Abhijeet Arun Gore  
**Role:** Technology Operations Intern (Pine Labs)  
**Preparation Area:** System Architecture, SRE Practices, Fintech Mechanics, AI Integration, and Honest Limits  

---

## Category 1: AI Integration & Evidentiary Grounding

#### Q1: Why didn't you let the LLM determine incident severity directly?
> **Answer:** In financial infrastructure, severity dictates legal SLAs, customer communication, and on-call paging. LLMs are non-deterministic and can produce inconsistent results on identical inputs or suffer from prompt manipulation. By using a deterministic, rules-based engine for severity and only using the LLM for plain-English explanation, we achieve 100% mathematical reproducibility and zero hallucination risk on severity tiers.

#### Q2: How do you prevent hallucinations in AI hypotheses?
> **Answer:** We implement a **Two-Tier Evidentiary Grounding Gate**:
> 1. *Citation Validation:* Every hypothesis returned by the model must cite valid, existing `EVT-` IDs present in that specific incident's normalized stream. Non-existent IDs are stripped.
> 2. *Honesty Guard:* If the model returns no valid event citations, we do NOT manufacture artificial citations. We mark the hypothesis as `UNSUPPORTED / ASSUMPTION` with confidence `LOW` and explicitly label it in the UI.

#### Q3: How do you handle LLM rate limits or network outages?
> **Answer:** The system implements an automatic **Deterministic Fallback Provider**. If `GEMINI_API_KEY` is missing, expired, or times out, the backend transparently falls back to local heuristic reasoning. The UI surfaces a visible provider badge (`Deterministic Fallback`), ensuring zero downtime during operations.

#### Q4: How is sensitive payment data (card numbers, secrets) protected from LLM prompts?
> **Answer:** Redaction occurs at ingestion step 1 *before* events are stored in the database or passed to model prompts. We apply inline regex masking with Luhn checksum validation for card PANs, 3-digit CVV masks, Bearer token strippers, and credential masking (`****`).

---

## Category 2: Payment Domain & Fintech Mechanics

#### Q5: What is the semantic difference between an HTTP 504 Gateway Timeout and a failed payment?
> **Answer:** An HTTP 504 Gateway Timeout simply means the payment gateway's socket timed out waiting for the acquiring bank's response. The acquiring bank may have already debited the customer and approved the transaction. Therefore, a 504 indicates an `AMBIGUOUS` or `PENDING` payment outcome requiring reconciliation, NOT a confirmed transaction failure.

#### Q6: How do you distinguish notification failure from payment processing failure?
> **Answer:** In Scenario 02 (Webhook Dispatch Failure), the transaction is already captured successfully in the orchestrator database. The failure is strictly in downstream asynchronous webhook delivery to the merchant. Classifying this as Critical would be incorrect; it is a Medium severity issue with `SUSPECTED` customer impact because the money moved successfully.

#### Q7: Why are idempotency keys critical in payment webhook retries?
> **Answer:** Webhooks operate under *at-least-once* delivery semantics over unreliable networks. If a network socket drops before an ACK is received, the dispatcher retransmits the event. Without idempotency checking on unique event IDs or transaction IDs, the merchant system could process duplicate credits or duplicate fulfillments.

#### Q8: How does database connection pool exhaustion cause cascading failures across payment microservices?
> **Answer:** Payment orchestrators hold database connections to persist transaction state and execute row locks. When slow queries or unclosed sessions saturate the pool, worker threads block waiting for connections. The caller (`payment-api`) times out waiting for the orchestrator, and client checkouts time out waiting for the API. This turns a localized database slowdown into an ingress gateway outage.

---

## Category 3: System Architecture & Testing Methodology

#### Q9: How was the test suite structured to ensure fresh-clone reproducibility?
> **Answer:** We implemented a pytest `conftest.py` with session-scoped isolated SQLite databases and FastAPI `TestClient` context managers. Tables are created explicitly during test initialization and torn down cleanly. 42 automated tests validate API routes, deterministic scoring boundaries, golden scenario agreements, and data redactors without depending on pre-existing local database files.

#### Q10: What are the known limitations of NEXUS Ops today?
> **Answer:** 
> 1. The telemetry ingestion is batch-oriented via HTTP paste/upload rather than a continuous Kafka or OpenTelemetry gRPC stream.
> 2. The local database tested is SQLite; while SQLAlchemy models support PostgreSQL, distributed transaction locks are simulated.
> 3. Topology relationships are synthetic directed acyclic graphs representing a standard payment mesh rather than live eBPF service discovery.

---

## Category 4: Candidate Contribution vs AI Tools

#### Q11: What was your individual contribution vs the AI tools used during development?
> **Answer:** 
> - **Individual Contribution (Abhijeet):** Designed the core deterministic severity policy matrix; established the payment-state outcome separation (`AUTHORIZATION_REQUESTED`, `AMBIGUOUS`, `CAPTURED`); authored the 8 realistic payment scenarios; architected the citation verification rules; and conducted end-to-end testing and defect audits.
> - **AI Tools Used (Antigravity / Gemini):** Assisted in generating boilerplate FastAPI routers, styling Tailwind components, authoring regex patterns, and drafting technical documentation. Every piece of logic and architecture was verified and tested directly.
