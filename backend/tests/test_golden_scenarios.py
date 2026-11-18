"""
NEXUS Ops — Independent Golden Fixture Verification & Edge Case Suite (Stage 3)
Evaluates all 8 Pine Labs-inspired payment scenarios against independently authored golden labels.
Also stresses edge cases: unrelated services, out-of-order events, missing timestamps,
conflicting signals, unknown payment status, duplicate logs, and missing trace IDs.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.normalizer import normalize_log_stream
from app.services.fingerprinting import cluster_error_patterns
from app.services.correlation import correlate_events
from app.services.severity_engine import evaluate_severity
from app.services.timeline import reconstruct_timeline
from app.services.topology import CRITICALITY_TIERS

# -----------------------------------------------------------------------------
# Independent Golden Fixtures (Authored separately from engine implementation)
# -----------------------------------------------------------------------------
GOLDEN_SCENARIOS = [
    {
        "id": "scenario-01-late-auth",
        "name": "Late Payment Authorization",
        "independent_expected_severity": "CRITICAL",
        "independent_expected_customer_impact": "CONFIRMED",
        "independent_expected_min_events": 5,
        "independent_expected_error_services": {"payment-api", "bank-connector", "customer-checkout"},
        "expected_primary_error": "TimeoutError",
        "raw_logs": """2026-11-18T10:00:00.120Z [payment-api] INFO Ingress payment order received txn_id=SYN-TXN-1001 amount=2499.00 INR
2026-11-18T10:00:00.250Z [payment-orchestrator] INFO Forwarding authorization request to bank-connector txn_id=SYN-TXN-1001
2026-11-18T10:00:15.300Z [bank-connector] ERROR SocketTimeoutException: No response received from acquiring bank within 15000ms txn_id=SYN-TXN-1001
2026-11-18T10:00:15.350Z [payment-api] ERROR HTTP 504 Gateway Timeout on payment authorization txn_id=SYN-TXN-1001
2026-11-18T10:00:15.400Z [customer-checkout] ERROR Payment attempt failed with status 504 txn_id=SYN-TXN-1001"""
    },
    {
        "id": "scenario-02-webhook-failure",
        "name": "Merchant Webhook Dispatch Failure",
        "independent_expected_severity": "MEDIUM",
        "independent_expected_customer_impact": "SUSPECTED",
        "independent_expected_min_events": 4,
        "independent_expected_error_services": {"webhook-dispatcher"},
        "expected_primary_error": "WebhookDeliveryError",
        "raw_logs": """2026-11-18T10:10:00.050Z [webhook-dispatcher] INFO Webhook event queued: event_type=payment.authorized txn_id=SYN-TXN-2001
2026-11-18T10:10:01.200Z [webhook-dispatcher] ERROR Webhook delivery failed: merchant endpoint returned HTTP 502 Bad Gateway attempt=1 txn_id=SYN-TXN-2001
2026-11-18T10:10:06.500Z [webhook-dispatcher] ERROR Webhook delivery failed: merchant endpoint returned HTTP 502 Bad Gateway attempt=2 txn_id=SYN-TXN-2001
2026-11-18T10:10:15.000Z [webhook-dispatcher] WARN Max retries exceeded; routing event to dead-letter queue (DLQ) txn_id=SYN-TXN-2001"""
    },
    {
        "id": "scenario-03-duplicate-webhook",
        "name": "Duplicate Webhook Events",
        "independent_expected_severity": "LOW",
        "independent_expected_customer_impact": "UNKNOWN",
        "independent_expected_min_events": 4,
        "independent_expected_error_services": {"payment-orchestrator"},
        "expected_primary_error": "DuplicateEventWarning",
        "raw_logs": """2026-11-18T10:15:00.100Z [webhook-dispatcher] INFO Consuming event from message queue event_id=EVT-DUP-01 txn_id=SYN-TXN-3001
2026-11-18T10:15:00.150Z [payment-orchestrator] INFO Processed payment authorization event_id=EVT-DUP-01 txn_id=SYN-TXN-3001
2026-11-18T10:15:02.300Z [webhook-dispatcher] INFO Re-delivering event from message queue retry_count=1 event_id=EVT-DUP-01 txn_id=SYN-TXN-3001
2026-11-18T10:15:02.350Z [payment-orchestrator] WARN Idempotency key collision: event_id=EVT-DUP-01 already processed. Dropped safely."""
    },
    {
        "id": "scenario-04-db-exhaustion",
        "name": "Database Connection Pool Exhaustion",
        "independent_expected_severity": "CRITICAL",
        "independent_expected_customer_impact": "CONFIRMED",
        "independent_expected_min_events": 5,
        "independent_expected_error_services": {"order-db", "payment-orchestrator", "payment-api"},
        "expected_primary_error": "DatabaseConnectionError",
        "raw_logs": """2026-11-18T10:20:00.000Z [order-db] WARN PostgreSQL connection pool approaching limit: active=98/100 idle=0
2026-11-18T10:20:02.100Z [order-db] ERROR FATAL: remaining connection slots are reserved for non-replication superuser connections
2026-11-18T10:20:02.300Z [payment-orchestrator] ERROR Cannot acquire connection from pool HikariPool-1: acquisition timeout 30000ms
2026-11-18T10:20:02.400Z [payment-orchestrator] ERROR Transaction aborted due to database connection timeout txn_id=SYN-TXN-4001
2026-11-18T10:20:02.500Z [payment-api] ERROR HTTP 500 InternalServerError from orchestrator txn_id=SYN-TXN-4001"""
    },
    {
        "id": "scenario-05-bank-latency",
        "name": "Acquiring Bank Partner Latency",
        "independent_expected_severity": "CRITICAL",
        "independent_expected_customer_impact": "CONFIRMED",
        "independent_expected_min_events": 5,
        "independent_expected_error_services": {"bank-connector", "payment-api"},
        "expected_primary_error": "TimeoutError",
        "raw_logs": """2026-11-18T10:30:00.050Z [payment-orchestrator] INFO Initiating card auth request to external banking partner txn_id=SYN-TXN-5001
2026-11-18T10:30:00.120Z [bank-connector] INFO Outbound ISO8583 message dispatched to acquiring partner bank
2026-11-18T10:30:25.500Z [bank-connector] ERROR Read timed out waiting for ISO8583 response: latency=25380ms txn_id=SYN-TXN-5001
2026-11-18T10:30:25.600Z [payment-api] ERROR HTTP 504 Gateway Timeout waiting for banking connector response txn_id=SYN-TXN-5001
2026-11-18T10:30:26.000Z [bank-connector] WARN Partner bank latency degradation detected (p99 > 20000ms); tripping circuit breaker to HALF-OPEN"""
    },
    {
        "id": "scenario-06-refund-failure",
        "name": "Refund Processing Failure",
        "independent_expected_severity": "MEDIUM",
        "independent_expected_customer_impact": "SUSPECTED",
        "independent_expected_min_events": 5,
        "independent_expected_error_services": {"bank-connector", "payment-orchestrator", "payment-api"},
        "expected_primary_error": "RefundHoldWarning",
        "raw_logs": """2026-11-18T10:40:00.100Z [payment-api] INFO Ingress refund request refund_id=SYN-REF-101 txn_id=SYN-TXN-8800 amount=1500.00
2026-11-18T10:40:00.250Z [payment-orchestrator] INFO Validated original transaction SYN-TXN-8800 status=CHARGED
2026-11-18T10:40:01.100Z [bank-connector] INFO Forwarding refund debit request to clearing partner bank
2026-11-18T10:40:03.400Z [bank-connector] ERROR Partner rejected refund: error_code=INSUFFICIENT_MERCHANT_SETTLEMENT_BALANCE refund_id=SYN-REF-101
2026-11-18T10:40:03.450Z [payment-orchestrator] WARN Refund transition failed: refund_id=SYN-REF-101 placed on SETTLEMENT_HOLD
2026-11-18T10:40:03.500Z [payment-api] WARN Refund response returned status=PENDING_MERCHANT_FUNDS refund_id=SYN-REF-101"""
    },
    {
        "id": "scenario-07-settlement-mismatch",
        "name": "Settlement & UTR Reconciliation Mismatch",
        "independent_expected_severity": "MEDIUM",
        "independent_expected_customer_impact": "UNKNOWN",
        "independent_expected_min_events": 5,
        "independent_expected_error_services": {"settlement-engine"},
        "expected_primary_error": "SettlementDiscrepancyWarning",
        "raw_logs": """2026-11-18T10:50:00.100Z [settlement-engine] INFO Initiating batch settlement cycle cycle_id=SETTLE-2026-11-18 total_records=450
2026-11-18T10:50:05.300Z [settlement-engine] INFO Received clearing network settlement acknowledgment batch_id=BAT-99120
2026-11-18T10:50:08.450Z [settlement-engine] WARN Reconciliation exception: 3 transactions captured on gateway missing UTR in clearing file
2026-11-18T10:50:08.500Z [settlement-engine] WARN Unmatched transaction record: txn_id=SYN-TXN-7710 captured_amount=1500.00 status=UTR_MISSING
2026-11-18T10:50:08.520Z [settlement-engine] WARN Unmatched transaction record: txn_id=SYN-TXN-7711 captured_amount=2200.00 status=UTR_MISSING"""
    },
    {
        "id": "scenario-08-deployment-regression",
        "name": "Post-Deployment Canary Code Regression",
        "independent_expected_severity": "CRITICAL",
        "independent_expected_customer_impact": "CONFIRMED",
        "independent_expected_min_events": 5,
        "independent_expected_error_services": {"payment-orchestrator", "payment-api"},
        "expected_primary_error": "NullPointerException",
        "raw_logs": """2026-11-18T11:00:00.000Z [deployment-manager] INFO Deployment initiated: releasing service 'payment-orchestrator' version=v2.4.1 commit=a89fbc
2026-11-18T11:00:15.000Z [deployment-manager] INFO Canary pod payment-orchestrator-canary-01 is READY accepting 10% traffic
2026-11-18T11:00:20.100Z [payment-orchestrator] ERROR NullPointerException: Cannot invoke 'CardToken.getFingerprint()' because 'token' is null
2026-11-18T11:00:21.250Z [payment-orchestrator] ERROR NullPointerException at com.pinelabs.payment.orchestrator.CardValidator.verify(CardValidator.java:84)
2026-11-18T11:00:22.300Z [payment-api] ERROR HTTP 500 InternalServerError from canary orchestrator txn_id=SYN-TXN-9010"""
    }
]


@pytest.mark.parametrize("fixture", GOLDEN_SCENARIOS)
def test_independent_golden_scenario_agreement(fixture):
    """
    Validates that the deterministic pipeline matches the independently authored
    golden fixtures across severity, customer impact, error services, and event counts.
    """
    events = normalize_log_stream(fixture["raw_logs"])
    assert len(events) >= fixture["independent_expected_min_events"], f"Scenario {fixture['id']} had fewer events than expected"

    patterns = cluster_error_patterns(events)
    correlations = correlate_events(events)
    severity_decision = evaluate_severity(events, patterns, correlations)

    # 1. Severity Agreement
    assert severity_decision.severity == fixture["independent_expected_severity"], (
        f"Scenario {fixture['id']}: Evaluated severity '{severity_decision.severity}' != Golden '{fixture['independent_expected_severity']}'"
    )

    # 2. Customer Impact Agreement
    assert severity_decision.customer_impact == fixture["independent_expected_customer_impact"], (
        f"Scenario {fixture['id']}: Evaluated impact '{severity_decision.customer_impact}' != Golden '{fixture['independent_expected_customer_impact']}'"
    )

    # 3. Failing Service Extraction Agreement
    error_events = [e for e in events if e.get("log_level") in ["WARN", "ERROR", "CRITICAL"] or e.get("error_type")]
    extracted_error_services = {e["service"] for e in error_events if e.get("service")}
    for expected_svc in fixture["independent_expected_error_services"]:
        assert expected_svc in extracted_error_services, (
            f"Scenario {fixture['id']}: Expected error service '{expected_svc}' not captured in {extracted_error_services}"
        )


# -----------------------------------------------------------------------------
# Edge Cases & Adversarial Ingestion Testing
# -----------------------------------------------------------------------------

def test_edge_case_unrelated_services_temporal_coincidence():
    """
    Edge Case A: Similar timestamps across completely unrelated services (no shared txn/trace/dependency)
    must NOT produce a false dependency cascade correlation.
    """
    logs = """2026-11-18T12:00:00.100Z [settlement-engine] WARN Scheduled recon job delayed
2026-11-18T12:00:00.200Z [customer-checkout] WARN Client device network dropped
2026-11-18T12:00:00.300Z [merchant-endpoint] WARN Merchant dashboard session refresh"""
    events = normalize_log_stream(logs)
    correlations = correlate_events(events)

    # Dependency cascade must NOT be formed between settlement-engine and merchant-endpoint
    cascade_groups = [g for g in correlations if g["correlation_type"] == "DEPENDENCY_CASCADE"]
    assert len(cascade_groups) == 0, f"False dependency cascade formed: {cascade_groups}"


def test_edge_case_out_of_order_timestamps():
    """
    Edge Case B: Out-of-order log streams must be sorted chronologically by the timeline reconstructor.
    """
    logs = """2026-11-18T12:00:30.000Z [payment-api] ERROR Late Event 3
2026-11-18T12:00:05.000Z [payment-orchestrator] ERROR Earliest Event 1
2026-11-18T12:00:15.000Z [bank-connector] ERROR Middle Event 2"""
    events = normalize_log_stream(logs)
    timeline_res = reconstruct_timeline(events)
    timeline = timeline_res["items"]

    assert len(timeline) == 3
    # Check strict chronological order
    timestamps = [item["timestamp"] for item in timeline]
    assert timestamps == sorted(timestamps), f"Timeline items were not chronologically sorted: {timestamps}"
    assert "Earliest Event 1" in timeline[0]["message"]
    assert "Late Event 3" in timeline[2]["message"]


def test_edge_case_missing_timestamps():
    """
    Edge Case C: Logs with missing or corrupted timestamps must not crash the pipeline.
    """
    logs = """[payment-api] ERROR Request failed without timestamp txn_id=SYN-TXN-9999
[order-db] WARN Connection slow without date"""
    events = normalize_log_stream(logs)
    assert len(events) == 2
    # Events should be normalized and assigned fallbacks or None without raising unhandled exceptions
    patterns = cluster_error_patterns(events)
    assert len(patterns) > 0


def test_edge_case_conflicting_signals_isolated_warning_with_success():
    """
    Edge Case D: Healthy ingress 200 traffic mixed with an isolated warning must not escalate to CRITICAL.
    """
    logs = """2026-11-18T12:10:00.100Z [payment-api] INFO HTTP 200 OK txn_id=SYN-TXN-801
2026-11-18T12:10:01.200Z [payment-api] INFO HTTP 200 OK txn_id=SYN-TXN-802
2026-11-18T12:10:02.300Z [customer-checkout] WARN User closed browser tab during redirection
2026-11-18T12:10:03.400Z [payment-api] INFO HTTP 200 OK txn_id=SYN-TXN-803"""
    events = normalize_log_stream(logs)
    patterns = cluster_error_patterns(events)
    correlations = correlate_events(events)
    sev = evaluate_severity(events, patterns, correlations)

    assert sev.severity == "LOW", f"Expected LOW for normal traffic with tab close, got {sev.severity}"
    assert sev.customer_impact in ["UNKNOWN", "NONE"]


def test_edge_case_unknown_payment_status_communicates_uncertainty():
    """
    Edge Case E: When log lacks HTTP status codes or explicit error types, customer impact
    must remain UNKNOWN and not jump to CONFIRMED.
    """
    logs = """2026-11-18T12:15:00.000Z [bank-connector] WARN Minor socket delay on upstream channel
2026-11-18T12:15:01.000Z [payment-orchestrator] INFO Retrying internal ping"""
    events = normalize_log_stream(logs)
    patterns = cluster_error_patterns(events)
    correlations = correlate_events(events)
    sev = evaluate_severity(events, patterns, correlations)

    assert sev.customer_impact == "UNKNOWN", f"Expected UNKNOWN customer impact, got {sev.customer_impact}"
    assert sev.severity in ["LOW", "MEDIUM"]


def test_edge_case_duplicate_event_lines_deduplication():
    """
    Edge Case F: 50 identical repeated log lines should be clustered into a single pattern
    with occurrence_count == 50, rather than flooding the forensic workspace.
    """
    log_line = "2026-11-18T12:20:00.000Z [webhook-dispatcher] ERROR ConnectException: Connection refused to merchant endpoint\n"
    logs = log_line * 50
    events = normalize_log_stream(logs)
    patterns = cluster_error_patterns(events)

    assert len(patterns) == 1, f"Expected exactly 1 clustered pattern for identical logs, got {len(patterns)}"
    assert patterns[0]["occurrence_count"] == 50
