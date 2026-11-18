"""
SQLAlchemy models for NEXUS Ops
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base


def get_utc_now():
    return datetime.now(timezone.utc)


class Incident(Base):
    __tablename__ = "incidents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_number = Column(String(50), unique=True, nullable=False, index=True)
    title = Column(String(255), nullable=False)
    severity = Column(String(20), nullable=False, default="MEDIUM", index=True)  # CRITICAL, HIGH, MEDIUM, LOW
    status = Column(String(20), nullable=False, default="OPEN", index=True)  # OPEN, INVESTIGATING, MITIGATED, RESOLVED, CLOSED
    customer_impact = Column(String(20), nullable=False, default="UNKNOWN")  # CONFIRMED, SUSPECTED, UNKNOWN
    source_scenario = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=get_utc_now)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now)
    resolved_at = Column(DateTime, nullable=True)
    summary = Column(Text, nullable=True)
    severity_rationale = Column(JSON, nullable=True)

    # Relationships
    events = relationship("LogEvent", back_populates="incident", cascade="all, delete-orphan")
    patterns = relationship("ErrorPattern", back_populates="incident", cascade="all, delete-orphan")
    correlated_groups = relationship("CorrelatedGroup", back_populates="incident", cascade="all, delete-orphan")
    evidence_records = relationship("EvidenceRecord", back_populates="incident", cascade="all, delete-orphan")
    hypotheses = relationship("Hypothesis", back_populates="incident", cascade="all, delete-orphan")
    recommendations = relationship("Recommendation", back_populates="incident", cascade="all, delete-orphan")
    feedback = relationship("IncidentFeedback", back_populates="incident", uselist=False, cascade="all, delete-orphan")
    postmortem = relationship("Postmortem", back_populates="incident", uselist=False, cascade="all, delete-orphan")


class LogEvent(Base):
    __tablename__ = "log_events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id = Column(String(36), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True)
    event_id = Column(String(50), nullable=False, index=True)  # e.g., EVT-001
    timestamp = Column(DateTime, nullable=True, index=True)
    service = Column(String(100), nullable=False, default="unknown-service", index=True)
    environment = Column(String(50), default="simulated")
    log_level = Column(String(20), default="INFO", index=True)
    message = Column(Text, nullable=False)
    error_type = Column(String(100), nullable=True)
    trace_id = Column(String(100), nullable=True, index=True)
    span_id = Column(String(100), nullable=True)
    transaction_id = Column(String(100), nullable=True, index=True)
    endpoint = Column(String(255), nullable=True)
    http_status = Column(Integer, nullable=True)
    duration_ms = Column(Float, nullable=True)
    dependency = Column(String(100), nullable=True)
    fingerprint = Column(String(64), nullable=True, index=True)
    redaction_applied = Column(Boolean, default=False)
    line_number = Column(Integer, default=1)

    incident = relationship("Incident", back_populates="events")


class ErrorPattern(Base):
    __tablename__ = "error_patterns"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id = Column(String(36), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True)
    fingerprint = Column(String(64), nullable=False, index=True)
    service = Column(String(100), nullable=False)
    error_type = Column(String(100), nullable=True)
    pattern_template = Column(Text, nullable=False)
    occurrence_count = Column(Integer, default=1)
    first_seen = Column(DateTime, nullable=True)
    last_seen = Column(DateTime, nullable=True)
    sample_event_ids = Column(JSON, default=list)

    incident = relationship("Incident", back_populates="patterns")


class CorrelatedGroup(Base):
    __tablename__ = "correlated_groups"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id = Column(String(36), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True)
    correlation_type = Column(String(50), nullable=False)  # SHARED_TRANSACTION, SHARED_TRACE, DEPENDENCY_CASCADE, TEMPORAL_WINDOW
    strength = Column(String(20), nullable=False)  # HIGH, MEDIUM, LOW
    rationale = Column(Text, nullable=False)
    event_ids = Column(JSON, default=list)

    incident = relationship("Incident", back_populates="correlated_groups")


class EvidenceRecord(Base):
    __tablename__ = "evidence_records"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id = Column(String(36), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True)
    evidence_code = Column(String(20), nullable=False, index=True)  # e.g., E-001
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    source_event_ids = Column(JSON, default=list)
    confidence = Column(String(20), default="HIGH")

    incident = relationship("Incident", back_populates="evidence_records")


class Hypothesis(Base):
    __tablename__ = "hypotheses"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id = Column(String(36), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True)
    hypothesis_code = Column(String(20), nullable=False)  # e.g., H-001
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    confidence = Column(String(20), default="MEDIUM")  # HIGH, MEDIUM, LOW
    supporting_evidence_codes = Column(JSON, default=list)
    contradicting_evidence_codes = Column(JSON, default=list)
    verification_steps = Column(JSON, default=list)
    is_primary = Column(Boolean, default=False)

    incident = relationship("Incident", back_populates="hypotheses")


class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id = Column(String(36), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True)
    priority = Column(Integer, default=1)
    action = Column(Text, nullable=False)
    rationale = Column(Text, nullable=False)
    associated_runbook_id = Column(String(50), nullable=True)
    verification_step = Column(Text, nullable=True)

    incident = relationship("Incident", back_populates="recommendations")


class IncidentFeedback(Base):
    __tablename__ = "incident_feedback"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id = Column(String(36), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, unique=True)
    verified_root_cause = Column(Text, nullable=False)
    hypothesis_accuracy = Column(String(20), default="VERIFIED")  # VERIFIED, PARTIAL, REJECTED
    useful_recommendations = Column(JSON, default=list)
    remediation_notes = Column(Text, nullable=True)
    reviewed_by = Column(String(100), default="SRE On-Call")
    reviewed_at = Column(DateTime, default=get_utc_now)

    incident = relationship("Incident", back_populates="feedback")


class Postmortem(Base):
    __tablename__ = "postmortems"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id = Column(String(36), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, unique=True)
    status = Column(String(20), default="DRAFT")  # DRAFT, REVIEWED, APPROVED
    executive_summary = Column(Text, nullable=False)
    timeline = Column(JSON, default=list)
    root_cause_analysis = Column(Text, nullable=False)
    what_went_well = Column(JSON, default=list)
    what_went_wrong = Column(JSON, default=list)
    detection_gaps = Column(JSON, default=list)
    action_items = Column(JSON, default=list)
    generated_at = Column(DateTime, default=get_utc_now)

    incident = relationship("Incident", back_populates="postmortem")
