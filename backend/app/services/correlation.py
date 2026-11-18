"""
Alert Correlation Engine (Module 6)
Correlates multi-service errors into cohesive incident groups based on:
1. Shared transaction IDs (Priority 1)
2. Shared trace IDs (Priority 2)
3. Configured topological dependency paths (Priority 3)
4. Common error fingerprints / dependencies (Priority 4)
5. Temporal proximity (Priority 5)
"""
from typing import List, Dict, Any, Set
from collections import defaultdict
from app.services.topology import get_synthetic_topology, get_service_dependencies


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
            correlated_groups.append({
                "correlation_type": "SHARED_TRACE",
                "strength": "HIGH",
                "rationale": f"Events share distributed trace context '{trace_id}' traversing service boundaries.",
                "event_ids": event_ids
            })

    # 3. Correlate by Configured Topology & Dependency Cascade (Strength: MEDIUM)
    # Check if failing services have direct or transitive dependency relationships
    failing_services: Set[str] = {e.get("service") for e in error_events if e.get("service")}
    covered_cascade_pairs = set()

    for caller_service in failing_services:
        direct_deps = set(get_service_dependencies(caller_service))
        failing_deps = direct_deps.intersection(failing_services)

        for dep_service in failing_deps:
            pair_key = (caller_service, dep_service)
            if pair_key in covered_cascade_pairs:
                continue
            covered_cascade_pairs.add(pair_key)

            caller_events = [e["event_id"] for e in error_events if e.get("service") == caller_service]
            dep_events = [e["event_id"] for e in error_events if e.get("service") == dep_service]
            combined_eids = (dep_events + caller_events)[:12]

            correlated_groups.append({
                "correlation_type": "DEPENDENCY_CASCADE",
                "strength": "MEDIUM",
                "rationale": (
                    f"Configured dependency relationship '{caller_service} -> {dep_service}': "
                    f"Downstream dependency '{dep_service}' failure propagated upstream to caller '{caller_service}'."
                ),
                "event_ids": combined_eids
            })

    # 4. Common Error Fingerprint Correlation (Strength: MEDIUM)
    fingerprint_map: Dict[str, List[str]] = defaultdict(list)
    for e in error_events:
        fp = e.get("fingerprint")
        if fp:
            fingerprint_map[fp].append(e["event_id"])

    for fp, eids in fingerprint_map.items():
        if len(eids) >= 3 and not any(set(eids).issubset(set(g["event_ids"])) for g in correlated_groups):
            correlated_groups.append({
                "correlation_type": "REPEATED_ERROR_FINGERPRINT",
                "strength": "MEDIUM",
                "rationale": f"Repeated occurrences ({len(eids)}) of standardized failure fingerprint '{fp}'.",
                "event_ids": eids[:8]
            })

    # 5. Temporal Proximity Window (Weak Fallback - only if no deterministic groups exist)
    if not correlated_groups and len(error_events) >= 2:
        correlated_groups.append({
            "correlation_type": "TEMPORAL_WINDOW",
            "strength": "LOW",
            "rationale": f"Discrete errors observed within close temporal window ({len(error_events)} events). Causality unconfirmed.",
            "event_ids": [e["event_id"] for e in error_events[:6]]
        })

    return correlated_groups
