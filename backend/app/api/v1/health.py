"""
System Health & Readiness Router
Provides Kubernetes / Docker observability probes and dependency health statuses.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db
from app.core.config import settings

router = APIRouter(tags=["Health & Diagnostics"])


@router.get("/health")
def health_check():
    return {
        "status": "UP",
        "system": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
        "disclaimer": "SIMULATED ENVIRONMENT — NO PRODUCTION SYSTEM CONNECTION"
    }


@router.get("/ready")
def readiness_check(db: Session = Depends(get_db)):
    try:
        # Check database connectivity
        db.execute(text("SELECT 1"))
        db_status = "CONNECTED"
    except Exception as e:
        db_status = f"FAILED: {str(e)}"

    return {
        "status": "READY" if db_status == "CONNECTED" else "DEGRADED",
        "database": db_status,
        "llm_provider": settings.LLM_PROVIDER,
        "gemini_configured": bool(settings.GEMINI_API_KEY)
    }
