"""
AI Investigation Orchestrator
Gathers normalized incident telemetry, queries LLM provider, enforces strict citation validation,
and commits grounded hypotheses and recommendations to the database.

Engineering Principles:
- Grounding: Never manufacture citations.
- If AI provides nonexistent or invalid event IDs, reject them and mark hypothesis UNSUPPORTED / ASSUMPTION.
- Persist observed facts, inferences, assumptions, and unknowns as first-class fields.
"""
import logging
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from app.models.incident import Incident, Hypothesis, EvidenceRecord, Recommendation
from app.ai.providers.gemini_provider import GeminiProvider
from app.ai.providers.deterministic_fallback import DeterministicFallbackProvider
from app.core.config import settings

logger = logging.getLogger(__name__)


def get_llm_provider():
    if settings.LLM_PROVIDER.lower() == "gemini" and settings.GEMINI_API_KEY:
        return GeminiProvider()
    return DeterministicFallbackProvider()


async def run_incident_investigation(incident: Incident, db: Session) -> Dict[str, Any]:
    """
    Executes grounded AI investigation for an incident.
    """
    provider = get_llm_provider()

    # 1. Compile representative evidence package (not just the first 80 lines)
    # Select: earliest errors, latest errors, burst samples, unique error types
    all_events = incident.events
    error_events = [e for e in all_events if e.log_level in ["WARN", "ERROR", "CRITICAL"] or e.error_type]

    # Pick representative events up to 80 items
    selected_events = []
    seen_fingerprints = set()
    for e in error_events:
        if e.fingerprint not in seen_fingerprints or len(selected_events) < 40:
            selected_events.append(e)
            if e.fingerprint:
                seen_fingerprints.add(e.fingerprint)
        if len(selected_events) >= 80:
            break

    if not selected_events:
        selected_events = all_events[:40]

    event_dict_list = [
        {
            "event_id": e.event_id,
            "timestamp": e.timestamp.isoformat() if e.timestamp else None,
            "service": e.service,
            "log_level": e.log_level,
            "message": e.message,
            "error_type": e.error_type,
            "trace_id": e.trace_id,
            "transaction_id": e.transaction_id,
            "http_status": e.http_status
        }
        for e in selected_events
    ]

    valid_event_ids = {e.event_id for e in all_events}

    pattern_list = [
        {
            "fingerprint": p.fingerprint,
            "service": p.service,
            "occurrence_count": p.occurrence_count,
            "pattern_template": p.pattern_template,
            "sample_event_ids": p.sample_event_ids
        }
        for p in incident.patterns
    ]

    correlated_list = [
        {
            "correlation_type": c.correlation_type,
            "strength": c.strength,
            "rationale": c.rationale,
            "event_ids": c.event_ids
        }
        for c in incident.correlated_groups
    ]

    payload = {
        "incident_number": incident.incident_number,
        "title": incident.title,
        "severity": incident.severity,
        "customer_impact": incident.customer_impact,
        "payment_outcome": getattr(incident, "payment_outcome", "UNKNOWN"),
        "events": event_dict_list,
        "patterns": pattern_list,
        "correlated_groups": correlated_list
    }

    # 2. Invoke Provider
    raw_analysis = await provider.generate_investigation(payload)

    # 3. Citation Verification Layer: Filter nonexistent event references
    primary = raw_analysis.get("primary_hypothesis", {})
    verified_supporting = [eid for eid in primary.get("supporting_event_ids", []) if eid in valid_event_ids]

    # Explicit Grounding Rule: If citations are missing or invalid, do NOT attach fake events
    assumptions = primary.get("assumptions", [])
    inferences = primary.get("inferences", [])
    unknowns = raw_analysis.get("missing_evidence", []) + raw_analysis.get("limitations", [])

    if not verified_supporting:
        primary_confidence = "LOW"
        assumptions.append("Hypothesis lacks verified event citations from supplied logs; classified as speculative assumption.")
    else:
        primary_confidence = primary.get("confidence", "MEDIUM")

    primary["supporting_event_ids"] = verified_supporting

    # Clean existing records in DB before inserting refreshed analysis
    db.query(Hypothesis).filter(Hypothesis.incident_id == incident.id).delete()
    db.query(EvidenceRecord).filter(EvidenceRecord.incident_id == incident.id).delete()
    db.query(Recommendation).filter(Recommendation.incident_id == incident.id).delete()

    # Save Primary Hypothesis
    h_primary = Hypothesis(
        incident_id=incident.id,
        hypothesis_code=primary.get("hypothesis_code", "H-001"),
        title=primary.get("title", "Likely Cause Anomaly"),
        description=primary.get("description", "Identified anomalous service behavior."),
        confidence=primary_confidence,
        supporting_evidence_codes=verified_supporting,
        contradicting_evidence_codes=[eid for eid in primary.get("contradicting_event_ids", []) if eid in valid_event_ids],
        assumptions=assumptions,
        inferences=inferences,
        unknowns=unknowns,
        verification_steps=primary.get("verification_steps", []),
        is_primary=True
    )
    db.add(h_primary)

    # Save Alternative Hypotheses
    for idx, alt in enumerate(raw_analysis.get("alternative_hypotheses", []), start=2):
        alt_verified = [eid for eid in alt.get("supporting_event_ids", []) if eid in valid_event_ids]
        alt_assumptions = alt.get("assumptions", [])
        if not alt_verified:
            alt_assumptions.append("Unverified alternative hypothesis.")
        h_alt = Hypothesis(
            incident_id=incident.id,
            hypothesis_code=alt.get("hypothesis_code", f"H-{idx:03d}"),
            title=alt.get("title", f"Alternative Hypothesis {idx}"),
            description=alt.get("description", ""),
            confidence=alt.get("confidence", "LOW") if alt_verified else "LOW",
            supporting_evidence_codes=alt_verified,
            contradicting_evidence_codes=[],
            assumptions=alt_assumptions,
            inferences=alt.get("inferences", []),
            unknowns=[],
            verification_steps=alt.get("verification_steps", []),
            is_primary=False
        )
        db.add(h_alt)

    # Save Evidence Records only for genuine verified citations
    for idx, eid in enumerate(verified_supporting, start=1):
        matching_evt = next((e for e in all_events if e.event_id == eid), None)
        svc_msg = f" [{matching_evt.service}] {matching_evt.message}" if matching_evt else ""
        ev_rec = EvidenceRecord(
            incident_id=incident.id,
            evidence_code=f"E-{idx:03d}",
            title=f"Observed Evidence: {eid}",
            description=f"Verified log record {eid}:{svc_msg}",
            source_event_ids=[eid],
            confidence="HIGH"
        )
        db.add(ev_rec)

    # Save Recommendations
    for idx, rec in enumerate(raw_analysis.get("recommendations", []), start=1):
        r_entry = Recommendation(
            incident_id=incident.id,
            priority=rec.get("priority", idx),
            action=rec.get("action", "Inspect component logs and verify connectivity."),
            rationale=rec.get("rationale", "Standard diagnostic verification step."),
            associated_runbook_id=rec.get("associated_runbook_id"),
            verification_step=rec.get("verification_step")
        )
        db.add(r_entry)

    # Update Incident summary
    if raw_analysis.get("summary"):
        incident.summary = raw_analysis["summary"]

    db.commit()
    db.refresh(incident)

    return {
        "summary": incident.summary,
        "primary_hypothesis": {
            "hypothesis_code": h_primary.hypothesis_code,
            "title": h_primary.title,
            "description": h_primary.description,
            "confidence": h_primary.confidence,
            "supporting_event_ids": verified_supporting,
            "assumptions": h_primary.assumptions,
            "inferences": h_primary.inferences,
            "unknowns": h_primary.unknowns,
            "verification_steps": h_primary.verification_steps,
            "is_primary": True
        },
        "alternative_hypotheses": raw_analysis.get("alternative_hypotheses", []),
        "recommendations": raw_analysis.get("recommendations", []),
        "missing_evidence": raw_analysis.get("missing_evidence", []),
        "limitations": raw_analysis.get("limitations", []),
        "provider": getattr(provider, "provider_name", "deterministic_fallback")
    }
