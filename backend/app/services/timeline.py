"""
Incident Timeline Reconstruction Engine (Module 7)
Reconstructs the chronological event timeline and explicitly tags milestone events:
- First Observed Event
- Earliest Known Underlying Cause
- First Confirmed Customer Impact
- Recovery Confirmation Signals
"""
from typing import List, Dict, Any
from datetime import datetime


def reconstruct_timeline(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Sorts events and extracts timeline milestones.
    """
    # Sort events by timestamp or line_number
    sorted_events = sorted(
        events,
        key=lambda x: (x.get("timestamp") or datetime.min, x.get("line_number", 0))
    )

    first_observed = sorted_events[0] if sorted_events else None
    earliest_underlying = None
    first_customer_impact = None
    recovery_signal = None

    # Identify earliest underlying error in backend services (order-db, bank-connector, message-queue)
    for evt in sorted_events:
        if evt.get("service") in ["order-db", "bank-connector", "message-queue"] and evt.get("log_level") in ["ERROR", "CRITICAL"]:
            earliest_underlying = evt
            break

    # If none found, earliest underlying is the first error event
    if not earliest_underlying:
        for evt in sorted_events:
            if evt.get("log_level") in ["WARN", "ERROR", "CRITICAL"]:
                earliest_underlying = evt
                break

    # Identify first customer impact (payment-api or customer-checkout receiving 5xx or timeout)
    for evt in sorted_events:
        if evt.get("service") in ["payment-api", "customer-checkout"] and (evt.get("http_status", 0) >= 500 or "timeout" in evt.get("message", "").lower()):
            first_customer_impact = evt
            break

    # Identify recovery signal (HTTP 200 after errors, or 'recovered', 'healthy', 'reconnected')
    for evt in reversed(sorted_events):
        msg = evt.get("message", "").lower()
        if "recovered" in msg or "healthy" in msg or "reconnected" in msg or "pool restored" in msg or (evt.get("http_status") == 200 and "success" in msg):
            recovery_signal = evt
            break

    timeline_items = []
    for evt in sorted_events:
        tags = []
        if first_observed and evt["event_id"] == first_observed["event_id"]:
            tags.append("FIRST_OBSERVED_EVENT")
        if earliest_underlying and evt["event_id"] == earliest_underlying["event_id"]:
            tags.append("EARLIEST_UNDERLYING_EVENT")
        if first_customer_impact and evt["event_id"] == first_customer_impact["event_id"]:
            tags.append("FIRST_CUSTOMER_IMPACT")
        if recovery_signal and evt["event_id"] == recovery_signal["event_id"]:
            tags.append("RECOVERY_CONFIRMATION")

        timeline_items.append({
            "event_id": evt["event_id"],
            "timestamp": evt.get("timestamp"),
            "service": evt.get("service"),
            "log_level": evt.get("log_level"),
            "message": evt.get("message"),
            "http_status": evt.get("http_status"),
            "tags": tags
        })

    return {
        "milestones": {
            "first_observed": first_observed["event_id"] if first_observed else None,
            "earliest_underlying": earliest_underlying["event_id"] if earliest_underlying else None,
            "first_customer_impact": first_customer_impact["event_id"] if first_customer_impact else None,
            "recovery_signal": recovery_signal["event_id"] if recovery_signal else None,
        },
        "items": timeline_items
    }
