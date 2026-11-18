"""
Alert Correlation Engine (Module 6)
Correlates multi-service errors into cohesive incident groups based on shared trace IDs,
shared transaction IDs, topological dependency relationships, and temporal proximity.
"""
from typing import List, Dict, Any, Set
from collections import defaultdict


def correlate_events(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Evaluates evidence to group discrete events into correlated causal or relational clusters.
    Prioritizes strong deterministic identifiers over weak temporal coincidences.
    """
    correlated_groups: List[Dict[str, Any]] = []
    error_events = [e for e in events if e.get("log_level") in ["WARN", "ERROR", "CRITICAL"] or e.get("error_type")]

    # 1. Correlate by Shared Transaction ID (Strength: HIGH)
    txn_map: Dict[str, List[str]] = defaultdict(list)
    for e in error_events:
        txn_id = e.get("transaction_id")
        if txn_id:
            txn_map[txn_id].append(e["event_id"])

    for txn_id, event_ids in txn_map.items():
        if len(event_ids) > 1:
            correlated_groups.append({
                "correlation_type": "SHARED_TRANSACTION",
                "strength": "HIGH",
                "rationale": f"Events share identical transaction identifier: '{txn_id}'. Failures belong to the same payment request lifecycle.",
                "event_ids": event_ids
            })

    # 2. Correlate by Shared Trace ID (Strength: HIGH)
    trace_map: Dict[str, List[str]] = defaultdict(list)
    for e in error_events:
        trace_id = e.get("trace_id")
        if trace_id:
            trace_map[trace_id].append(e["event_id"])

    for trace_id, event_ids in trace_map.items():
        if len(event_ids) > 1:
            # Check if not already covered by transaction group
            correlated_groups.append({
                "correlation_type": "SHARED_TRACE",
                "strength": "HIGH",
                "rationale": f"Events share distributed trace context '{trace_id}' traversing service boundaries.",
                "event_ids": event_ids
            })

    # 3. Correlate by Dependency Cascade (Strength: MEDIUM)
    # E.g. If bank-connector fails with timeouts and payment-api shows timeouts, group them as cascade
    failing_services: Set[str] = {e.get("service") for e in error_events}
    if "bank-connector" in failing_services and "payment-api" in failing_services:
        has_api_timeout = any(
            "timeout" in e.get("message", "").lower()
            or "504" in e.get("message", "")
            or ((e.get("http_status") or 0) >= 500)
            for e in error_events if e.get("service") == "payment-api"
        )
        if has_api_timeout:
            cascade_events = [e["event_id"] for e in error_events if e.get("service") in ["bank-connector", "payment-api"]]
            correlated_groups.append({
                "correlation_type": "DEPENDENCY_CASCADE",
                "strength": "MEDIUM",
                "rationale": "Upstream bank-connector degradation propagating timeout cascades to client-facing payment-api.",
                "event_ids": cascade_events[:12]
            })
    elif "order-db" in failing_services and "payment-orchestrator" in failing_services:
        cascade_events = [e["event_id"] for e in error_events if e.get("service") in ["order-db", "payment-orchestrator"]]
        correlated_groups.append({
            "correlation_type": "DEPENDENCY_CASCADE",
            "strength": "MEDIUM",
            "rationale": "Database connection saturation propagating transaction abortion cascades into payment-orchestrator.",
            "event_ids": cascade_events[:12]
        })

    # 4. Temporal Proximity Correlation (Strength: LOW)
    # If no groups were formed and errors exist in a tight window (< 30 seconds)
    if not correlated_groups and len(error_events) >= 2:
        timed_events = [e for e in error_events if e.get("timestamp")]
        if len(timed_events) >= 2:
            timed_events.sort(key=lambda x: x["timestamp"])
            delta = (timed_events[-1]["timestamp"] - timed_events[0]["timestamp"]).total_seconds()
            if delta <= 60:
                correlated_groups.append({
                    "correlation_type": "TEMPORAL_WINDOW",
                    "strength": "LOW",
                    "rationale": f"Errors occurred within a compact temporal window of {int(delta)}s. Inferred potential shared trigger.",
                    "event_ids": [e["event_id"] for e in timed_events]
                })

    return correlated_groups
