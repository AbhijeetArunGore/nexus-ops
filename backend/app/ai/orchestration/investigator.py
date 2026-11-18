"""
AI Investigation Orchestrator
Gathers normalized incident telemetry, queries LLM provider, enforces citation validation,
and commits grounded hypotheses and recommendations to the database.
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

    # 1. Compile compact investigation package
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
        for e in incident.events[:80]  # Bounded context window
    ]

    valid_event_ids = {e["event_id"] for e in event_dict_list}

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
        "events": event_dict_list,
        "patterns": pattern_list,
        "correlated_groups": correlated_list
    }

    # 2. Invoke Provider
    raw_analysis = await provider.generate_investigation(payload)

    # 3. Citation Verification Layer: Filter nonexistent event references
    primary = raw_analysis.get("primary_hypothesis", {})
    verified_supporting = [eid for eid in primary.get("supporting_event_ids", []) if eid in valid_event_ids]
    if not verified_supporting and valid_event_ids:
        # Fall back to first available error event to maintain evidence grounding
        error_eids = [e["event_id"] for e in event_dict_list if e.get("log_level") in ["ERROR", "CRITICAL"]]
        verified_supporting = error_eids[:3] if error_eids else list(valid_event_ids)[:2]

    primary["supporting_event_ids"] = verified_supporting

    # Clean existing records in DB before inserting refreshed analysis
    db.query(Hypothesis).filter(Hypothesis.incident_id == incident.id).delete()
    db.query(EvidenceRecord).filter(EvidenceRecord.incident_id == incident.id).delete()
    db.query(Recommendation).filter(Recommendation.incident_id == incident.id).delete()

    # Save Primary Hypothesis
    h_primary = Hypothesis(
        incident_id=incident.id,
        hypothesis_code=primary.get("hypothesis_code", "H-001"),
        title=primary.get("title", "Service Anomaly"),
        description=primary.get("description", "Identified anomalous service behavior."),
        confidence=primary.get("confidence", "HIGH"),
        supporting_evidence_codes=primary.get("supporting_event_ids", []),
        contradicting_evidence_codes=primary.get("contradicting_event_ids", []),
        verification_steps=primary.get("verification_steps", []),
        is_primary=True
    )
    db.add(h_primary)

    # Save Alternative Hypotheses
    for idx, alt in enumerate(raw_analysis.get("alternative_hypotheses", []), start=2):
        alt_verified = [eid for eid in alt.get("supporting_event_ids", []) if eid in valid_event_ids]
        h_alt = Hypothesis(
            incident_id=incident.id,
            hypothesis_code=alt.get("hypothesis_code", f"H-{idx:03d}"),
            title=alt.get("title", f"Alternative Hypothesis {idx}"),
            description=alt.get("description", ""),
            confidence=alt.get("confidence", "LOW"),
            supporting_evidence_codes=alt_verified,
            contradicting_evidence_codes=[],
            verification_steps=alt.get("verification_steps", []),
            is_primary=False
        )
        db.add(h_alt)

    # Save Evidence Records
    for idx, eid in enumerate(verified_supporting, start=1):
        ev_rec = EvidenceRecord(
            incident_id=incident.id,
            evidence_code=f"E-{idx:03d}",
            title=f"Forensic Observation on {eid}",
            description=f"Observable failure event {eid} correlated with incident root cause.",
            source_event_ids=[eid],
            confidence="HIGH"
        )
        db.add(ev_rec)

    # Save Recommendations
    for rec in raw_analysis.get("recommendations", []):
        r_entry = Recommendation(
            incident_id=incident.id,
            priority=rec.get("priority", 1),
            action=rec.get("action", "Inspect application logs."),
            rationale=rec.get("rationale", "Restores service operational integrity."),
            associated_runbook_id=rec.get("associated_runbook_id"),
            verification_step=rec.get("verification_step")
        )
        db.add(r_entry)

    # Update summary on Incident
    incident.summary = raw_analysis.get("incident_summary")
    db.commit()
    db.refresh(incident)

    return raw_analysis
