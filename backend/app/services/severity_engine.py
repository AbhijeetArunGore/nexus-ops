"""
Deterministic Severity Engine (Module 9)
Evaluates an explainable 4-tier policy decision matrix (CRITICAL, HIGH, MEDIUM, LOW)
based on service criticality, error velocity, cascading depth, and payment state impact.
Severity is NEVER determined by an LLM.
"""
from typing import List, Dict, Any
from app.schemas.incident import SeverityDecision, SeverityRationaleItem
from app.services.topology import CRITICALITY_TIERS


def evaluate_severity(events: List[Dict[str, Any]], patterns: List[Dict[str, Any]], correlated_groups: List[Dict[str, Any]]) -> SeverityDecision:
    """
    Computes deterministic incident severity and customer impact status.
    """
    score = 0
    reasons: List[SeverityRationaleItem] = []
    customer_impact = "UNKNOWN"

    error_events = [e for e in events if e.get("log_level") in ["WARN", "ERROR", "CRITICAL"] or e.get("error_type")]
    failing_services = {e.get("service", "").lower() for e in error_events}

    # Business partner declines are functional rejections, not platform infrastructure outages
    business_rejection_keywords = ["insufficient", "declined", "card_expired", "invalid_cvv", "settlement_hold"]

    # Rule 1: Tier 1 Service Failure (Payment Core Outage - requires actual ERROR or CRITICAL level, not pure WARN or partner business decline)
    tier_1_failing = [
        s for s in failing_services
        if CRITICALITY_TIERS.get(s) == "TIER_1"
        and any(
            e.get("service") == s
            and e.get("log_level") in ["ERROR", "CRITICAL"]
            and not any(k in e.get("message", "").lower() for k in business_rejection_keywords)
            for e in error_events
        )
    ]
    if tier_1_failing:
        score += 40
        reasons.append(SeverityRationaleItem(
            rule="TIER_1_PAYMENT_SERVICE_IMPACT",
            weight="+40 pts",
            description=f"Critical payment processing service(s) degraded: {', '.join(tier_1_failing)}",
            supporting_event_ids=[e["event_id"] for e in error_events if e.get("service") in tier_1_failing][:6]
        ))

    # Rule 2: Confirmed Customer Impact (HTTP 5xx or Gateway Timeouts on Ingress)
    client_5xx = [
        e for e in error_events
        if e.get("service") in ["payment-api", "customer-checkout"]
        and (((e.get("http_status") or 0) >= 500) or "504" in e.get("message", "") or "500" in e.get("message", ""))
    ]
    if client_5xx:
        score += 35
        customer_impact = "CONFIRMED"
        reasons.append(SeverityRationaleItem(
            rule="CONFIRMED_CUSTOMER_PAYMENT_FAILURE",
            weight="+35 pts",
            description=f"Observed {len(client_5xx)} direct customer-facing HTTP 5xx errors or 504 timeouts on payment ingress.",
            supporting_event_ids=[e["event_id"] for e in client_5xx][:6]
        ))
    elif any(e.get("service") == "payment-api" for e in error_events):
        customer_impact = "SUSPECTED"

    # Rule 3: Cascading Multi-Service Correlation
    has_cascade = any(g.get("correlation_type") == "DEPENDENCY_CASCADE" for g in correlated_groups)
    infra_failing = [
        s for s in failing_services
        if any(
            e.get("service") == s
            and not any(k in e.get("message", "").lower() for k in business_rejection_keywords)
            for e in error_events
        )
    ]
    if has_cascade or len(infra_failing) >= 3:
        score += 25
        reasons.append(SeverityRationaleItem(
            rule="MULTI_SERVICE_CASCADING_FAILURE",
            weight="+25 pts",
            description=f"Error propagation spans multiple services across architecture ({len(infra_failing)} services affected).",
            supporting_event_ids=[e["event_id"] for e in error_events][:6]
        ))

    # Rule 4: High Error Velocity / Burst
    max_burst = max([p.get("occurrence_count", 0) for p in patterns], default=0)
    if max_burst >= 4:
        score += 20
        reasons.append(SeverityRationaleItem(
            rule="HIGH_FREQUENCY_ERROR_BURST",
            weight="+20 pts",
            description=f"Single error fingerprint burst triggered {max_burst} times.",
            supporting_event_ids=[e["event_id"] for e in error_events[:6]]
        ))

    # Rule 5: Database Connection Exhaustion (System-wide risk)
    db_exhaustion = any(
        e.get("error_type") == "DatabaseConnectionError"
        or ("pool" in e.get("message", "").lower() and e.get("service") in ["order-db", "payment-orchestrator"])
        or "connection slots" in e.get("message", "").lower()
        for e in error_events
    )
    if db_exhaustion:
        score += 30
        reasons.append(SeverityRationaleItem(
            rule="DATABASE_CONNECTION_EXHAUSTION",
            weight="+30 pts",
            description="Database connection pool saturation detected, risking system-wide deadlock.",
            supporting_event_ids=[e["event_id"] for e in error_events if e.get("error_type") == "DatabaseConnectionError" or "pool" in e.get("message", "").lower()][:6]
        ))

    # Rule 6: Settlement & UTR Reconciliation Discrepancy
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

    # Rule 7: Webhook / Batch Asynchronous Failures (Tier 2/3 only)
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

    # Rule 8: Refund Processing Hold
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

    # Map Score to Severity Tier
    if score >= 70:
        severity = "CRITICAL"
    elif score >= 40:
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
        score=score,
        reasons=reasons
    )
