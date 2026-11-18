"""
Runbook Library & Payment Knowledge Base Service (Modules 13 & 14)
Curates synthetic SRE runbooks, Pine Labs payment concepts, and operational troubleshooting guides.
"""
from typing import List, Dict, Any, Optional

RUNBOOK_CATALOG: List[Dict[str, Any]] = [
    {
        "id": "RB-PAY-001",
        "title": "Payment API 504 Gateway Timeout Investigation",
        "category": "API_GATEWAY",
        "applicable_services": ["payment-api", "payment-orchestrator", "bank-connector"],
        "symptoms": [
            "Customer checkout shows 504 Gateway Timeout",
            "Elevated p99 latency on /payments/v1/order endpoint",
            "Socket timeout communicating with internal orchestrator or bank connector"
        ],
        "investigation_steps": [
            "1. Inspect Payment API downstream HTTP client connection pool and timeout configuration (default 15s).",
            "2. Correlate trace_id across payment-orchestrator and bank-connector to isolate latency origin.",
            "3. Verify whether acquiring bank partner is acknowledging authorization requests within SLA.",
            "4. Check if thread/worker starvation is occurring in Gunicorn/Uvicorn workers."
        ],
        "escalation_conditions": "Escalate to Payment Core On-Call if timeout rate > 5% for 3 consecutive minutes.",
        "recovery_verification": "Execute synthetic canary payment orders; verify p99 latency drops below 1,500ms and HTTP 200 responses return.",
        "provenance": "SIMULATED_SRE_PROCEDURE"
    },
    {
        "id": "RB-PAY-002",
        "title": "Database Connection Pool Saturation & Deadlock Remediation",
        "category": "DATABASE",
        "applicable_services": ["order-db", "payment-orchestrator"],
        "symptoms": [
            "Errors: 'remaining connection slots are reserved for non-replication superuser connections'",
            "HikariCP/SQLAlchemy Timeout: 'Connection acquisition timed out after 30000ms'",
            "Transaction rollback rate spike"
        ],
        "investigation_steps": [
            "1. Run `SELECT count(*), state FROM pg_stat_activity GROUP BY state;` to check idle-in-transaction connections.",
            "2. Identify long-running queries (>10s) holding exclusive locks: `SELECT pid, now() - query_start, query FROM pg_stat_activity WHERE state != 'idle';`.",
            "3. Check for leaked database sessions where connection.close() is skipped on unhandled exceptions."
        ],
        "escalation_conditions": "Escalate to DBA On-Call if active connection count exceeds 90% of max_connections.",
        "recovery_verification": "Verify pool active connection count drops below 40% and transaction commit rate stabilizes.",
        "provenance": "SIMULATED_SRE_PROCEDURE"
    },
    {
        "id": "RB-PAY-003",
        "title": "Merchant Webhook Dispatch Failure & Retry Storm Control",
        "category": "WEBHOOKS",
        "applicable_services": ["webhook-dispatcher", "message-queue"],
        "symptoms": [
            "Merchant reports missing payment success notifications",
            "Webhook Dispatcher logging HTTP 500/502/504 from merchant callbacks",
            "Exponential queue buildup in dead-letter queues (DLQ)"
        ],
        "investigation_steps": [
            "1. Inspect Webhook Dispatcher error logs for specific merchant endpoint domains.",
            "2. Verify whether exponential backoff retries are active (attempts at 1m, 5m, 15m, 1h, 6h).",
            "3. Test merchant URL reachability and TLS certificate validity using curl with timeout.",
            "4. Confirm that signature verification headers (`X-Pine-Signature`) are correctly formatted."
        ],
        "escalation_conditions": "Notify Merchant Integration Support if a specific high-volume merchant endpoint remains unreachable for >30 minutes.",
        "recovery_verification": "Verify webhook queue depth decreases and merchant endpoint acknowledges 200 OK.",
        "provenance": "SIMULATED_SRE_PROCEDURE"
    },
    {
        "id": "RB-PAY-004",
        "title": "Duplicate Webhook Event & Idempotency Key Collisions",
        "category": "WEBHOOKS",
        "applicable_services": ["webhook-dispatcher", "payment-orchestrator"],
        "symptoms": [
            "Merchant receives identical payment_id notification multiple times",
            "Idempotency violation warnings in payment-orchestrator logs"
        ],
        "investigation_steps": [
            "1. Check if upstream message queue or network retries re-delivered the event.",
            "2. Verify whether the merchant endpoint is returning HTTP 200 in under 3 seconds to acknowledge receipt.",
            "3. Validate that merchant webhook consumer inspects `event_id` and processes notifications idempotently."
        ],
        "escalation_conditions": "Escalate to Application Engineering if internal deduplication cache has evicted active keys.",
        "recovery_verification": "Ensure exactly-once processing acknowledgment at consumer boundary.",
        "provenance": "SIMULATED_SRE_PROCEDURE"
    },
    {
        "id": "RB-PAY-005",
        "title": "External Acquiring Bank Latency Degradation & Circuit Breaking",
        "category": "BANK_INTEGRATION",
        "applicable_services": ["bank-connector", "external-payment-partner"],
        "symptoms": [
            "Bank Connector reporting ISO8583 socket timeout",
            "Payment authorization success rate plunges for a specific card network or UPI provider"
        ],
        "investigation_steps": [
            "1. Identify whether failure is isolated to a single acquiring bank partner or widespread.",
            "2. Check Bank Connector circuit breaker status (CLOSED, OPEN, HALF-OPEN).",
            "3. If circuit breaker is OPEN, verify if dynamic failover routing to secondary gateway partner is active.",
            "4. Review acquiring partner operational health dashboard or status page."
        ],
        "escalation_conditions": "Contact Partner Bank NOC immediately if partner response latency exceeds 10,000ms for > 2 minutes.",
        "recovery_verification": "Observe partner latency returning below 800ms and circuit breaker resetting to CLOSED.",
        "provenance": "SIMULATED_SRE_PROCEDURE"
    },
    {
        "id": "RB-PAY-006",
        "title": "Ambiguous Payment Status Verification (Late Auth Response)",
        "category": "PAYMENT_LIFECYCLE",
        "applicable_services": ["payment-api", "payment-orchestrator", "bank-connector"],
        "symptoms": [
            "Client request timed out, but late authorization response arrived from bank after timeout",
            "Order state remains PENDING while bank debited customer"
        ],
        "investigation_steps": [
            "1. DO NOT immediately mark transaction as FAILED.",
            "2. Trigger server-to-server Payment Status Verification API to poll acquiring partner for definitive state.",
            "3. If partner confirms SUCCESS: Transition order state to CHARGED and trigger out-of-band webhook notification.",
            "4. If partner confirms NOT_FOUND / FAILED: Mark order as FAILED safely."
        ],
        "escalation_conditions": "Escalate to Finance Reconciliation if status remains AMBIGUOUS after 3 polling attempts.",
        "recovery_verification": "Order reaches terminal state (CHARGED or FAILED) with matching bank UTR reference.",
        "provenance": "OFFICIAL_PINE_DOC_INSPIRED"
    },
    {
        "id": "RB-PAY-007",
        "title": "Refund Processing Failure & Reconciliation Hold",
        "category": "REFUNDS",
        "applicable_services": ["payment-orchestrator", "bank-connector"],
        "symptoms": [
            "Merchant POST /payments/v1/refund returns HTTP 500 or stays in PENDING indefinitely",
            "Acquiring partner rejects refund with error: 'TRANSACTION_ALREADY_SETTLED' or 'INSUFFICIENT_MERCHANT_BALANCE'"
        ],
        "investigation_steps": [
            "1. Inspect original payment transaction status to verify it was in CHARGED status.",
            "2. Verify whether refund was submitted with idempotent request key (`X-Idempotency-Key`).",
            "3. Check merchant settlement account balance to confirm funds are available for refund debit."
        ],
        "escalation_conditions": "Escalate to Merchant Operations if refund requests remain in PENDING > 24 hours.",
        "recovery_verification": "Refund reaches terminal SUCCESS state and customer refund ARN/RRN is generated.",
        "provenance": "OFFICIAL_PINE_DOC_INSPIRED"
    },
    {
        "id": "RB-PAY-008",
        "title": "Settlement & UTR Reconciliation Mismatch",
        "category": "SETTLEMENT",
        "applicable_services": ["settlement-engine", "core-banking-network"],
        "symptoms": [
            "Daily batch settlement file rejected by clearing network",
            "Mismatch between captured orders total and partner credited amount",
            "Missing UTR (Unique Transaction Reference) numbers in settlement report"
        ],
        "investigation_steps": [
            "1. Check settlement job logs for parsing errors or date cutoff discrepancies.",
            "2. Query un-reconciled transactions for the settlement cycle.",
            "3. Verify bank statement credit matching against batch settlement ID."
        ],
        "escalation_conditions": "Escalate to Settlement Operations if reconciliation discrepancy exceeds ₹10,000.",
        "recovery_verification": "All captured transactions matched against valid UTR with zero balance deviation.",
        "provenance": "OFFICIAL_PINE_DOC_INSPIRED"
    },
    {
        "id": "RB-PAY-009",
        "title": "Post-Deployment Canary Regression & Rollback",
        "category": "DEPLOYMENT",
        "applicable_services": ["payment-api", "payment-orchestrator"],
        "symptoms": [
            "Sudden spike in HTTP 5xx or unhandled exceptions immediately following deployment release",
            "Canary instances showing 10x error rate compared to stable baseline"
        ],
        "investigation_steps": [
            "1. Check deployment timestamp against error rate inflection point.",
            "2. Inspect application error fingerprints for new stack traces not present in previous build.",
            "3. If error budget burn rate is exceeded, initiate immediate automated or manual rollback."
        ],
        "escalation_conditions": "Trigger rollback immediately if canary error rate exceeds 1% of total traffic.",
        "recovery_verification": "Canary traffic diverted back to stable version; error rates return to baseline <0.01%.",
        "provenance": "SIMULATED_SRE_PROCEDURE"
    },
    {
        "id": "RB-PAY-010",
        "title": "Application HTTP 5xx Error Surge Investigation",
        "category": "CORE_APPLICATION",
        "applicable_services": ["payment-api", "payment-orchestrator", "webhook-dispatcher"],
        "symptoms": [
            "HTTP 500 Internal Server Error rate exceeds 2% across all endpoints",
            "Unhandled exceptions in application logs"
        ],
        "investigation_steps": [
            "1. Inspect error fingerprints to identify the primary root exception class.",
            "2. Check host CPU, memory utilization, and thread contention.",
            "3. Verify configuration drift, expired TLS certificates, or bad environment variable rollouts."
        ],
        "escalation_conditions": "Escalate to On-Call Tech Lead if 5xx errors affect multiple payment endpoints.",
        "recovery_verification": "HTTP 5xx rate drops to 0.0% on public health and status probes.",
        "provenance": "SIMULATED_SRE_PROCEDURE"
    }
]


def search_runbooks(query: str, service: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Retrieves matching runbooks based on keyword match in title, category, symptoms, or service.
    """
    q = query.lower().strip()
    results = []
    for rb in RUNBOOK_CATALOG:
        match = False
        if not q:
            match = True
        elif q in rb["title"].lower() or q in rb["category"].lower() or any(q in s.lower() for s in rb["symptoms"]):
            match = True
        elif any(q in step.lower() for step in rb["investigation_steps"]):
            match = True

        if service and service.lower() not in [s.lower() for s in rb["applicable_services"]]:
            match = False

        if match:
            results.append(rb)
    return results


def get_runbook_by_id(rb_id: str) -> Optional[Dict[str, Any]]:
    for rb in RUNBOOK_CATALOG:
        if rb["id"] == rb_id:
            return rb
    return None
