"""
Payment Reliability Lab & Scenario Simulation Router (Module 15)
Provides 8 realistic Pine Labs-inspired synthetic payment incident scenarios
and executes them through the live deterministic analysis engine.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from app.core.database import get_db
from app.api.v1.analyses import process_and_create_incident
from app.schemas.incident import IncidentSummaryResponse

router = APIRouter(prefix="/scenarios", tags=["Payment Reliability Lab"])

# Master Catalog of 8 Pine Labs-Inspired Payment Scenarios
SCENARIOS_CATALOG: List[Dict[str, Any]] = [
    {
        "id": "scenario-01-late-response",
        "title": "Scenario 01: Late Payment Authorization Response",
        "category": "PAYMENT_LIFECYCLE",
        "description": "Payment API times out after 15s waiting for bank response; a delayed SUCCESS authorization later arrives from bank connector.",
        "difficulty": "Intermediate",
        "expected_severity": "CRITICAL",
        "expected_primary_hypothesis": "Ambiguous Payment State / Late Partner Authorization",
        "key_learning": "Never mark 504 Gateway Timeout as terminal FAILED without out-of-band status verification; customer funds may have been captured.",
        "log_sample": """2026-11-18T10:00:00.120Z [payment-api] INFO Order created order_id=SYN-ORD-9001 amount=4999.00 currency=INR
2026-11-18T10:00:00.250Z [payment-orchestrator] INFO Dispatching authorization to bank-connector txn_id=SYN-TXN-9001 trace_id=tr-9001-abc
2026-11-18T10:00:00.310Z [bank-connector] INFO Submitting ISO8583 payment authorization to external-payment-partner txn_id=SYN-TXN-9001
2026-11-18T10:00:15.350Z [payment-api] ERROR HTTP 504 Gateway Timeout waiting for orchestrator response txn_id=SYN-TXN-9001
2026-11-18T10:00:15.360Z [customer-checkout] WARN Ingress received HTTP 504 for txn_id=SYN-TXN-9001 order_status=PENDING
2026-11-18T10:00:18.420Z [bank-connector] INFO Late authorization response received from partner bank: status=SUCCESS auth_code=AUTH-882190 txn_id=SYN-TXN-9001
2026-11-18T10:00:18.440Z [payment-orchestrator] WARN Received late authorization response for already-timed-out transaction txn_id=SYN-TXN-9001 state_mismatch=true"""
    },
    {
        "id": "scenario-02-webhook-failure",
        "title": "Scenario 02: Merchant Webhook Dispatch Failure & Retry Exhaustion",
        "category": "WEBHOOKS",
        "description": "Transaction succeeds, but merchant callback URL returns HTTP 500/504 with repeated exponential retry failures.",
        "difficulty": "Beginner",
        "expected_severity": "MEDIUM",
        "expected_primary_hypothesis": "Merchant Webhook Dispatch Failure / Callback Unreachability",
        "key_learning": "Failures in asynchronous notifications do not invalidate successful payment captures; isolate webhook retries to prevent queue head-of-line blocking.",
        "log_sample": """2026-11-18T10:05:00.100Z [payment-orchestrator] INFO Payment captured successfully txn_id=SYN-TXN-9002 amount=1250.00
2026-11-18T10:05:00.200Z [message-queue] INFO Enqueued payment_success webhook event to queue 'merchant_events' txn_id=SYN-TXN-9002
2026-11-18T10:05:00.350Z [webhook-dispatcher] INFO Attempt 1: POST https://merchant-shop.example.com/api/webhook txn_id=SYN-TXN-9002
2026-11-18T10:05:03.400Z [webhook-dispatcher] ERROR Webhook HTTP 502 Bad Gateway from merchant-shop.example.com txn_id=SYN-TXN-9002
2026-11-18T10:06:03.450Z [webhook-dispatcher] WARN Attempt 2 (retry after 60s): POST failed with HTTP 504 Gateway Timeout txn_id=SYN-TXN-9002
2026-11-18T10:11:03.500Z [webhook-dispatcher] ERROR Attempt 3 (retry after 300s): Connection refused to merchant endpoint txn_id=SYN-TXN-9002
2026-11-18T10:11:03.520Z [webhook-dispatcher] WARN Moving event SYN-TXN-9002 to Dead Letter Queue (DLQ) after 3 failed attempts"""
    },
    {
        "id": "scenario-03-duplicate-webhooks",
        "title": "Scenario 03: Duplicate Webhook Events & Idempotency Collisions",
        "category": "WEBHOOKS",
        "description": "Upstream network retransmits duplicate webhook delivery; verifies idempotency key handling.",
        "difficulty": "Intermediate",
        "expected_severity": "LOW",
        "expected_primary_hypothesis": "Duplicate Notification / Idempotency Collision",
        "key_learning": "Webhook delivery is at-least-once; merchant systems must use idempotency checks to avoid double-crediting customer accounts.",
        "log_sample": """2026-11-18T10:15:00.100Z [webhook-dispatcher] INFO Dispatching webhook event_id=EVT-WH-5541 txn_id=SYN-TXN-9003 event_type=payment.captured
2026-11-18T10:15:00.850Z [merchant-endpoint] INFO Webhook processed successfully event_id=EVT-WH-5541 HTTP 200 OK
2026-11-18T10:15:02.100Z [webhook-dispatcher] WARN Re-delivering event_id=EVT-WH-5541 due to unacknowledged broker socket ACK
2026-11-18T10:15:02.300Z [payment-orchestrator] WARN Idempotency key collision detected for event_id=EVT-WH-5541 txn_id=SYN-TXN-9003 already processed at 10:15:00
2026-11-18T10:15:02.310Z [webhook-dispatcher] INFO Duplicate event recognized and dropped safely by deduplication cache"""
    },
    {
        "id": "scenario-04-db-exhaustion",
        "title": "Scenario 04: Database Connection Pool Exhaustion & Cascade",
        "category": "DATABASE",
        "description": "Relational database connection pool saturates due to slow queries, starving payment orchestrator and triggering widespread HTTP 500 errors.",
        "difficulty": "Advanced",
        "expected_severity": "CRITICAL",
        "expected_primary_hypothesis": "Database Connection Pool Saturation & Starvation",
        "key_learning": "Connection exhaustion rapidly turns isolated database query slowdowns into complete payment gateway outages.",
        "log_sample": """2026-11-18T10:20:00.050Z [order-db] WARN HikariPool-1 active connections=98/100 idle=0 pending_threads=15
2026-11-18T10:20:01.120Z [order-db] ERROR remaining connection slots are reserved for non-replication superuser connections
2026-11-18T10:20:02.200Z [payment-orchestrator] ERROR DatabaseConnectionError: Connection acquisition timed out after 30000ms txn_id=SYN-TXN-9004
2026-11-18T10:20:02.250Z [payment-orchestrator] ERROR Failed to persist order transaction record txn_id=SYN-TXN-9004 HTTP 500
2026-11-18T10:20:03.100Z [payment-api] ERROR InternalServerError: Downstream dependency order-db unreachable HTTP 500
2026-11-18T10:20:04.150Z [customer-checkout] ERROR Payment initiation rejected HTTP 500 txn_id=SYN-TXN-9005
2026-11-18T10:20:05.200Z [order-db] ERROR Connection refused: pg_stat_activity shows 100 connections in 'idle in transaction' state"""
    },
    {
        "id": "scenario-05-partner-degradation",
        "title": "Scenario 05: Acquiring Bank Partner Latency Degradation",
        "category": "BANK_INTEGRATION",
        "description": "External acquiring bank response latency surges from 400ms to 25,000ms, triggering circuit breakers.",
        "difficulty": "Advanced",
        "expected_severity": "CRITICAL",
        "expected_primary_hypothesis": "External Acquiring Partner Socket Timeout & Latency Cascade",
        "key_learning": "Resilient gateways must trip circuit breakers early to failover traffic to alternate payment aggregators before worker threads starve.",
        "log_sample": """2026-11-18T10:30:00.100Z [bank-connector] INFO Outbound ISO8583 payment request dispatched to PartnerBank-A txn_id=SYN-TXN-9006
2026-11-18T10:30:15.110Z [bank-connector] ERROR SocketTimeout: PartnerBank-A did not respond within 15000ms socket_timeout=true txn_id=SYN-TXN-9006
2026-11-18T10:30:15.150Z [payment-api] ERROR HTTP 504 Gateway Timeout on /payments/v1/order txn_id=SYN-TXN-9006
2026-11-18T10:30:18.200Z [bank-connector] ERROR SocketTimeout: PartnerBank-A latency p99 exceeds 25000ms txn_id=SYN-TXN-9007
2026-11-18T10:30:20.300Z [bank-connector] WARN CircuitBreaker 'PartnerBank-A' transitioned from CLOSED to OPEN (failure_rate=85%)
2026-11-18T10:30:21.350Z [bank-connector] INFO Dynamic route failover activated: routing pending transactions to PartnerBank-B"""
    },
    {
        "id": "scenario-06-refund-failure",
        "title": "Scenario 06: Refund Processing Failure & Ledger Discrepancy",
        "category": "REFUNDS",
        "description": "Merchant initiates customer refund; acquiring partner rejects request due to insufficient merchant settlement balance.",
        "difficulty": "Intermediate",
        "expected_severity": "MEDIUM",
        "expected_primary_hypothesis": "Refund Processing Failure / Insufficient Settlement Reserve",
        "key_learning": "Refunds fail asynchronously if the merchant's rolling settlement account balance is lower than the refund amount.",
        "log_sample": """2026-11-18T10:40:00.100Z [payment-api] INFO POST /payments/v1/refund refund_id=SYN-REF-101 txn_id=SYN-TXN-8800 amount=2500.00
2026-11-18T10:40:00.250Z [payment-orchestrator] INFO Validated original transaction SYN-TXN-8800 status=CHARGED
2026-11-18T10:40:01.100Z [bank-connector] INFO Forwarding refund debit request to clearing partner bank
2026-11-18T10:40:03.400Z [bank-connector] ERROR Partner rejected refund: error_code=INSUFFICIENT_MERCHANT_SETTLEMENT_BALANCE refund_id=SYN-REF-101
2026-11-18T10:40:03.450Z [payment-orchestrator] WARN Refund transition failed: refund_id=SYN-REF-101 placed on SETTLEMENT_HOLD
2026-11-18T10:40:03.500Z [payment-api] WARN Refund response returned status=PENDING_MERCHANT_FUNDS refund_id=SYN-REF-101"""
    },
    {
        "id": "scenario-07-settlement-mismatch",
        "title": "Scenario 07: Daily Settlement & UTR Reconciliation Mismatch",
        "category": "SETTLEMENT",
        "description": "Batch settlement job completes with missing UTR numbers for 3 captured transactions.",
        "difficulty": "Intermediate",
        "expected_severity": "MEDIUM",
        "expected_primary_hypothesis": "Settlement & UTR Reconciliation Discrepancy",
        "key_learning": "Never declare financial accounting loss from raw application errors without reconciling clearing network UTR files.",
        "log_sample": """2026-11-18T10:50:00.100Z [settlement-engine] INFO Initiating batch settlement cycle cycle_id=SETTLE-2026-11-18 total_records=450
2026-11-18T10:50:05.300Z [settlement-engine] INFO Received clearing network settlement acknowledgment batch_id=BAT-99120
2026-11-18T10:50:08.450Z [settlement-engine] WARN Reconciliation exception: 3 transactions captured on gateway missing UTR in clearing file
2026-11-18T10:50:08.500Z [settlement-engine] WARN Unmatched transaction record: txn_id=SYN-TXN-7710 captured_amount=1500.00 status=UTR_MISSING
2026-11-18T10:50:08.520Z [settlement-engine] WARN Unmatched transaction record: txn_id=SYN-TXN-7711 captured_amount=2200.00 status=UTR_MISSING
2026-11-18T10:50:08.550Z [settlement-engine] INFO Generating daily settlement discrepancy report for Finance Operations review"""
    },
    {
        "id": "scenario-08-deployment-regression",
        "title": "Scenario 08: Post-Deployment Canary Code Regression",
        "category": "DEPLOYMENT",
        "description": "Production release v2.4.1 deploys a null-pointer bug into payment-orchestrator, causing instant 5xx errors on card validation.",
        "difficulty": "Advanced",
        "expected_severity": "CRITICAL",
        "expected_primary_hypothesis": "Post-Deployment Code Regression / Null Pointer Exception",
        "key_learning": "Immediate correlation between deployment events and error rate inflection triggers rapid automated canary rollback.",
        "log_sample": """2026-11-18T11:00:00.000Z [deployment-manager] INFO Deployment initiated: releasing service 'payment-orchestrator' version=v2.4.1 commit=a89fbc
2026-11-18T11:00:15.000Z [deployment-manager] INFO Canary pod payment-orchestrator-canary-01 is READY accepting 10% traffic
2026-11-18T11:00:20.100Z [payment-orchestrator] ERROR NullPointerException: Cannot invoke 'CardToken.getFingerprint()' because 'token' is null
2026-11-18T11:00:21.250Z [payment-orchestrator] ERROR NullPointerException at com.pinelabs.payment.orchestrator.CardValidator.verify(CardValidator.java:84)
2026-11-18T11:00:22.300Z [payment-api] ERROR HTTP 500 InternalServerError from canary orchestrator txn_id=SYN-TXN-9010
2026-11-18T11:00:25.400Z [payment-orchestrator] ERROR NullPointerException at CardValidator.verify line 84 txn_id=SYN-TXN-9011
2026-11-18T11:00:30.000Z [deployment-manager] WARN Canary error budget burn rate exceeded: initiating automated rollback to v2.4.0"""
    }
]


@router.get("", response_model=List[Dict[str, Any]])
def list_scenarios():
    """
    Returns the catalog of 8 Pine Labs-inspired scenarios.
    """
    return [
        {
            "id": s["id"],
            "title": s["title"],
            "category": s["category"],
            "description": s["description"],
            "difficulty": s["difficulty"],
            "expected_severity": s["expected_severity"],
            "expected_primary_hypothesis": s["expected_primary_hypothesis"],
            "key_learning": s["key_learning"]
        }
        for s in SCENARIOS_CATALOG
    ]


@router.post("/{scenario_id}/run", response_model=IncidentSummaryResponse)
def run_scenario(scenario_id: str, db: Session = Depends(get_db)):
    """
    Executes a synthetic scenario by passing its raw logs through the real deterministic engine!
    """
    scenario = next((s for s in SCENARIOS_CATALOG if s["id"] == scenario_id), None)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found.")

    incident = process_and_create_incident(
        content=scenario["log_sample"],
        title=scenario["title"],
        db=db,
        scenario_name=scenario["id"]
    )

    total_events = len(incident.events)
    total_errors = sum(1 for e in incident.events if e.log_level in ["WARN", "ERROR", "CRITICAL"] or e.error_type)
    affected_services = sorted(list({e.service for e in incident.events}))

    return IncidentSummaryResponse(
        id=incident.id,
        incident_number=incident.incident_number,
        title=incident.title,
        severity=incident.severity,
        status=incident.status,
        customer_impact=incident.customer_impact,
        source_scenario=incident.source_scenario,
        created_at=incident.created_at,
        updated_at=incident.updated_at,
        resolved_at=incident.resolved_at,
        summary=incident.summary,
        severity_rationale={"reasons": incident.severity_rationale or []},
        total_events=total_events,
        total_errors=total_errors,
        affected_services=affected_services
    )
