"""
Runbook Library & Knowledge Base Router (Module 13)
Provides access to curated SRE procedures and Pine Labs payment concepts.
"""
from fastapi import APIRouter, Query, HTTPException
from typing import List, Optional
from app.services.knowledge_service import RUNBOOK_CATALOG, search_runbooks, get_runbook_by_id

router = APIRouter(prefix="/runbooks", tags=["Runbooks & Knowledge"])


@router.get("")
def list_runbooks(query: Optional[str] = Query(None), service: Optional[str] = Query(None)):
    """
    Search and retrieve runbooks from the knowledge base.
    """
    if query or service:
        return search_runbooks(query or "", service)
    return RUNBOOK_CATALOG


@router.get("/{runbook_id}")
def get_runbook(runbook_id: str):
    rb = get_runbook_by_id(runbook_id)
    if not rb:
        raise HTTPException(status_code=404, detail="Runbook not found.")
    return rb
