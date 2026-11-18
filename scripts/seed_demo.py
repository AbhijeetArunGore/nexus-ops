"""
Synthetic Demo Seeding Script for NEXUS Ops
Generates a realistic, clean, balanced set of simulated payment incidents:
- 1 Critical: Database connection pool exhaustion with cascade
- 1 High: Acquiring partner latency degradation
- 1 Medium: Merchant webhook dispatch failure
- 1 Low: Duplicate webhook safely deduplicated via idempotency key
- 1 Mitigated/Resolved: Late authorization reconciled after investigation
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.core.database import SessionLocal, Base, engine
from app.models.incident import Incident, LogEvent, ErrorPattern, CorrelatedGroup, Hypothesis, EvidenceRecord, Recommendation
from app.api.v1.analyses import process_and_create_incident
from app.api.v1.scenarios import SCENARIOS_CATALOG


def seed_demo_environment():
    print("==================================================")
    print("  Seeding NEXUS Ops Demo Environment")
    print("==================================================")

    # Ensure tables exist
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # Clear existing demo incidents to ensure a fresh clean state
        existing_count = db.query(Incident).count()
        if existing_count > 0:
            print(f"Cleaning {existing_count} existing records...")
            db.query(Incident).delete()
            db.commit()

        # Select 4 representative scenarios
        demo_scenario_ids = [
            "scenario-04-db-exhaustion",      # CRITICAL
            "scenario-05-partner-degradation",# HIGH/CRITICAL
            "scenario-02-webhook-failure",    # MEDIUM
            "scenario-03-duplicate-webhooks",  # LOW
        ]

        for scen_id in demo_scenario_ids:
            scen = next((s for s in SCENARIOS_CATALOG if s["id"] == scen_id), None)
            if scen:
                print(f"Ingesting {scen['title']}...")
                inc = process_and_create_incident(
                    content=scen["log_sample"],
                    title=scen["title"],
                    db=db,
                    scenario_name=scen["id"]
                )
                print(f"  -> Created {inc.incident_number} (Severity: {inc.severity}, Impact: {inc.customer_impact})")

        print("\nDemo seeding completed successfully! Dashboard has balanced representative severities.")

    except Exception as e:
        db.rollback()
        print(f"Error seeding demo: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_demo_environment()
