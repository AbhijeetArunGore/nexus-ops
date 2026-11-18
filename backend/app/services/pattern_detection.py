"""
Pattern & Burst Detection Engine (Module 5)
Analyzes telemetry for operational failure patterns: bursts, cascades, timeouts,
database connection exhaustion, webhook retries, and high-frequency spikes.
"""
from typing import List, Dict, Any


def detect_operational_patterns(events: List[Dict[str, Any]], patterns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Evaluates rule-based failure patterns across normalized events and clusters.
    """
    detected_patterns: List[Dict[str, Any]] = []

    # 1. Database Connection Pool Exhaustion
    db_events = [
        e for e in events
        if "pool" in e.get("message", "").lower()
        or "connection refused" in e.get("message", "").lower()
        or "remaining connection slots" in e.get("message", "").lower()
        or e.get("error_type") == "DatabaseConnectionError"
    ]
    if len(db_events) >= 2:
        detected_patterns.append({
            "pattern_type": "DATABASE_CONNECTION_EXHAUSTION",
            "severity_weight": "HIGH",
            "title": "Database Connection Pool Exhaustion Detected",
            "description": f"Observed {len(db_events)} database connection acquisition failures or timeouts.",
            "event_ids": [e["event_id"] for e in db_events[:10]]
        })

    # 2. Timeout Bursts (HTTP 504 / Network Timeouts)
    timeout_events = [
        e for e in events
        if e.get("http_status") in [504, 408]
        or "timeout" in e.get("message", "").lower()
        or e.get("error_type") == "TimeoutError"
    ]
    if len(timeout_events) >= 2:
        detected_patterns.append({
            "pattern_type": "TIMEOUT_BURST",
            "severity_weight": "HIGH",
            "title": "Payment Timeout Burst Detected",
            "description": f"Identified {len(timeout_events)} request/dependency timeouts indicating downstream latency or unavailability.",
            "event_ids": [e["event_id"] for e in timeout_events[:10]]
        })

    # 3. HTTP 5xx Server Error Surge
    server_error_events = [
        e for e in events
        if e.get("http_status") and 500 <= e.get("http_status") <= 503
    ]
    if len(server_error_events) >= 3:
        detected_patterns.append({
            "pattern_type": "HTTP_5XX_SURGE",
            "severity_weight": "HIGH",
            "title": "HTTP 5xx Server Error Spike",
            "description": f"Encountered {len(server_error_events)} internal server errors (500/502/503).",
            "event_ids": [e["event_id"] for e in server_error_events[:10]]
        })

    # 4. Webhook Delivery Failures & Retries
    webhook_events = [
        e for e in events
        if "webhook" in e.get("service", "").lower() or "webhook" in e.get("message", "").lower()
        if e.get("log_level") in ["WARN", "ERROR", "CRITICAL"]
    ]
    if len(webhook_events) >= 2:
        has_retries = any("retry" in e.get("message", "").lower() for e in webhook_events)
        detected_patterns.append({
            "pattern_type": "WEBHOOK_DELIVERY_FAILURE",
            "severity_weight": "MEDIUM",
            "title": "Merchant Webhook Dispatch Failure",
            "description": f"Observed {len(webhook_events)} webhook transmission errors {'with retry attempts' if has_retries else ''}.",
            "event_ids": [e["event_id"] for e in webhook_events[:10]]
        })

    # 5. Duplicate Events / Idempotency Violations
    duplicate_events = [
        e for e in events
        if "duplicate" in e.get("message", "").lower()
        or "idempotency" in e.get("message", "").lower()
        or "already processed" in e.get("message", "").lower()
    ]
    if duplicate_events:
        detected_patterns.append({
            "pattern_type": "DUPLICATE_EVENT_BURST",
            "severity_weight": "MEDIUM",
            "title": "Duplicate Notification / Idempotency Warning",
            "description": f"Detected {len(duplicate_events)} duplicate event arrivals or idempotency key collisions.",
            "event_ids": [e["event_id"] for e in duplicate_events[:10]]
        })

    # 6. High-Frequency Burst (Single Fingerprint > 4 occurrences)
    for p in patterns:
        if p["occurrence_count"] >= 4:
            detected_patterns.append({
                "pattern_type": "ERROR_BURST",
                "severity_weight": "HIGH",
                "title": f"High-Frequency Error Burst on {p['service']}",
                "description": f"Fingerprint {p['fingerprint']} triggered {p['occurrence_count']} times across {p['service']}.",
                "event_ids": p.get("sample_event_ids", [])
            })

    return detected_patterns
