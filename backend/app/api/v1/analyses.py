"""
Log Ingestion & Analysis Router (Module 1)
Supports multi-format log upload and paste processing through the deterministic pipeline.
Includes strict binary execution prevention and file-size constraints.
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timezone
import uuid

from app.core.database import get_db
from app.core.config import settings
from app.models.incident import Incident, LogEvent, ErrorPattern, CorrelatedGroup
from app.services.normalizer import normalize_log_stream
from app.services.fingerprinting import cluster_error_patterns
from app.services.pattern_detection import detect_operational_patterns
from app.services.correlation import correlate_events
from app.services.severity_engine import evaluate_severity
from app.schemas.incident import IngestionPasteRequest, IncidentSummaryResponse

router = APIRouter(prefix="/analyses", tags=["Ingestion & Analysis"])

# Forbidden binary executable magic byte signatures
FORBIDDEN_MAGIC_BYTES = [
    b"MZ",              # Windows PE executable / DLL
    b"\x7fELF",         # Linux ELF executable
    b"\xca\xfe\xba\xbe", # Java bytecode class
    b"\xfe\xed\xfa\xce", # Mach-O binary
    b"\xfe\xed\xfa\xcf", # Mach-O 64-bit binary
    b"\xce\xfa\xed\xfe", # Mach-O binary (reverse)
    b"\xcf\xfa\xed\xfe", # Mach-O 64-bit binary (reverse)
]


def validate_not_executable(raw_bytes: bytes):
    """
    Guards against executable file uploads by inspecting leading magic bytes.
    """
    for magic in FORBIDDEN_MAGIC_BYTES:
        if raw_bytes.startswith(magic):
            raise HTTPException(
                status_code=400,
                detail="Security rejection: Uploaded file contains executable binary magic bytes (PE/ELF/Mach-O/Class)."
            )


def process_and_create_incident(content: str, title: str, db: Session, scenario_name: Optional[str] = None) -> Incident:
    """
    Executes the deterministic ingestion pipeline:
    Validation -> Normalization -> Redaction -> Fingerprinting -> Pattern Detection -> Correlation -> Severity -> Persistence.
    """
    clean_content = content.strip()
    if not clean_content:
        raise HTTPException(status_code=400, detail="Input log payload is empty.")

    if len(clean_content.encode("utf-8")) > settings.MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(status_code=400, detail=f"Payload exceeds maximum permitted size of {settings.MAX_UPLOAD_SIZE_BYTES // (1024*1024)}MB.")

    # 1. Normalize and Redact (includes multiline coalescing)
    normalized_events = normalize_log_stream(clean_content)
    if not normalized_events:
        raise HTTPException(status_code=400, detail="No valid log entries could be extracted from input.")

    if len(normalized_events) > settings.MAX_LOG_LINES:
        normalized_events = normalized_events[:settings.MAX_LOG_LINES]

    # 2. Cluster Error Patterns
    error_patterns = cluster_error_patterns(normalized_events)

    # 3. Detect Failure Patterns
    detected_patterns = detect_operational_patterns(normalized_events, error_patterns)

    # 4. Correlate Alerts
    correlated_groups = correlate_events(normalized_events)

    # 5. Deterministic Severity Evaluation
    severity_decision = evaluate_severity(normalized_events, error_patterns, correlated_groups)

    # 6. Create Incident Record
    incident_count = db.query(Incident).count() + 1
    incident_number = f"INC-2026-{incident_count:04d}"

    incident = Incident(
        id=str(uuid.uuid4()),
        incident_number=incident_number,
        title=title or f"Payment Telemetry Incident {incident_number}",
        severity=severity_decision.severity,
        status="OPEN",
        customer_impact=severity_decision.customer_impact,
        payment_outcome=severity_decision.payment_outcome,
        source_scenario=scenario_name,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        severity_rationale=[r.model_dump() for r in severity_decision.reasons]
    )
    db.add(incident)
    db.flush()

    # 7. Persist Events
    for e in normalized_events:
        event_model = LogEvent(
            id=str(uuid.uuid4()),
            incident_id=incident.id,
            event_id=e["event_id"],
            timestamp=e["timestamp"],
            service=e["service"],
            environment=e["environment"],
            log_level=e["log_level"],
            message=e["message"],
            error_type=e.get("error_type"),
            trace_id=e.get("trace_id"),
            span_id=e.get("span_id"),
            transaction_id=e.get("transaction_id"),
            endpoint=e.get("endpoint"),
            http_status=e.get("http_status"),
            duration_ms=e.get("duration_ms"),
            dependency=e.get("dependency"),
            fingerprint=e.get("fingerprint"),
            redaction_applied=e.get("redaction_applied", False),
            line_number=e.get("line_number", 1)
        )
        db.add(event_model)

    # 8. Persist Error Patterns
    for p in error_patterns:
        pat_model = ErrorPattern(
            id=str(uuid.uuid4()),
            incident_id=incident.id,
            fingerprint=p["fingerprint"],
            service=p["service"],
            error_type=p.get("error_type"),
            pattern_template=p["pattern_template"],
            occurrence_count=p["occurrence_count"],
            first_seen=p.get("first_seen"),
            last_seen=p.get("last_seen"),
            sample_event_ids=p.get("sample_event_ids", [])
        )
        db.add(pat_model)

    # 9. Persist Correlated Groups
    for c in correlated_groups:
        corr_model = CorrelatedGroup(
            id=str(uuid.uuid4()),
            incident_id=incident.id,
            correlation_type=c["correlation_type"],
            strength=c["strength"],
            rationale=c["rationale"],
            event_ids=c["event_ids"]
        )
        db.add(corr_model)

    db.commit()
    db.refresh(incident)
    return incident


@router.post("/paste", response_model=IncidentSummaryResponse)
def paste_logs(payload: IngestionPasteRequest, db: Session = Depends(get_db)):
    """
    Ingests raw copied/pasted text logs.
    """
    title = payload.title or "Pasted Telemetry Log Analysis"
    incident = process_and_create_incident(payload.content, title, db)

    total_events = len(incident.events)
    total_errors = sum(1 for e in incident.events if e.log_level in ["WARN", "ERROR", "CRITICAL"] or e.error_type)
    affected_services = sorted(list({e.service for e in incident.events}))

    return IncidentSummaryResponse(
        id=incident.id,
        incident_number=incident.incident_number,
        title=incident.title,
        severity=incident.severity,
        status=incident.status,
        customer_impact=incident.customer_impact,
        payment_outcome=incident.payment_outcome or "UNKNOWN",
        source_scenario=incident.source_scenario,
        created_at=incident.created_at,
        updated_at=incident.updated_at,
        resolved_at=incident.resolved_at,
        summary=incident.summary,
        severity_rationale={"reasons": incident.severity_rationale},
        total_events=total_events,
        total_errors=total_errors,
        affected_services=affected_services
    )


@router.post("/upload", response_model=IncidentSummaryResponse)
async def upload_log_file(file: UploadFile = File(...), title: Optional[str] = Form(None), db: Session = Depends(get_db)):
    """
    Ingests uploaded log file (.log, .txt, .json, .jsonl, .csv).
    Validates magic bytes to prevent binary executable uploads.
    """
    # 1. Read first chunk for magic bytes validation
    chunk = await file.read(512)
    if not chunk or len(chunk.strip()) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    validate_not_executable(chunk)

    # 2. Extension validation
    allowed_extensions = (".log", ".txt", ".json", ".jsonl", ".csv")
    filename = (file.filename or "").lower()
    if not any(filename.endswith(ext) for ext in allowed_extensions):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '{file.filename}'. Permitted formats: .log, .txt, .json, .jsonl, .csv"
        )

    # 3. Stream remaining content with bounded size enforcement
    max_size = settings.MAX_UPLOAD_SIZE_BYTES
    bytes_read = len(chunk)
    chunks = [chunk]

    while True:
        more = await file.read(64 * 1024)
        if not more:
            break
        bytes_read += len(more)
        if bytes_read > max_size:
            raise HTTPException(
                status_code=400,
                detail=f"Payload exceeds maximum permitted size of {max_size // (1024*1024)}MB."
            )
        chunks.append(more)

    raw_bytes = b"".join(chunks)

    # 3. Decode UTF-8
    try:
        content = raw_bytes.decode("utf-8", errors="replace")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Encoding error: unable to decode UTF-8 stream: {str(e)}")

    incident_title = title or f"Analysis of {file.filename}"
    incident = process_and_create_incident(content, incident_title, db)

    total_events = len(incident.events)
    total_errors = sum(1 for e in incident.events if e.log_level in ["WARN", "ERROR", "CRITICAL"] or e.error_type)
    affected_services = sorted(list({e.service for e in incident.events}))

    return IncidentSummaryResponse(
        id=incident.id,
        incident_number=incident.incident_number,
        title=incident.title,
        severity=incident.severity,
        status=incident.status,
        customer_impact=incident.customer_impact,
        payment_outcome=incident.payment_outcome or "UNKNOWN",
        source_scenario=incident.source_scenario,
        created_at=incident.created_at,
        updated_at=incident.updated_at,
        resolved_at=incident.resolved_at,
        summary=incident.summary,
        severity_rationale={"reasons": incident.severity_rationale},
        total_events=total_events,
        total_errors=total_errors,
        affected_services=affected_services
    )
