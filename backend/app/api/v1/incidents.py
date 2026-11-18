"""
Incident Workspace & Investigation Router
Manages incident lifecycle, deterministic timelines, evidence graphs, blast radius,
AI investigations, adversarial gap audits, and postmortems.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone

from app.core.database import get_db
from app.models.incident import Incident, IncidentFeedback, Postmortem
from app.schemas.incident import (
    IncidentSummaryResponse, IncidentDetailResponse, StatusUpdateRequest,
    FeedbackCreateRequest, WhatAmIMissingResponse, BlastRadiusResponse,
    EvidenceGraphResponse, TelemetryGapItem
)
from app.services.timeline import reconstruct_timeline
from app.services.topology import compute_blast_radius
from app.services.evidence_graph import build_evidence_graph
from app.services.what_am_i_missing import analyze_what_am_i_missing
from app.services.telemetry_gaps import detect_telemetry_gaps
from app.ai.orchestration.investigator import run_incident_investigation, get_llm_provider

router = APIRouter(prefix="/incidents", tags=["Incidents"])


@router.get("", response_model=List[IncidentSummaryResponse])
def list_incidents(
    severity: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    service: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(Incident)
    if severity:
        query = query.filter(Incident.severity == severity.upper())
    if status:
        query = query.filter(Incident.status == status.upper())

    incidents = query.order_by(Incident.created_at.desc()).all()
    results = []
    for inc in incidents:
        events = inc.events
        affected_services = sorted(list({e.service for e in events}))
        if service and service.lower() not in [s.lower() for s in affected_services]:
            continue

        total_errors = sum(1 for e in events if e.log_level in ["WARN", "ERROR", "CRITICAL"] or e.error_type)
        results.append(IncidentSummaryResponse(
            id=inc.id,
            incident_number=inc.incident_number,
            title=inc.title,
            severity=inc.severity,
            status=inc.status,
            customer_impact=inc.customer_impact,
            source_scenario=inc.source_scenario,
            created_at=inc.created_at,
            updated_at=inc.updated_at,
            resolved_at=inc.resolved_at,
            summary=inc.summary,
            severity_rationale={"reasons": inc.severity_rationale or []},
            total_events=len(events),
            total_errors=total_errors,
            affected_services=affected_services
        ))
    return results


@router.get("/{incident_id}", response_model=IncidentDetailResponse)
def get_incident_detail(incident_id: str, db: Session = Depends(get_db)):
    inc = db.query(Incident).filter(Incident.id == incident_id).first()
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found.")

    events = inc.events
    total_errors = sum(1 for e in events if e.log_level in ["WARN", "ERROR", "CRITICAL"] or e.error_type)
    affected_services = sorted(list({e.service for e in events}))

    return IncidentDetailResponse(
        id=inc.id,
        incident_number=inc.incident_number,
        title=inc.title,
        severity=inc.severity,
        status=inc.status,
        customer_impact=inc.customer_impact,
        source_scenario=inc.source_scenario,
        created_at=inc.created_at,
        updated_at=inc.updated_at,
        resolved_at=inc.resolved_at,
        summary=inc.summary,
        severity_rationale={"reasons": inc.severity_rationale or []},
        total_events=len(events),
        total_errors=total_errors,
        affected_services=affected_services,
        events=events,
        patterns=inc.patterns,
        correlated_groups=inc.correlated_groups,
        evidence_records=inc.evidence_records,
        hypotheses=inc.hypotheses,
        recommendations=inc.recommendations
    )


@router.patch("/{incident_id}/status")
def update_incident_status(incident_id: str, payload: StatusUpdateRequest, db: Session = Depends(get_db)):
    inc = db.query(Incident).filter(Incident.id == incident_id).first()
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found.")

    inc.status = payload.status
    inc.updated_at = datetime.now(timezone.utc)
    if payload.status in ["RESOLVED", "CLOSED"] and not inc.resolved_at:
        inc.resolved_at = datetime.now(timezone.utc)

    db.commit()
    return {"success": True, "incident_id": inc.id, "status": inc.status}


@router.post("/{incident_id}/investigate")
async def trigger_investigation(incident_id: str, db: Session = Depends(get_db)):
    inc = db.query(Incident).filter(Incident.id == incident_id).first()
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found.")

    res = await run_incident_investigation(inc, db)
    return {"success": True, "investigation": res}


@router.get("/{incident_id}/timeline")
def get_timeline(incident_id: str, db: Session = Depends(get_db)):
    inc = db.query(Incident).filter(Incident.id == incident_id).first()
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found.")

    event_dicts = [
        {
            "event_id": e.event_id,
            "timestamp": e.timestamp,
            "service": e.service,
            "log_level": e.log_level,
            "message": e.message,
            "http_status": e.http_status,
            "line_number": e.line_number
        }
        for e in inc.events
    ]
    return reconstruct_timeline(event_dicts)


@router.get("/{incident_id}/blast-radius", response_model=BlastRadiusResponse)
def get_blast_radius(incident_id: str, db: Session = Depends(get_db)):
    inc = db.query(Incident).filter(Incident.id == incident_id).first()
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found.")

    event_dicts = [
        {
            "service": e.service,
            "log_level": e.log_level,
            "error_type": e.error_type
        }
        for e in inc.events
    ]
    return compute_blast_radius(incident_id, event_dicts)


@router.get("/{incident_id}/evidence-graph", response_model=EvidenceGraphResponse)
def get_evidence_graph_data(incident_id: str, db: Session = Depends(get_db)):
    inc = db.query(Incident).filter(Incident.id == incident_id).first()
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found.")

    event_dicts = [{"event_id": e.event_id, "service": e.service} for e in inc.events]
    pattern_dicts = [
        {
            "fingerprint": p.fingerprint,
            "service": p.service,
            "occurrence_count": p.occurrence_count,
            "pattern_template": p.pattern_template,
            "sample_event_ids": p.sample_event_ids
        }
        for p in inc.patterns
    ]
    hyp_dicts = [
        {
            "hypothesis_code": h.hypothesis_code,
            "title": h.title,
            "confidence": h.confidence,
            "description": h.description,
            "supporting_event_ids": h.supporting_evidence_codes
        }
        for h in inc.hypotheses
    ]
    rec_dicts = [
        {
            "action": r.action,
            "priority": r.priority,
            "rationale": r.rationale
        }
        for r in inc.recommendations
    ]

    return build_evidence_graph(
        incident_id=incident_id,
        events=event_dicts,
        patterns=pattern_dicts,
        hypotheses=hyp_dicts,
        recommendations=rec_dicts,
        severity_reasons=inc.severity_rationale or []
    )


@router.post("/{incident_id}/what-am-i-missing", response_model=WhatAmIMissingResponse)
def get_what_am_i_missing(incident_id: str, db: Session = Depends(get_db)):
    inc = db.query(Incident).filter(Incident.id == incident_id).first()
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found.")

    event_dicts = [
        {
            "event_id": e.event_id,
            "service": e.service,
            "message": e.message,
            "log_level": e.log_level,
            "trace_id": e.trace_id,
            "http_status": e.http_status
        }
        for e in inc.events
    ]
    pattern_dicts = [{"service": p.service, "occurrence_count": p.occurrence_count} for p in inc.patterns]
    hyp_dicts = [{"title": h.title} for h in inc.hypotheses]

    return analyze_what_am_i_missing(incident_id, event_dicts, pattern_dicts, hyp_dicts)


@router.get("/{incident_id}/telemetry-gaps", response_model=List[TelemetryGapItem])
def get_telemetry_gaps(incident_id: str, db: Session = Depends(get_db)):
    inc = db.query(Incident).filter(Incident.id == incident_id).first()
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found.")

    event_dicts = [
        {
            "event_id": e.event_id,
            "service": e.service,
            "message": e.message,
            "log_level": e.log_level,
            "trace_id": e.trace_id,
            "duration_ms": e.duration_ms
        }
        for e in inc.events
    ]
    return detect_telemetry_gaps(event_dicts)


@router.post("/{incident_id}/feedback")
def submit_feedback(incident_id: str, payload: FeedbackCreateRequest, db: Session = Depends(get_db)):
    inc = db.query(Incident).filter(Incident.id == incident_id).first()
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found.")

    # Upsert feedback
    fb = db.query(IncidentFeedback).filter(IncidentFeedback.incident_id == incident_id).first()
    if not fb:
        fb = IncidentFeedback(
            incident_id=incident_id,
            verified_root_cause=payload.verified_root_cause,
            hypothesis_accuracy=payload.hypothesis_accuracy,
            useful_recommendations=payload.useful_recommendations,
            remediation_notes=payload.remediation_notes,
            reviewed_by=payload.reviewed_by
        )
        db.add(fb)
    else:
        fb.verified_root_cause = payload.verified_root_cause
        fb.hypothesis_accuracy = payload.hypothesis_accuracy
        fb.useful_recommendations = payload.useful_recommendations
        fb.remediation_notes = payload.remediation_notes
        fb.reviewed_by = payload.reviewed_by
        fb.reviewed_at = datetime.now(timezone.utc)

    db.commit()
    return {"success": True, "feedback_id": fb.id}


@router.post("/{incident_id}/postmortem")
async def generate_postmortem(incident_id: str, db: Session = Depends(get_db)):
    inc = db.query(Incident).filter(Incident.id == incident_id).first()
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found.")

    provider = get_llm_provider()
    incident_data = {
        "incident_number": inc.incident_number,
        "title": inc.title,
        "severity": inc.severity,
        "created_at": inc.created_at.isoformat() if inc.created_at else None,
        "events": [{"event_id": e.event_id, "service": e.service, "message": e.message} for e in inc.events[:30]],
        "hypotheses": [{"title": h.title, "description": h.description} for h in inc.hypotheses]
    }

    draft = await provider.draft_postmortem(incident_data)

    pm = db.query(Postmortem).filter(Postmortem.incident_id == incident_id).first()
    if not pm:
        pm = Postmortem(
            incident_id=incident_id,
            status="DRAFT",
            executive_summary=draft.get("executive_summary", ""),
            timeline=draft.get("timeline", []),
            root_cause_analysis=draft.get("root_cause_analysis", ""),
            what_went_well=draft.get("what_went_well", []),
            what_went_wrong=draft.get("what_went_wrong", []),
            detection_gaps=draft.get("detection_gaps", []),
            action_items=draft.get("action_items", [])
        )
        db.add(pm)
    else:
        pm.executive_summary = draft.get("executive_summary", pm.executive_summary)
        pm.timeline = draft.get("timeline", pm.timeline)
        pm.root_cause_analysis = draft.get("root_cause_analysis", pm.root_cause_analysis)
        pm.what_went_well = draft.get("what_went_well", pm.what_went_well)
        pm.what_went_wrong = draft.get("what_went_wrong", pm.what_went_wrong)
        pm.detection_gaps = draft.get("detection_gaps", pm.detection_gaps)
        pm.action_items = draft.get("action_items", pm.action_items)

    db.commit()
    return {"success": True, "postmortem": draft}


@router.get("/{incident_id}/postmortem")
def get_postmortem(incident_id: str, db: Session = Depends(get_db)):
    pm = db.query(Postmortem).filter(Postmortem.incident_id == incident_id).first()
    if not pm:
        raise HTTPException(status_code=404, detail="Postmortem not yet generated.")

    return {
        "id": pm.id,
        "incident_id": pm.incident_id,
        "status": pm.status,
        "executive_summary": pm.executive_summary,
        "timeline": pm.timeline,
        "root_cause_analysis": pm.root_cause_analysis,
        "what_went_well": pm.what_went_well,
        "what_went_wrong": pm.what_went_wrong,
        "detection_gaps": pm.detection_gaps,
        "action_items": pm.action_items,
        "generated_at": pm.generated_at
    }
