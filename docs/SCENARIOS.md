# NEXUS Ops — Payment Reliability Lab Scenarios

> **Domain:** Simulated Pine Labs Payment Processing Architecture  
> **Environment Note:** SIMULATED ENVIRONMENT — NO PRODUCTION CONNECTION.  
> Inspired by publicly documented payment workflows: order creation, bank authorization, webhook dispatch, UTR reconciliation, and refunds.

---

## Scenario 01: Late Payment Authorization Response
- **Category:** Payment Lifecycle & State Machine
- **Severity Evaluated:** `HIGH` (Score: 65) | Customer Impact: `SUSPECTED`
- **The Failure Mode:** Client payment request times out after 15 seconds, returning an HTTP 504 Gateway Timeout. Three seconds after the timeout, the external acquiring bank partner returns a successful ISO8583 authorization response.
- **Why This Matters in Fintech:** If an engineer or client application blindly assumes a 504 means the transaction failed and advises the customer to retry, the customer may be double-debited!
- **Mitigation & Runbook:** Do not mark transaction terminal `FAILED`. Execute an out-of-band Payment Status Verification API call (`RB-PAY-006`) to reconcile state before notifying the merchant.

---

## Scenario 02: Merchant Webhook Dispatch Failure & Retry Exhaustion
- **Category:** Asynchronous Webhook Integration
- **Severity Evaluated:** `MEDIUM` (Score: 35) | Customer Impact: `SUSPECTED`
- **The Failure Mode:** The customer was charged successfully, but the merchant callback URL (`merchant-shop.example.com`) returns HTTP 502/504. The Webhook Dispatcher attempts exponential retries (at 1m, 5m) before routing the event to the Dead Letter Queue (DLQ).
- **Why This Matters in Fintech:** Asynchronous notification failures must never hold up payment processing queues or invalidate captured transactions.
- **Mitigation & Runbook:** Verify merchant endpoint reachability and TLS certificate validity (`RB-PAY-003`).

---

## Scenario 03: Duplicate Webhook Events & Idempotency Collisions
- **Category:** Idempotency & Deduplication
- **Severity Evaluated:** `LOW` (Score: 10) | Customer Impact: `UNKNOWN`
- **The Failure Mode:** Due to an unacknowledged broker socket acknowledgment, the Webhook Dispatcher re-delivers the identical event ID. The receiving consumer encounters an idempotency key collision.
- **Why This Matters in Fintech:** At-least-once delivery is a physical reality in distributed networks. Webhook consumers must process notifications idempotently based on `event_id` to prevent double-fulfillment.
- **Mitigation & Runbook:** Verify Redis/PostgreSQL deduplication cache TTL and idempotency key uniqueness constraints (`RB-PAY-004`).

---

## Scenario 04: Database Connection Pool Exhaustion & Cascade
- **Category:** Relational Database SRE
- **Severity Evaluated:** `CRITICAL` (Score: 95) | Customer Impact: `CONFIRMED`
- **The Failure Mode:** A slow query causes HikariCP/SQLAlchemy active connections to reach 100% capacity (`active=98/100, idle=0`). New requests time out after 30,000ms. Payment Orchestrator fails to persist transactions, cascading 500 errors to Payment API and customer checkout.
- **Why This Matters in Fintech:** Connection pool exhaustion is the #1 cause of catastrophic full-system payment gateway outages.
- **Mitigation & Runbook:** Query `pg_stat_activity` for long-running transactions and exclusive table locks (`RB-PAY-002`). Increase pool size and enforce query statement timeouts.

---

## Scenario 05: External Acquiring Bank Partner Latency Degradation
- **Category:** Partner Integration & Circuit Breakers
- **Severity Evaluated:** `CRITICAL` (Score: 85) | Customer Impact: `CONFIRMED`
- **The Failure Mode:** Partner Bank A latency surges from 400ms to 25,000ms. Socket read timeouts trigger 504 errors on customer ingress. The Bank Connector circuit breaker trips from `CLOSED` to `OPEN` and activates dynamic failover routing to Partner Bank B.
- **Why This Matters in Fintech:** Without circuit breakers, slow third-party partners exhaust gateway worker threads, crashing unrelated payment methods (UPI, NetBanking).
- **Mitigation & Runbook:** Verify circuit-breaker health, inspect partner status dashboards, and failover traffic to secondary acquiring routes (`RB-PAY-005`).

---

## Scenario 06: Refund Processing Failure & Ledger Discrepancy
- **Category:** Refund Operations
- **Severity Evaluated:** `MEDIUM` (Score: 35) | Customer Impact: `SUSPECTED`
- **The Failure Mode:** Merchant initiates a ₹2,500 refund. The acquiring partner bank rejects the refund with error code: `INSUFFICIENT_MERCHANT_SETTLEMENT_BALANCE`.
- **Why This Matters in Fintech:** Refunds fail asynchronously if the merchant's rolling settlement account balance is lower than the refund amount.
- **Mitigation & Runbook:** Place refund in `SETTLEMENT_HOLD` status until merchant settlement account is replenished (`RB-PAY-007`).

---

## Scenario 07: Daily Settlement & UTR Reconciliation Mismatch
- **Category:** Financial Settlement & Clearing
- **Severity Evaluated:** `MEDIUM` (Score: 35) | Customer Impact: `UNKNOWN`
- **The Failure Mode:** Daily batch settlement job processes 450 transactions. Three captured transactions are missing UTR (Unique Transaction Reference) numbers in the bank clearing file.
- **Why This Matters in Fintech:** Never declare accounting loss from application errors alone. Automated recon jobs must isolate unmatched UTRs for manual banking liaison.
- **Mitigation & Runbook:** Generate daily settlement discrepancy report for Finance Operations review (`RB-PAY-008`).

---

## Scenario 08: Post-Deployment Canary Code Regression
- **Category:** Deployment Engineering & Canary Rollback
- **Severity Evaluated:** `CRITICAL` (Score: 90) | Customer Impact: `CONFIRMED`
- **The Failure Mode:** Deployment of version v2.4.1 introduces a `NullPointerException` in `CardValidator.java` on canary pods. 500 errors spike immediately. Automated canary rollback restores v2.4.0 within 30 seconds.
- **Why This Matters in Fintech:** Correlation between deployment timestamps and error rate inflection points allows rapid automated rollback before customer error budgets are exhausted.
- **Mitigation & Runbook:** Initiate immediate canary traffic draining and automated rollback (`RB-PAY-009`).
