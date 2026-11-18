"""
'What Am I Missing?' Adversarial Investigation Assistant (Module 12)
Executes a second-pass analysis to challenge initial diagnostic assumptions,
uncover unexamined patterns, identify missing telemetry, and formulate alternative hypotheses.
"""
from typing import List, Dict, Any
from app.schemas.incident import WhatAmIMissingResponse, WhatAmIMissingItem


def analyze_what_am_i_missing(
    incident_id: str,
    events: List[Dict[str, Any]],
    patterns: List[Dict[str, Any]],
    hypotheses: List[Dict[str, Any]]
) -> WhatAmIMissingResponse:
    """
    Evaluates forensic gaps and blindspots in current incident telemetry.
    """
    gaps: List[WhatAmIMissingItem] = []
    alternatives: List[str] = []
    blindspots: List[str] = []

    # 1. Check for Missing Distributed Tracing
    events_with_trace = [e for e in events if e.get("trace_id")]
    trace_coverage = len(events_with_trace) / max(len(events), 1)
    if trace_coverage < 0.5:
        gaps.append(WhatAmIMissingItem(
            category="OBSERVABILITY_BLINDSPOT",
            description=f"Trace ID coverage is only {int(trace_coverage * 100)}%. Cross-service request journey cannot be definitively confirmed without distributed context.",
            risk_level="HIGH",
            recommended_check="Inspect OpenTelemetry W3C traceparent propagation in API gateway headers."
        ))
        blindspots.append("Uninstrumented microservice hops between Payment Gateway and Core Banking.")

    # 2. Check for Unknown Payment State (Ambiguous Transaction Settlement)
    has_timeouts = any("timeout" in e.get("message", "").lower() for e in events)
    has_delayed_auth = any("auth" in e.get("message", "").lower() and "success" in e.get("message", "").lower() for e in events)
    if has_timeouts and not has_delayed_auth:
        gaps.append(WhatAmIMissingItem(
            category="PAYMENT_LIFECYCLE_AMBIGUITY",
            description="Upstream returned 504 Gateway Timeout, but payment processing status at acquiring bank is unknown. Customer may have been debited.",
            risk_level="CRITICAL",
            recommended_check="Execute out-of-band payment status inquiry API before advising merchant to re-attempt order."
        ))
        alternatives.append("Bank authorization may have succeeded asynchronously despite network gateway timeout.")

    # 3. Check for Database Connection Saturation vs Slow Queries
    has_db_errors = any("pool" in e.get("message", "").lower() for e in events)
    if has_db_errors:
        gaps.append(WhatAmIMissingItem(
            category="RESOURCE_SATURATION_ANALYSIS",
            description="Database connection exhaustion was detected, but connection holding duration and slow query logs are absent from ingested logs.",
            risk_level="HIGH",
            recommended_check="Inspect pg_stat_activity for unindexed sequential scans or uncommitted long-running transactions."
        ))
        alternatives.append("Connection pool exhaustion may be triggered by downstream network latency keeping connections open rather than direct database lockup.")

    # 4. Check for Webhook Signature & Merchant Reachability
    has_webhook_err = any("webhook" in e.get("service", "").lower() for e in events)
    if has_webhook_err:
        gaps.append(WhatAmIMissingItem(
            category="PARTNER_DEPENDENCY_VERIFICATION",
            description="Webhook dispatcher recorded HTTP failures. Unable to verify whether failure is due to merchant TLS handshake, DNS resolution, or payload validation failure.",
            risk_level="MEDIUM",
            recommended_check="Inspect merchant endpoint TLS negotiation logs and HTTP response bodies for 401/403 or 502 Bad Gateway."
        ))

    # 5. Check for Unverified System Recovery
    last_event = events[-1] if events else {}
    if last_event.get("log_level") in ["ERROR", "CRITICAL"]:
        gaps.append(WhatAmIMissingItem(
            category="RECOVERY_VERIFICATION_GAP",
            description="The final log entry in the dataset is an error. No synthetic healthcheck probes or successful transactions have confirmed service restoration.",
            risk_level="HIGH",
            recommended_check="Run synthetic canary transactions through payment-api to verify end-to-end recovery."
        ))
        blindspots.append("Active outage duration is unconfirmed; system may still be dropping live payments.")

    if not alternatives:
        alternatives.append("Transient upstream partner network blip rather than permanent hardware degradation.")

    return WhatAmIMissingResponse(
        incident_id=incident_id,
        gaps_identified=gaps,
        alternative_hypotheses=alternatives,
        telemetry_blindspots=blindspots
    )
