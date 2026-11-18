"""
Ops Knowledge Copilot Router (Module 14)
Conversational technical assistant supporting LEARNING and ENGINEERING modes with incident context.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.models.incident import Incident
from app.schemas.incident import CopilotAskRequest, CopilotAnswerResponse
from app.ai.orchestration.investigator import get_llm_provider

router = APIRouter(prefix="/copilot", tags=["Ops Knowledge Copilot"])


@router.post("/ask", response_model=CopilotAnswerResponse)
async def ask_copilot(payload: CopilotAskRequest, incident_id: Optional[str] = None, db: Session = Depends(get_db)):
    """
    Answers technical operational questions with optional incident grounding.
    """
    incident_context = None
    if incident_id:
        inc = db.query(Incident).filter(Incident.id == incident_id).first()
        if inc:
            incident_context = {
                "incident_number": inc.incident_number,
                "title": inc.title,
                "severity": inc.severity,
                "status": inc.status,
                "customer_impact": inc.customer_impact,
                "affected_services": list({e.service for e in inc.events}),
                "events_count": len(inc.events),
                "hypotheses": [h.title for h in inc.hypotheses]
            }

    provider = get_llm_provider()

    # Grounding: Retrieve top matching runbooks and concepts from local knowledge base
    from app.services.knowledge_service import search_runbooks, RUNBOOK_CATALOG
    matched_runbooks = search_runbooks(payload.query)

    answer_dict = await provider.answer_copilot_query(payload.query, payload.mode, incident_context)

    # Blend matched runbook references if present
    sources = list(answer_dict.get("source_references", []))
    for rb in matched_runbooks[:2]:
        rb_ref = f"{rb['id']}: {rb['title']} (Synthetic SRE Runbook)"
        if rb_ref not in sources:
            sources.append(rb_ref)

    return CopilotAnswerResponse(
        query=payload.query,
        mode=payload.mode,
        answer=answer_dict.get("answer", "Unable to formulate answer."),
        technical_details=answer_dict.get("technical_details"),
        supporting_evidence=answer_dict.get("supporting_evidence", []),
        suggested_actions=answer_dict.get("suggested_actions", []),
        source_references=sources,
        follow_up_questions=answer_dict.get("follow_up_questions", [])
    )
