"""
NEXUS Ops — Payment Reliability & Incident Intelligence Platform
Master FastAPI Application Entrypoint
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.core.config import settings
from app.core.database import Base, engine
from app.api.v1.health import router as health_router
from app.api.v1.analyses import router as analyses_router
from app.api.v1.incidents import router as incidents_router
from app.api.v1.copilot import router as copilot_router
from app.api.v1.runbooks import router as runbooks_router
from app.api.v1.scenarios import router as scenarios_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("nexus-ops")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing NEXUS Ops database schema...")
    Base.metadata.create_all(bind=engine)
    logger.info("NEXUS Ops initialized successfully.")
    yield
    logger.info("NEXUS Ops shutting down.")


app = FastAPI(
    title="NEXUS Ops",
    description="Payment Reliability & Incident Intelligence Platform (Simulated Pine Labs Architecture)",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(health_router, prefix="/api/v1")
app.include_router(analyses_router, prefix="/api/v1")
app.include_router(incidents_router, prefix="/api/v1")
app.include_router(copilot_router, prefix="/api/v1")
app.include_router(runbooks_router, prefix="/api/v1")
app.include_router(scenarios_router, prefix="/api/v1")


@app.get("/")
def root():
    return {
        "project": "NEXUS Ops",
        "tagline": "From Operational Signals to Explainable Incident Intelligence",
        "environment": "SIMULATED ENVIRONMENT — NO PRODUCTION SYSTEM CONNECTION",
        "documentation": "/docs",
        "api_v1": "/api/v1"
    }
