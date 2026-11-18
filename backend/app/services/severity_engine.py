"""
Deterministic Severity & Payment Impact Engine (Module 9)
Evaluates an explainable 4-tier policy decision matrix (CRITICAL, HIGH, MEDIUM, LOW)
based on service criticality, error velocity, cascading depth, customer impact,
and payment-state outcome.

Engineering Principles:
- Severity is NEVER determined by an LLM.
- Separates:
  1. Operational Incident Severity (CRITICAL, HIGH, MEDIUM, LOW)
  2. Customer Experience Impact (CONFIRMED, SUSPECTED, UNKNOWN)
  3. Payment Transaction Outcome (AUTHORIZATION_REQUESTED, AUTHORIZED, CAPTURED, DECLINED, FAILED, PENDING, AMBIGUOUS, UNKNOWN)
- A single isolated 504 timeout does not become Critical or Confirmed Financial Loss.
- Evaluates multi-factor evidence: tier-1 degradation, ingress 5xx, database exhaustion, cascading correlation.
"""
from typing import List, Dict, Any, Set
from app.schemas.incident import SeverityDecision, SeverityRationaleItem
from app.services.topology import CRITICALITY_TIERS


def evaluate_severity(
    events: List[Dict[str, Any]],
    patterns: List[Dict[str, Any]],
    correlated_groups: List[Dict[str, Any]]
) -> SeverityDecision:
    """
    Computes deterministic incident severity, customer impact status, and payment outcome.
    """
    score = 0
    reasons: List[SeverityRationaleItem] = []
    customer_impact = "UNKNOWN"
    payment_outcome = "UNKNOWN"

    error_events = [e for e in events if e.get("log_level") in ["WARN", "ERROR", "CRITICAL"] or e.get("error_type")]
    failing_services: Set[str] = {e.get("service", "").lower() for e in error_events if e.get("service")}
    all_messages_lower = " ".join(e.get("message", "").lower() for e in events)

    # Business partner declines are functional rejections, not platform infrastructure outages
    business_rejection_keywords = ["insufficient", "declined", "card_expired", "invalid_cvv", "settlement_hold"]

    # --- 1. Evaluate Payment Transaction Outcome ---
    if "captured successfully" in all_messages_lower or "payment_captured" in all_messages_lower:
        payment_outcome = "CAPTURED"
    elif "authorized successfully" in all_messages_lower or "authorization_approved" in all_messages_lower:
        payment_outcome = "AUTHORIZED"
    elif "settlement_hold" in all_messages_lower or "payout_hold" in all_messages_lower:
        payment_outcome = "PENDING"
    elif any(k in all_messages_lower for k in ["declined", "insufficient_funds", "invalid_cvv", "card_expired"]):
        payment_outcome = "DECLINED"
    elif "timeout" in all_messages_lower or "504" in all_messages_lower:
        if "reconciliation" in all_messages_lower or "delayed response" in all_messages_lower or "late authorization" in all_messages_lower:
            payment_outcome = "AMBIGUOUS"
        else:
            payment_outcome = "PENDING"
    elif any("failed" in e.get("message", "").lower() for e in error_events if e.get("service") in ["payment-api", "payment-orchestrator"]):
        payment_outcome = "FAILED"
    elif events:
        payment_outcome = "AUTHORIZATION_REQUESTED"

    # --- 2. Rule 1: Tier 1 Service Failure ---
    # Business rejections (like refund holds or card declined) are functional logic, not Tier 1 outages
    is_refund_scenario = any("refund" in e.get("message", "").lower() or "settlement_hold" in e.get("message", "").lower() for e in error_events)
    tier_1_failing = [
        s for s in failing_services
        if CRITICALITY_TIERS.get(s) == "TIER_1"
        and not is_refund_scenario
        and any(
            e.get("service") == s
            and e.get("log_level") in ["ERROR", "CRITICAL"]
            and not any(k in e.get("message", "").lower() for k in business_rejection_keywords)
            for e in error_events
        )
    ]
    if tier_1_failing:
        score += 35
        reasons.append(SeverityRationaleItem(
            rule="TIER_1_PAYMENT_SERVICE_IMPACT",
            weight="+35 pts",
            description=f"Critical payment processing service(s) degraded: {', '.join(tier_1_failing)}",
            supporting_event_ids=[e["event_id"] for e in error_events if e.get("service") in tier_1_failing][:6]
        ))

    # --- 3. Rule 2: Customer-Facing Ingress Errors ---
    # Ingress HTTP 5xx or customer checkout failures or canary deployment 500s
    client_5xx = [
        e for e in error_events
        if e.get("service") in ["payment-api", "customer-checkout"]
        and (
            ((e.get("http_status") or 0) >= 500)
            or "http 500" in e.get("message", "").lower()
            or "http 504" in e.get("message", "").lower()
            or " 500 " in e.get("message", "")
            or " 504 " in e.get("message", "")
            or "gateway timeout" in e.get("message", "").lower()
            or "attempt failed" in e.get("message", "").lower()
        )
    ]

    distinct_txns = {e.get("transaction_id") for e in client_5xx if e.get("transaction_id")}

    if client_5xx:
        score += 35
        # If there are customer checkout failures, multiple 5xx events, multiple txns, or accompanying db/partner outages
        has_critical_context = any(
            e.get("service") in ["order-db", "bank-connector", "deployment-manager"]
            or "timeout" in e.get("message", "").lower()
            or "nullpointer" in e.get("message", "").lower()
            for e in error_events
        )
        if len(client_5xx) >= 2 or any(e.get("service") == "customer-checkout" for e in client_5xx) or len(distinct_txns) >= 2 or has_critical_context:
            customer_impact = "CONFIRMED"
        else:
            customer_impact = "SUSPECTED"

        reasons.append(SeverityRationaleItem(
            rule="CUSTOMER_PAYMENT_INGRESS_FAILURE",
            weight="+35 pts",
            description=f"Observed {len(client_5xx)} customer-facing HTTP 5xx/504 errors on payment ingress.",
            supporting_event_ids=[e["event_id"] for e in client_5xx][:6]
        ))
    elif any(e.get("service") == "payment-api" for e in error_events):
        customer_impact = "SUSPECTED"

    # --- 4. Rule 3: Cascading Multi-Service Failure ---
    has_cascade = any(g.get("correlation_type") == "DEPENDENCY_CASCADE" for g in correlated_groups)
    infra_failing = [
        s for s in failing_services
        if not is_refund_scenario
        and any(
            e.get("service") == s
            and not any(k in e.get("message", "").lower() for k in business_rejection_keywords)
            for e in error_events
        )
    ]
    if (has_cascade and not is_refund_scenario) or len(infra_failing) >= 3:
        score += 25
        reasons.append(SeverityRationaleItem(
            rule="MULTI_SERVICE_CASCADING_FAILURE",
            weight="+25 pts",
            description=f"Error propagation spans multiple services across architecture ({len(infra_failing)} services affected).",
            supporting_event_ids=[e["event_id"] for e in error_events][:6]
        ))

    # --- 5. Rule 4: High Error Velocity / Burst ---
    max_burst = max([p.get("occurrence_count", 0) for p in patterns], default=0)
    if max_burst >= 4:
        score += 20
        reasons.append(SeverityRationaleItem(
            rule="HIGH_FREQUENCY_ERROR_BURST",
            weight="+20 pts",
            description=f"Single error fingerprint burst triggered {max_burst} times.",
            supporting_event_ids=[e["event_id"] for e in error_events[:6]]
        ))

    # --- 6. Rule 5: Database Connection Pool Exhaustion ---
    db_exhaustion = any(
        e.get("error_type") == "DatabaseConnectionError"
        or ("pool" in e.get("message", "").lower() and e.get("service") in ["order-db", "payment-orchestrator"])
        or "connection slots" in e.get("message", "").lower()
        for e in error_events
    )
    if db_exhaustion:
        score += 35
        reasons.append(SeverityRationaleItem(
            rule="DATABASE_CONNECTION_EXHAUSTION",
            weight="+35 pts",
            description="Database connection pool saturation detected, risking system-wide deadlock.",
            supporting_event_ids=[e["event_id"] for e in error_events if e.get("error_type") == "DatabaseConnectionError" or "pool" in e.get("message", "").lower()][:6]
        ))

    # --- 7. Rule 6: Settlement & Reconciliation Discrepancy ---
    has_settlement_issue = any(
        "settlement" in e.get("service", "").lower()
        or "utr" in e.get("message", "").lower()
        or "reconciliation" in e.get("message", "").lower()
        for e in error_events
    )
    if has_settlement_issue and not tier_1_failing:
        score += 25
        reasons.append(SeverityRationaleItem(
            rule="SETTLEMENT_RECONCILIATION_DISCREPANCY",
            weight="+25 pts",
            description="Operational records contain unmatched settlement UTR references requiring clearing reconciliation.",
            supporting_event_ids=[e["event_id"] for e in error_events if "settlement" in e.get("service", "").lower() or "utr" in e.get("message", "").lower()][:6]
        ))

    # --- 8. Rule 7: Webhook / Batch Asynchronous Failures ---
    webhook_failures = [
        e for e in error_events
        if "webhook" in e.get("service", "").lower()
        and (e.get("log_level") in ["ERROR", "CRITICAL"] or "failed" in e.get("message", "").lower() or "502" in e.get("message", ""))
        and "dropped safely" not in e.get("message", "").lower()
    ]
    if not tier_1_failing and webhook_failures:
        score += 20
        if customer_impact == "UNKNOWN":
            customer_impact = "SUSPECTED"
        reasons.append(SeverityRationaleItem(
            rule="ASYNCHRONOUS_NOTIFICATION_DELAY",
            weight="+20 pts",
            description="Failures isolated to asynchronous webhook dispatch. Transactions may have authorized successfully.",
            supporting_event_ids=[e["event_id"] for e in webhook_failures][:6]
        ))

    # --- 9. Rule 8: Refund Processing Hold ---
    # Functional rejection due to merchant settlement reserve is a business rule hold, not platform infrastructure failure
    has_refund_issue = any(
        "refund" in e.get("message", "").lower() or "settlement_hold" in e.get("message", "").lower()
        for e in error_events
    )
    if has_refund_issue and not client_5xx:
        score += 25
        if customer_impact == "UNKNOWN":
            customer_impact = "SUSPECTED"
        reasons.append(SeverityRationaleItem(
            rule="REFUND_PROCESSING_HOLD",
            weight="+25 pts",
            description="Customer refund request placed on hold due to partner or settlement balance constraints.",
            supporting_event_ids=[e["event_id"] for e in error_events if "refund" in e.get("message", "").lower()][:6]
        ))

    # --- 10. Map Score to Severity Tier ---
    if score >= 70:
        severity = "CRITICAL"
    elif score >= 35:
        severity = "HIGH"
    elif score >= 20:
        severity = "MEDIUM"
    else:
        severity = "LOW"
        if not reasons:
            reasons.append(SeverityRationaleItem(
                rule="NORMAL_OR_ISOLATED_ACTIVITY",
                weight="0 pts",
                description="No multi-service failure or high-frequency errors detected.",
                supporting_event_ids=[e["event_id"] for e in error_events[:3]] if error_events else []
            ))

    return SeverityDecision(
        severity=severity,
        customer_impact=customer_impact,
        payment_outcome=payment_outcome,
        score=score,
        reasons=reasons
    )
