"""
Log Normalization Engine (Module 2)
Parses heterogeneous log formats:
- Structured JSON and JSONL records
- Pretty-printed multiline JSON arrays
- RFC 4180 CSV logs with headers (timestamp, service, level, message, etc.)
- Java Log4j / Logback / Spring logs
- Python Tracebacks and multi-line exception blocks
- Syslog / Nginx access and error logs
- Generic application logs with service inference

Engineering Principles:
- Unknown logs never default to 'payment-api'. Service extraction follows strict precedence:
  1. JSON fields (service, app, logger, component, container_name)
  2. Bracketed service identifiers [service-name]
  3. Key-value service=X or app=X
  4. Java/Python logger namespaces (com.pinelabs.payments.X -> payments)
  5. Fallback to 'unknown-service'.
- Includes true CSV parsing and multiline JSON array parsing.
"""
import re
import json
import csv
import io
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Tuple
from app.services.redaction import redact_text

# Regex patterns for text logs
ISO_TIMESTAMP_PATTERN = re.compile(
    r'\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?'
)
SYSLOG_TIMESTAMP_PATTERN = re.compile(
    r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}\b',
    re.IGNORECASE
)
LEVEL_PATTERN = re.compile(
    r'\b(CRITICAL|FATAL|ERROR|WARN|WARNING|INFO|DEBUG|TRACE)\b',
    re.IGNORECASE
)
TRANSACTION_ID_PATTERN = re.compile(
    r'\b(?:SYN-)?TXN-[A-Za-z0-9\-_]+\b|\b(?:order|txn|trans)[_-]?id[:=\s]+([A-Za-z0-9\-_]+)',
    re.IGNORECASE
)
TRACE_ID_PATTERN = re.compile(
    r'\btrace[_-]?id[:=\s]+([A-Za-z0-9\-_]+)|\b(tr-[A-Za-z0-9\-_]+)\b|\b[a-f0-9]{32}\b',
    re.IGNORECASE
)
HTTP_STATUS_PATTERN = re.compile(
    r'\bHTTP[/12\.]*\s+([1-5]\d{2})\b|\bstatus[:=\s]+([1-5]\d{2})\b',
    re.IGNORECASE
)
SERVICE_NAME_PATTERN = re.compile(
    r'\[([a-zA-Z0-9\-_]+)\]|\b(?:service|app|component|container)[:=\s]+([a-zA-Z0-9\-_]+)',
    re.IGNORECASE
)
JAVA_LOGGER_PATTERN = re.compile(
    r'\b(?:com|org|io|net|in)\.([a-zA-Z0-9\-_]+)\.([a-zA-Z0-9\-_]+)\.([A-Z][a-zA-Z0-9]+)\b'
)
ERROR_TYPE_PATTERN = re.compile(
    r'\b([A-Z][a-zA-Z0-9_]*(?:Exception|Error|Timeout|Exhaustion|Failure))\b'
)
STACK_TRACE_LINE_PATTERN = re.compile(
    r'^\s+(?:at\s+|File\s+|Caused by:|\.\.\.\s*\d+\s+more|\^|raise\s+)',
    re.IGNORECASE
)


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
    """Determines if a line is a stack trace continuation of the previous log entry."""
    if not line:
        return False
    if ISO_TIMESTAMP_PATTERN.match(line):
        return False
    if line.strip().startswith("{") and line.strip().endswith("}"):
        return False
    if STACK_TRACE_LINE_PATTERN.match(line):
        return True
    if line.startswith("    ") or line.startswith("\t"):
        return True
    return False


def coalesce_multiline_logs(lines: List[str]) -> List[Tuple[int, str]]:
    """Coalesces multiline stack traces into single logical log strings."""
    coalesced: List[Tuple[int, str]] = []
    current_entry: List[str] = []
    current_line_no = 1

    for idx, raw_line in enumerate(lines, start=1):
        line = raw_line.rstrip()
        if not line:
            continue

        if is_continuation_line(line) and current_entry:
            current_entry.append(line)
        else:
            if current_entry:
                coalesced.append((current_line_no, "\n".join(current_entry)))
            current_entry = [line]
            current_line_no = idx

    if current_entry:
        coalesced.append((current_line_no, "\n".join(current_entry)))

    return coalesced


def try_parse_csv(content: str) -> Optional[List[Dict[str, Any]]]:
    """
    Attempts to parse content as RFC 4180 CSV with headers.
    Returns normalized event dicts if headers contain log signals.
    """
    try:
        sample = content[:4096]
        if "," not in sample and "\t" not in sample:
            return None

        reader = csv.DictReader(io.StringIO(content))
        if not reader.fieldnames:
            return None

        fields_lower = [f.lower().strip() for f in reader.fieldnames if f]
        has_log_fields = any(f in fields_lower for f in ["message", "msg", "log", "error", "level", "service"])
        if not has_log_fields:
            return None

        events = []
        for idx, row in enumerate(reader, start=2):
            msg_val = row.get("message") or row.get("msg") or row.get("log") or row.get("error") or str(row)
            redacted_msg, was_redacted = redact_text(msg_val)

            ts_raw = row.get("timestamp") or row.get("time") or row.get("date") or row.get("@timestamp")
            parsed_ts = parse_timestamp(ts_raw)

            svc_val = row.get("service") or row.get("app") or row.get("component") or "unknown-service"
            level_val = (row.get("level") or row.get("log_level") or "INFO").upper()
            if level_val == "WARNING":
                level_val = "WARN"

            status_raw = row.get("http_status") or row.get("status")
            status_int = int(status_raw) if status_raw and str(status_raw).isdigit() else None

            events.append({
                "event_id": f"EVT-{idx:04d}",
                "timestamp": parsed_ts,
                "service": str(svc_val).lower(),
                "environment": "simulated",
                "log_level": level_val,
                "message": redacted_msg,
                "error_type": row.get("error_type") or row.get("exception"),
                "trace_id": row.get("trace_id") or row.get("traceId"),
                "span_id": row.get("span_id"),
                "transaction_id": row.get("transaction_id") or row.get("txn_id"),
                "endpoint": row.get("endpoint") or row.get("path"),
                "http_status": status_int,
                "duration_ms": float(row["duration_ms"]) if row.get("duration_ms") and str(row.get("duration_ms")).replace('.', '', 1).isdigit() else None,
                "dependency": row.get("dependency"),
                "redaction_applied": was_redacted,
                "line_number": idx
            })
        return events if events else None
    except Exception:
        return None


def try_parse_json_array(content: str) -> Optional[List[Dict[str, Any]]]:
    """
    Attempts to parse entire content as a top-level JSON array of log objects.
    """
    clean = content.strip()
    if clean.startswith("[") and clean.endswith("]"):
        try:
            arr = json.loads(clean)
            if isinstance(arr, list) and arr and isinstance(arr[0], dict):
                events = []
                for idx, data in enumerate(arr, start=1):
                    msg = data.get("message") or data.get("msg") or data.get("log") or json.dumps(data)
                    redacted_msg, was_redacted = redact_text(msg)
                    ts_raw = data.get("timestamp") or data.get("time") or data.get("@timestamp")
                    parsed_ts = parse_timestamp(ts_raw)

                    svc = data.get("service") or data.get("app") or data.get("logger") or "unknown-service"
                    lvl = (data.get("level") or data.get("log_level") or "INFO").upper()
                    if lvl == "WARNING":
                        lvl = "WARN"

                    status = data.get("http_status") or data.get("status")
                    events.append({
                        "event_id": f"EVT-{idx:04d}",
                        "timestamp": parsed_ts,
                        "service": str(svc).lower(),
                        "environment": "simulated",
                        "log_level": lvl,
                        "message": redacted_msg,
                        "error_type": data.get("error_type") or data.get("exception"),
                        "trace_id": data.get("trace_id") or data.get("traceId"),
                        "span_id": data.get("span_id"),
                        "transaction_id": data.get("transaction_id") or data.get("txn_id"),
                        "endpoint": data.get("endpoint") or data.get("path"),
                        "http_status": int(status) if status and str(status).isdigit() else None,
                        "duration_ms": float(data.get("duration_ms") or data.get("latency_ms", 0)) if (data.get("duration_ms") or data.get("latency_ms")) else None,
                        "dependency": data.get("dependency"),
                        "redaction_applied": was_redacted,
                        "line_number": idx
                    })
                return events
        except Exception:
            return None
    return None


def normalize_log_line(line: str, line_no: int, event_idx: int) -> Dict[str, Any]:
    """
    Normalizes a single text log line, Syslog, or individual JSONL record.
    Never defaults service to 'payment-api' unless indicated by log evidence.
    """
    line_clean = line.strip()

    # 1. JSON / JSONL record parsing
    if line_clean.startswith("{") and line_clean.endswith("}"):
        try:
            data = json.loads(line_clean)
            msg = data.get("message") or data.get("msg") or data.get("log") or line_clean
            redacted_msg, was_redacted = redact_text(msg)

            ts_raw = data.get("timestamp") or data.get("time") or data.get("@timestamp")
            parsed_ts = parse_timestamp(ts_raw)

            status = data.get("http_status") or data.get("status")
            status_int = int(status) if status and str(status).isdigit() else None

            # Service inference precedence: service -> app -> component -> logger -> container -> unknown-service
            svc = data.get("service") or data.get("app") or data.get("component") or data.get("logger") or data.get("container") or "unknown-service"

            lvl = str(data.get("level") or data.get("log_level") or "INFO").upper()
            if lvl == "WARNING":
                lvl = "WARN"

            return {
                "event_id": f"EVT-{event_idx:04d}",
                "timestamp": parsed_ts,
                "service": str(svc).lower(),
                "environment": "simulated",
                "log_level": lvl,
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

    # Service extraction with strict precedence (Never default to payment-api)
    service = "unknown-service"
    service_match = SERVICE_NAME_PATTERN.search(line_clean)
    if service_match:
        service = (service_match.group(1) or service_match.group(2) or "unknown-service").lower()
    else:
        # Check Java logger pattern: com.pinelabs.service_name.Class
        java_match = JAVA_LOGGER_PATTERN.search(line_clean)
        if java_match:
            service = java_match.group(2).lower()
        else:
            # Check known synthetic service tokens if present explicitly
            for s in ["payment-api", "payment-orchestrator", "bank-connector", "webhook-dispatcher", "settlement-engine", "order-db", "customer-checkout", "deployment-manager"]:
                if s in line_clean.lower():
                    service = s
                    break

    # Transaction ID
    txn_match = TRANSACTION_ID_PATTERN.search(line_clean)
    transaction_id = txn_match.group(0) if txn_match else None
    if transaction_id and "=" in transaction_id:
        transaction_id = transaction_id.split("=")[-1].strip()

    # Trace ID
    trace_match = TRACE_ID_PATTERN.search(line_clean)
    trace_id = trace_match.group(1) or trace_match.group(2) if trace_match else None

    # HTTP Status
    status_match = HTTP_STATUS_PATTERN.search(line_clean)
    http_status = int(status_match.group(1) or status_match.group(2)) if status_match else None

    # Error type
    error_match = ERROR_TYPE_PATTERN.search(line_clean)
    error_type = error_match.group(1) if error_match else None

    return {
        "event_id": f"EVT-{event_idx:04d}",
        "timestamp": parsed_ts,
        "service": service,
        "environment": "simulated",
        "log_level": log_level,
        "message": redacted_msg,
        "error_type": error_type,
        "trace_id": trace_id,
        "span_id": None,
        "transaction_id": transaction_id,
        "endpoint": None,
        "http_status": http_status,
        "duration_ms": None,
        "dependency": None,
        "redaction_applied": was_redacted,
        "line_number": line_no
    }


def normalize_log_stream(raw_content: str) -> List[Dict[str, Any]]:
    """
    Master ingestion pipeline parsing raw content into normalized LogEvent dictionaries.
    Supports CSV, JSON arrays, and coalesced multiline text/JSONL.
    """
    if not raw_content or not raw_content.strip():
        return []

    # 1. Check for top-level JSON Array
    json_arr_events = try_parse_json_array(raw_content)
    if json_arr_events:
        return json_arr_events

    # 2. Check for CSV format
    csv_events = try_parse_csv(raw_content)
    if csv_events:
        return csv_events

    # 3. Standard text / multiline coalesced stream
    lines = raw_content.splitlines()
    coalesced = coalesce_multiline_logs(lines)

    events: List[Dict[str, Any]] = []
    for idx, (line_no, line_text) in enumerate(coalesced, start=1):
        evt = normalize_log_line(line_text, line_no=line_no, event_idx=idx)
        events.append(evt)

    return events
