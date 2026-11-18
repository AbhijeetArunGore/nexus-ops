"""
Log Normalization Engine (Module 2)
Parses heterogeneous log formats (JSON, JSONL, Java Log4j/Logback, Python stack traces, HTTP logs)
into a structured LogEvent schema. Includes multiline stack trace coalescing.
"""
import re
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from app.services.redaction import redact_text

# Common regex patterns for text logs
ISO_TIMESTAMP_PATTERN = re.compile(r'\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?')
LEVEL_PATTERN = re.compile(r'\b(CRITICAL|FATAL|ERROR|WARN|WARNING|INFO|DEBUG|TRACE)\b', re.IGNORECASE)
TRANSACTION_ID_PATTERN = re.compile(r'\b(?:SYN-)?TXN-[A-Za-z0-9\-_]+\b|\b(?:order|txn|trans)[_-]?id[:=\s]+([A-Za-z0-9\-_]+)', re.IGNORECASE)
TRACE_ID_PATTERN = re.compile(r'\btrace[_-]?id[:=\s]+([A-Za-z0-9\-]+)|\b[a-f0-9]{32}\b', re.IGNORECASE)
HTTP_STATUS_PATTERN = re.compile(r'\bHTTP[/12\.]*\s+([1-5]\d{2})\b|\bstatus[:=\s]+([1-5]\d{2})\b', re.IGNORECASE)
SERVICE_NAME_PATTERN = re.compile(r'\[([a-zA-Z0-9\-_]+(?:-service|-api|-orchestrator|-connector|-dispatcher|-engine)?)\]|\bservice[:=\s]+([a-zA-Z0-9\-_]+)', re.IGNORECASE)
ERROR_TYPE_PATTERN = re.compile(r'\b([A-Z][a-zA-Z0-9_]*(?:Exception|Error|Timeout|Exhaustion|Failure))\b')

# Continuation line indicators for multiline traces
STACK_TRACE_LINE_PATTERN = re.compile(r'^\s+(?:at\s+|File\s+|Caused by:|\.\.\.\s*\d+\s+more|\^|raise\s+)', re.IGNORECASE)


def parse_timestamp(ts_str: Optional[str]) -> Optional[datetime]:
    if not ts_str:
        return None
    try:
        clean = ts_str.strip().replace(" ", "T")
        if clean.endswith("Z"):
            clean = clean[:-1] + "+00:00"
        return datetime.fromisoformat(clean)
    except Exception:
        return None


def is_continuation_line(line: str) -> bool:
    """
    Determines if a line is a stack trace continuation of the previous log entry.
    """
    if not line:
        return False
    # If line starts with standard timestamp, it is a new log entry
    if ISO_TIMESTAMP_PATTERN.match(line):
        return False
    # If line starts with JSON object, it is a new entry
    if line.strip().startswith("{") and line.strip().endswith("}"):
        return False
    # Check for stack trace indentations or indicators
    if STACK_TRACE_LINE_PATTERN.match(line):
        return True
    if line.startswith("    ") or line.startswith("\t"):
        return True
    return False


def coalesce_multiline_logs(lines: List[str]) -> List[tuple[int, str]]:
    """
    Coalesces multiline stack traces into single logical log strings.
    Returns: list of (line_number, combined_log_string)
    """
    coalesced: List[tuple[int, str]] = []
    current_line_no = 1
    current_buffer: List[str] = []

    for idx, raw_line in enumerate(lines, start=1):
        stripped = raw_line.rstrip()
        if not stripped:
            continue

        if is_continuation_line(stripped) and current_buffer:
            # Append continuation line to current log entry
            current_buffer.append(stripped.strip())
        else:
            # Flush existing buffer
            if current_buffer:
                coalesced.append((current_line_no, "\n".join(current_buffer)))
            current_line_no = idx
            current_buffer = [stripped]

    # Flush last buffer
    if current_buffer:
        coalesced.append((current_line_no, "\n".join(current_buffer)))

    return coalesced


def normalize_log_line(raw_line: str, line_no: int, index: int) -> Dict[str, Any]:
    """
    Parses a single log entry into the standard LogEvent schema.
    """
    event_id = f"EVT-{index:04d}"
    line_clean = raw_line.strip()
    if not line_clean:
        return {}

    # 1. Attempt JSON parsing
    if line_clean.startswith("{") and line_clean.endswith("}"):
        try:
            data = json.loads(line_clean)
            msg = str(data.get("message") or data.get("msg") or data.get("log") or json.dumps(data))
            redacted_msg, was_redacted = redact_text(msg)

            ts_str = data.get("timestamp") or data.get("time") or data.get("@timestamp")
            parsed_ts = parse_timestamp(str(ts_str)) if ts_str else None

            status = data.get("http_status") or data.get("status_code") or data.get("status")
            try:
                status_int = int(status) if status is not None else None
            except Exception:
                status_int = None

            return {
                "event_id": event_id,
                "timestamp": parsed_ts,
                "service": str(data.get("service") or data.get("app") or "payment-api").lower(),
                "environment": "simulated",
                "log_level": str(data.get("level") or data.get("log_level") or "INFO").upper(),
                "message": redacted_msg,
                "error_type": data.get("error_type") or data.get("exception"),
                "trace_id": data.get("trace_id") or data.get("traceId"),
                "span_id": data.get("span_id") or data.get("spanId"),
                "transaction_id": data.get("transaction_id") or data.get("txn_id"),
                "endpoint": data.get("endpoint") or data.get("path") or data.get("url"),
                "http_status": status_int,
                "duration_ms": float(data.get("duration_ms") or data.get("latency_ms")) if (data.get("duration_ms") or data.get("latency_ms")) else None,
                "dependency": data.get("dependency") or data.get("target"),
                "redaction_applied": was_redacted,
                "line_number": line_no
            }
        except Exception:
            pass

    # 2. Text / Log4j / Syslog / Trace parsing
    redacted_msg, was_redacted = redact_text(line_clean)

    # Timestamp extraction
    ts_match = ISO_TIMESTAMP_PATTERN.search(line_clean)
    parsed_ts = parse_timestamp(ts_match.group(0)) if ts_match else None

    # Log Level extraction
    level_match = LEVEL_PATTERN.search(line_clean)
    log_level = level_match.group(1).upper() if level_match else "INFO"
    if log_level == "WARNING":
        log_level = "WARN"
    elif log_level == "FATAL":
        log_level = "CRITICAL"

    # Service extraction
    service = "payment-api"
    service_match = SERVICE_NAME_PATTERN.search(line_clean)
    if service_match:
        service = (service_match.group(1) or service_match.group(2) or "payment-api").lower()
    else:
        for s in ["payment-api", "payment-orchestrator", "bank-connector", "webhook-dispatcher", "settlement-engine", "order-db"]:
            if s in line_clean.lower():
                service = s
                break

    # Transaction ID
    txn_id = None
    txn_match = TRANSACTION_ID_PATTERN.search(line_clean)
    if txn_match:
        txn_id = txn_match.group(0) if txn_match.group(0).startswith("SYN-") or txn_match.group(0).startswith("TXN-") else txn_match.group(1)

    # Trace ID
    trace_id = None
    trace_match = TRACE_ID_PATTERN.search(line_clean)
    if trace_match:
        trace_id = trace_match.group(1) if trace_match.group(1) else trace_match.group(0)

    # HTTP Status
    http_status = None
    http_match = HTTP_STATUS_PATTERN.search(line_clean)
    if http_match:
        try:
            http_status = int(http_match.group(1) or http_match.group(2))
        except Exception:
            pass

    # Error Type
    error_type = None
    err_match = ERROR_TYPE_PATTERN.search(line_clean)
    if err_match:
        error_type = err_match.group(1)
    elif "nullpointerexception" in line_clean.lower():
        error_type = "NullPointerException"
    elif "timeout" in line_clean.lower():
        error_type = "TimeoutError"
    elif ("database" in line_clean.lower() or "pg_" in line_clean.lower() or "hikaripool" in line_clean.lower() or "postgres" in line_clean.lower() or "mysql" in line_clean.lower() or "order-db" in service or "connection slots" in line_clean.lower()) and ("connection" in line_clean.lower() or "slot" in line_clean.lower() or "pool" in line_clean.lower()):
        error_type = "DatabaseConnectionError"
    elif "webhook" in line_clean.lower() and ("refused" in line_clean.lower() or "failed" in line_clean.lower()):
        error_type = "WebhookDeliveryError"

    return {
        "event_id": event_id,
        "timestamp": parsed_ts,
        "service": service,
        "environment": "simulated",
        "log_level": log_level,
        "message": redacted_msg,
        "error_type": error_type,
        "trace_id": trace_id,
        "span_id": None,
        "transaction_id": txn_id,
        "endpoint": None,
        "http_status": http_status,
        "duration_ms": None,
        "dependency": None,
        "redaction_applied": was_redacted,
        "line_number": line_no
    }


def normalize_log_stream(content: str) -> List[Dict[str, Any]]:
    """
    Coalesces multiline traces and parses each entry into the normalized schema.
    """
    lines = content.splitlines()
    coalesced_entries = coalesce_multiline_logs(lines)
    events = []
    idx = 1
    for line_no, entry_text in coalesced_entries:
        parsed = normalize_log_line(entry_text, line_no, idx)
        if parsed:
            events.append(parsed)
            idx += 1
    return events
