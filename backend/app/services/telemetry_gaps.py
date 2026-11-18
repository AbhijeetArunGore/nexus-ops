"""
Telemetry Gap Detector (Module 18)
Identifies observability blindspots in ingested logs and generates actionable
OpenTelemetry / SRE instrumentation improvements to improve future incident investigations.
"""
from typing import List, Dict, Any
from app.schemas.incident import TelemetryGapItem


def detect_telemetry_gaps(events: List[Dict[str, Any]]) -> List[TelemetryGapItem]:
    """
    Evaluates telemetry quality against production SRE observability standards.
    """
    gaps: List[TelemetryGapItem] = []

    # 1. Trace ID Propagation
    missing_trace = [e for e in events if not e.get("trace_id")]
    if len(missing_trace) > len(events) * 0.3:
        gaps.append(TelemetryGapItem(
            missing_signal="Distributed W3C Trace Context (trace_id / span_id)",
            affected_service="Cross-Service Payment Pipeline",
            operational_impact="Inability to correlate single customer order across Payment API, Orchestrator, and Bank Connector.",
            instrumentation_fix="Inject OpenTelemetry TracerProvider with traceparent header propagation across HTTP & gRPC clients.",
            priority="HIGH"
        ))

    # 2. Duration / Latency Metrics
    events_with_duration = [e for e in events if e.get("duration_ms") is not None]
    if len(events_with_duration) < len(events) * 0.2:
        gaps.append(TelemetryGapItem(
            missing_signal="Explicit Execution Latency (duration_ms)",
            affected_service="payment-api / bank-connector",
            operational_impact="Cannot distinguish slow database queries from external network socket timeouts.",
            instrumentation_fix="Emit Prometheus histogram `payment_request_duration_seconds{service, endpoint, status}` on all inbound and outbound endpoints.",
            priority="HIGH"
        ))

    # 3. Payment State Transition Logging
    has_state_changes = any("state" in e.get("message", "").lower() or "status" in e.get("message", "").lower() for e in events)
    if not has_state_changes:
        gaps.append(TelemetryGapItem(
            missing_signal="Finite State Machine (FSM) Transition Events",
            affected_service="payment-orchestrator",
            operational_impact="Hard to determine if transaction aborted before or after acquiring bank debit.",
            instrumentation_fix="Emit structured event `payment_state_transition` with `previous_state`, `target_state`, and `order_id` on every FSM change.",
            priority="MEDIUM"
        ))

    # 4. Database Connection Pool Metrics
    has_db = any("db" in e.get("service", "").lower() or "pool" in e.get("message", "").lower() for e in events)
    if has_db:
        gaps.append(TelemetryGapItem(
            missing_signal="HikariCP / SQLAlchemy Connection Pool Gauge Metrics",
            affected_service="order-db / payment-orchestrator",
            operational_impact="Engineers cannot detect gradual connection leaks before total pool exhaustion occurs.",
            instrumentation_fix="Export `db_pool_active_connections`, `db_pool_idle_connections`, and `db_pool_wait_duration_ms` to Prometheus.",
            priority="HIGH"
        ))

    # 5. Outbound Partner Response Payload Snippets
    has_partner_err = any("bank" in e.get("service", "").lower() for e in events)
    if has_partner_err:
        gaps.append(TelemetryGapItem(
            missing_signal="Partner Gateway Response Code & Raw ISO8583 Field 39",
            affected_service="bank-connector",
            operational_impact="Operations cannot verify if failure is due to bank decline (insufficient funds) or partner technical outage.",
            instrumentation_fix="Log sanitized partner response error code (`bank_response_code`) on all non-200 responses.",
            priority="MEDIUM"
        ))

    return gaps
