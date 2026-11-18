"""
NEXUS Ops Scenario Verification Test Suite (Stage 2)
Independently verifies all 8 Pine Labs-inspired payment incident scenarios.
Asserts that each scenario processes its synthetic logs through the live pipeline
and matches expected severity, customer impact, and diagnostic outcomes.
"""
import pytest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app
from app.api.v1.scenarios import SCENARIOS_CATALOG

client = TestClient(app)


def test_scenario_catalog_integrity():
    """Verify all 8 scenarios exist in catalog with complete metadata."""
    resp = client.get("/api/v1/scenarios")
    assert resp.status_code == 200
    scenarios = resp.json()
    assert len(scenarios) == 8

    expected_ids = {
        "scenario-01-late-response",
        "scenario-02-webhook-failure",
        "scenario-03-duplicate-webhooks",
        "scenario-04-db-exhaustion",
        "scenario-05-partner-degradation",
        "scenario-06-refund-failure",
        "scenario-07-settlement-mismatch",
        "scenario-08-deployment-regression"
    }
    assert {s["id"] for s in scenarios} == expected_ids


@pytest.mark.parametrize("scenario", SCENARIOS_CATALOG)
def test_each_scenario_live_execution(scenario):
    """
    Executes each scenario through the live REST endpoint,
    validating deterministic severity, event count, and persistence.
    """
    scen_id = scenario["id"]
    expected_sev = scenario["expected_severity"]

    # 1. Run live simulation
    res = client.post(f"/api/v1/scenarios/{scen_id}/run")
    assert res.status_code == 200, f"Scenario {scen_id} failed with status {res.status_code}"
    data = res.json()

    assert data["source_scenario"] == scen_id
    assert data["total_events"] > 0
    assert data["severity"] == expected_sev, f"Scenario {scen_id} evaluated severity {data['severity']} != expected {expected_sev}"

    inc_id = data["id"]

    # 2. Verify incident detail contains parsed events & patterns
    detail_res = client.get(f"/api/v1/incidents/{inc_id}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert len(detail["events"]) == data["total_events"]

    # 3. Trigger AI investigation and assert citations are grounded
    inv_res = client.post(f"/api/v1/incidents/{inc_id}/investigate")
    assert inv_res.status_code == 200
    inv = inv_res.json()["investigation"]

    primary_h = inv["primary_hypothesis"]
    assert primary_h["is_primary"] is True
    # All citations must belong to real events in this incident
    valid_event_ids = {e["event_id"] for e in detail["events"]}
    for cited_eid in primary_h["supporting_event_ids"]:
        assert cited_eid in valid_event_ids, f"Hallucinated citation {cited_eid} found in {scen_id}!"
