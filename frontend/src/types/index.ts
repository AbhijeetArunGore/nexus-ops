export type Severity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
export type IncidentStatus = 'OPEN' | 'INVESTIGATING' | 'MITIGATED' | 'RESOLVED' | 'CLOSED';
export type CustomerImpact = 'CONFIRMED' | 'SUSPECTED' | 'UNKNOWN';

export interface SeverityRationaleItem {
  rule: string;
  weight: string;
  description: string;
  supporting_event_ids: string[];
}

export interface IncidentSummary {
  id: string;
  incident_number: string;
  title: string;
  severity: Severity;
  status: IncidentStatus;
  customer_impact: CustomerImpact;
  source_scenario?: string | null;
  created_at: string;
  updated_at: string;
  resolved_at?: string | null;
  summary?: string | null;
  severity_rationale?: {
    reasons: SeverityRationaleItem[];
  };
  total_events: number;
  total_errors: number;
  affected_services: string[];
}

export interface LogEvent {
  id: string;
  incident_id: string;
  event_id: string;
  timestamp: string | null;
  service: string;
  environment: string;
  log_level: string;
  message: string;
  error_type?: string | null;
  trace_id?: string | null;
  span_id?: string | null;
  transaction_id?: string | null;
  endpoint?: string | null;
  http_status?: number | null;
  duration_ms?: number | null;
  dependency?: string | null;
  fingerprint?: string | null;
  redaction_applied: boolean;
  line_number: number;
}

export interface ErrorPattern {
  id: string;
  fingerprint: string;
  service: string;
  error_type?: string | null;
  pattern_template: string;
  occurrence_count: number;
  first_seen?: string | null;
  last_seen?: string | null;
  sample_event_ids: string[];
}

export interface CorrelatedGroup {
  id: string;
  correlation_type: string;
  strength: 'HIGH' | 'MEDIUM' | 'LOW';
  rationale: string;
  event_ids: string[];
}

export interface EvidenceRecord {
  id: string;
  evidence_code: string;
  title: string;
  description: string;
  source_event_ids: string[];
  confidence: string;
}

export interface Hypothesis {
  id: string;
  hypothesis_code: string;
  title: string;
  description: string;
  confidence: 'HIGH' | 'MEDIUM' | 'LOW';
  supporting_evidence_codes: string[];
  contradicting_evidence_codes: string[];
  verification_steps: string[];
  is_primary: boolean;
}

export interface Recommendation {
  id: string;
  priority: number;
  action: string;
  rationale: string;
  associated_runbook_id?: string | null;
  verification_step?: string | null;
}

export interface IncidentDetail extends IncidentSummary {
  events: LogEvent[];
  patterns: ErrorPattern[];
  correlated_groups: CorrelatedGroup[];
  evidence_records: EvidenceRecord[];
  hypotheses: Hypothesis[];
  recommendations: Recommendation[];
}

export interface TimelineItem {
  event_id: string;
  timestamp: string | null;
  service: string;
  log_level: string;
  message: string;
  http_status?: number | null;
  tags: string[];
}

export interface TimelineResponse {
  milestones: {
    first_observed?: string | null;
    earliest_underlying?: string | null;
    first_customer_impact?: string | null;
    recovery_signal?: string | null;
  };
  items: TimelineItem[];
}

export interface BlastRadiusNode {
  service: string;
  status: 'OBSERVED_IMPACT' | 'POTENTIAL_BLAST_RADIUS' | 'HEALTHY';
  depth: number;
  error_count: number;
}

export interface BlastRadiusEdge {
  from_service: string;
  to_service: string;
  relationship: string;
}

export interface BlastRadiusResponse {
  incident_id: string;
  observed_services: string[];
  exposed_downstream_services: string[];
  nodes: BlastRadiusNode[];
  edges: BlastRadiusEdge[];
}

export interface EvidenceGraphNode {
  id: string;
  label: string;
  type: 'event' | 'pattern' | 'hypothesis' | 'recommendation' | 'service' | 'rule';
  metadata: Record<string, any>;
}

export interface EvidenceGraphEdge {
  source: string;
  target: string;
  label: string;
}

export interface EvidenceGraphResponse {
  incident_id: string;
  nodes: EvidenceGraphNode[];
  edges: EvidenceGraphEdge[];
}

export interface WhatAmIMissingItem {
  category: string;
  description: string;
  risk_level: string;
  recommended_check: string;
}

export interface WhatAmIMissingResponse {
  incident_id: string;
  gaps_identified: WhatAmIMissingItem[];
  alternative_hypotheses: string[];
  telemetry_blindspots: string[];
}

export interface TelemetryGapItem {
  missing_signal: string;
  affected_service: string;
  operational_impact: string;
  instrumentation_fix: string;
  priority: 'HIGH' | 'MEDIUM' | 'LOW';
}

export interface Runbook {
  id: string;
  title: string;
  category: string;
  applicable_services: string[];
  symptoms: string[];
  investigation_steps: string[];
  escalation_conditions: string;
  recovery_verification: string;
  provenance: string;
}

export interface ScenarioMeta {
  id: string;
  title: string;
  category: string;
  description: string;
  difficulty: string;
  expected_severity: Severity;
  expected_primary_hypothesis: string;
  key_learning: string;
}

export interface CopilotResponse {
  query: string;
  mode: 'LEARNING' | 'ENGINEERING';
  answer: string;
  technical_details?: string;
  supporting_evidence: string[];
  suggested_actions: string[];
  source_references: string[];
  follow_up_questions: string[];
}
