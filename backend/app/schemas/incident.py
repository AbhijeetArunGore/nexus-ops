"""
Pydantic Schemas for NEXUS Ops
"""
from typing import List, Optional, Any, Dict
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class LogEventBase(BaseModel):
    event_id: str
    timestamp: Optional[datetime] = None
    service: str = "unknown-service"
    environment: str = "simulated"
    log_level: str = "INFO"
    message: str
    error_type: Optional[str] = None
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    transaction_id: Optional[str] = None
    endpoint: Optional[str] = None
    http_status: Optional[int] = None
    duration_ms: Optional[float] = None
    dependency: Optional[str] = None
    fingerprint: Optional[str] = None
    redaction_applied: bool = False
    line_number: int = 1


class LogEventResponse(LogEventBase):
    id: str
    incident_id: str
    model_config = ConfigDict(from_attributes=True)


class ErrorPatternResponse(BaseModel):
    id: str
    fingerprint: str
    service: str
    error_type: Optional[str] = None
    pattern_template: str
    occurrence_count: int
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    sample_event_ids: List[str] = []
    model_config = ConfigDict(from_attributes=True)


class CorrelatedGroupResponse(BaseModel):
    id: str
    correlation_type: str
    strength: str
    rationale: str
    event_ids: List[str] = []
    model_config = ConfigDict(from_attributes=True)


class EvidenceRecordResponse(BaseModel):
    id: str
    evidence_code: str
    title: str
    description: str
    source_event_ids: List[str] = []
    confidence: str
    model_config = ConfigDict(from_attributes=True)


class HypothesisResponse(BaseModel):
    id: str
    hypothesis_code: str
    title: str
    description: str
    confidence: str
    supporting_evidence_codes: List[str] = []
    contradicting_evidence_codes: List[str] = []
    verification_steps: List[str] = []
    is_primary: bool
    model_config = ConfigDict(from_attributes=True)


class RecommendationResponse(BaseModel):
    id: str
    priority: int
    action: str
    rationale: str
    associated_runbook_id: Optional[str] = None
    verification_step: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class SeverityRationaleItem(BaseModel):
    rule: str
    weight: str
    description: str
    supporting_event_ids: List[str] = []


class SeverityDecision(BaseModel):
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    customer_impact: str  # CONFIRMED, SUSPECTED, UNKNOWN
    score: int
    reasons: List[SeverityRationaleItem] = []


class IncidentSummaryResponse(BaseModel):
    id: str
    incident_number: str
    title: str
    severity: str
    status: str
    customer_impact: str
    source_scenario: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None
    summary: Optional[str] = None
    severity_rationale: Optional[Dict[str, Any]] = None
    total_events: int = 0
    total_errors: int = 0
    affected_services: List[str] = []
    model_config = ConfigDict(from_attributes=True)


class IncidentDetailResponse(IncidentSummaryResponse):
    events: List[LogEventResponse] = []
    patterns: List[ErrorPatternResponse] = []
    correlated_groups: List[CorrelatedGroupResponse] = []
    evidence_records: List[EvidenceRecordResponse] = []
    hypotheses: List[HypothesisResponse] = []
    recommendations: List[RecommendationResponse] = []


class IngestionPasteRequest(BaseModel):
    content: str
    title: Optional[str] = None
    source_name: Optional[str] = "pasted_logs.log"


class StatusUpdateRequest(BaseModel):
    status: str = Field(..., pattern="^(OPEN|INVESTIGATING|MITIGATED|RESOLVED|CLOSED)$")


class FeedbackCreateRequest(BaseModel):
    verified_root_cause: str
    hypothesis_accuracy: str = Field("VERIFIED", pattern="^(VERIFIED|PARTIAL|REJECTED)$")
    useful_recommendations: List[str] = []
    remediation_notes: Optional[str] = None
    reviewed_by: str = "SRE Reviewer"


class CopilotAskRequest(BaseModel):
    query: str
    mode: str = Field("ENGINEERING", pattern="^(LEARNING|ENGINEERING)$")


class CopilotAnswerResponse(BaseModel):
    query: str
    mode: str
    answer: str
    technical_details: Optional[str] = None
    supporting_evidence: List[str] = []
    suggested_actions: List[str] = []
    source_references: List[str] = []
    follow_up_questions: List[str] = []


class WhatAmIMissingItem(BaseModel):
    category: str
    description: str
    risk_level: str
    recommended_check: str


class WhatAmIMissingResponse(BaseModel):
    incident_id: str
    gaps_identified: List[WhatAmIMissingItem] = []
    alternative_hypotheses: List[str] = []
    telemetry_blindspots: List[str] = []


class TelemetryGapItem(BaseModel):
    missing_signal: str
    affected_service: str
    operational_impact: str
    instrumentation_fix: str
    priority: str  # HIGH, MEDIUM, LOW


class BlastRadiusNode(BaseModel):
    service: str
    status: str  # OBSERVED_IMPACT, POTENTIAL_BLAST_RADIUS, HEALTHY
    depth: int
    error_count: int = 0


class BlastRadiusEdge(BaseModel):
    from_service: str
    to_service: str
    relationship: str


class BlastRadiusResponse(BaseModel):
    incident_id: str
    observed_services: List[str]
    exposed_downstream_services: List[str]
    nodes: List[BlastRadiusNode]
    edges: List[BlastRadiusEdge]


class EvidenceGraphNode(BaseModel):
    id: str
    label: str
    type: str  # event, pattern, hypothesis, recommendation, service, rule
    metadata: Dict[str, Any] = {}


class EvidenceGraphEdge(BaseModel):
    source: str
    target: str
    label: str


class EvidenceGraphResponse(BaseModel):
    incident_id: str
    nodes: List[EvidenceGraphNode]
    edges: List[EvidenceGraphEdge]
