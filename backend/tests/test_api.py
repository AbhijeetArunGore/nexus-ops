"""
NEXUS Ops API Integration Test Suite
Validates all FastAPI REST endpoints, input constraints, security validations,
and database persistence using TestClient.
"""
import pytest
import io
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_api_health_and_readiness():
    """Verify health and readiness probes."""
    resp_health = client.get("/api/v1/health")
    assert resp_health.status_code == 200
    assert resp_health.json()["status"] == "UP"
    assert "SIMULATED ENVIRONMENT" in resp_health.json()["disclaimer"]

    resp_ready = client.get("/api/v1/ready")
    assert resp_ready.status_code == 200
    assert resp_ready.json()["status"] == "READY"
    assert resp_ready.json()["database"] == "CONNECTED"


def test_api_paste_ingestion_success_and_empty():
    """Test log paste endpoint with valid payload and empty rejection."""
    # Valid paste
    valid_payload = {
        "content": "2026-11-18T10:00:00Z [payment-api] ERROR HTTP 504 Gateway Timeout txn_id=SYN-TXN-101",
        "title": "API Test Incident"
    }
    resp = client.post("/api/v1/analyses/paste", json=valid_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["incident_number"].startswith("INC-2026-")
    assert data["total_events"] == 1
    assert data["severity"] in ["MEDIUM", "HIGH", "CRITICAL"]

    # Empty paste rejection
    resp_empty = client.post("/api/v1/analyses/paste", json={"content": "   "})
    assert resp_empty.status_code == 400
    assert "empty" in resp_empty.json()["detail"].lower()


def test_api_upload_file_validation_and_security():
    """Test file upload validation: valid text, unsupported extension, binary executable magic bytes."""
    # 1. Valid log file
    log_content = b"2026-11-18T10:00:00Z [bank-connector] WARN Socket read timeout\n"
    file_valid = ("test.log", io.BytesIO(log_content), "text/plain")
    resp_valid = client.post("/api/v1/analyses/upload", files={"file": file_valid})
    assert resp_valid.status_code == 200
    assert resp_valid.json()["total_events"] == 1

    # 2. Unsupported extension rejection (.exe, .sh, .py)
    file_bad_ext = ("payload.exe", io.BytesIO(b"echo hello"), "application/octet-stream")
    resp_bad = client.post("/api/v1/analyses/upload", files={"file": file_bad_ext})
    assert resp_bad.status_code == 400
    assert "Unsupported file format" in resp_bad.json()["detail"]

    # 3. Binary executable magic byte rejection (Windows MZ header disguised as .log)
    fake_exe = b"MZ\x90\x00\x03\x00\x00\x00some windows executable binary"
    file_fake_exe = ("malicious.log", io.BytesIO(fake_exe), "text/plain")
    resp_sec = client.post("/api/v1/analyses/upload", files={"file": file_fake_exe})
    assert resp_sec.status_code == 400
    assert "Security rejection: Uploaded file contains executable binary" in resp_sec.json()["detail"]


def test_api_incident_lifecycle_and_investigation():
    """Test full incident workflow: create, get detail, status update, investigate, feedback, postmortem."""
    # Create incident
    paste_resp = client.post("/api/v1/analyses/paste", json={
        "content": """2026-11-18T10:00:00Z [order-db] ERROR remaining connection slots are reserved
2026-11-18T10:00:01Z [payment-orchestrator] ERROR DatabaseConnectionError: Connection acquisition timed out
2026-11-18T10:00:02Z [payment-api] ERROR HTTP 500 InternalServerError from orchestrator txn_id=SYN-TXN-901""",
        "title": "Database Saturation Test"
    })
    inc_id = paste_resp.json()["id"]

    # Get detail
    detail_resp = client.get(f"/api/v1/incidents/{inc_id}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["severity"] == "CRITICAL"
    assert len(detail["events"]) == 3
    assert len(detail["patterns"]) >= 1

    # Update status to INVESTIGATING
    patch_resp = client.patch(f"/api/v1/incidents/{inc_id}/status", json={"status": "INVESTIGATING"})
    assert patch_resp.status_code == 200
    assert patch_resp.json()["status"] == "INVESTIGATING"

    # Trigger AI investigation
    inv_resp = client.post(f"/api/v1/incidents/{inc_id}/investigate")
    assert inv_resp.status_code == 200
    inv_data = inv_resp.json()["investigation"]
    assert "primary_hypothesis" in inv_data
    assert len(inv_data["primary_hypothesis"]["supporting_event_ids"]) > 0

    # Get timeline
    tl_resp = client.get(f"/api/v1/incidents/{inc_id}/timeline")
    assert tl_resp.status_code == 200
    assert "milestones" in tl_resp.json()

    # Get blast radius
    br_resp = client.get(f"/api/v1/incidents/{inc_id}/blast-radius")
    assert br_resp.status_code == 200
    assert "order-db" in br_resp.json()["observed_services"]

    # Get evidence graph
    eg_resp = client.get(f"/api/v1/incidents/{inc_id}/evidence-graph")
    assert eg_resp.status_code == 200
    assert len(eg_resp.json()["nodes"]) > 0

    # What Am I Missing
    wm_resp = client.post(f"/api/v1/incidents/{inc_id}/what-am-i-missing")
    assert wm_resp.status_code == 200
    assert len(wm_resp.json()["gaps_identified"]) > 0

    # Telemetry Gaps
    tg_resp = client.get(f"/api/v1/incidents/{inc_id}/telemetry-gaps")
    assert tg_resp.status_code == 200

    # Feedback submission
    fb_resp = client.post(f"/api/v1/incidents/{inc_id}/feedback", json={
        "verified_root_cause": "PostgreSQL connection pool exhausted by unindexed table lock",
        "hypothesis_accuracy": "VERIFIED",
        "useful_recommendations": ["Tune HikariCP pool size"]
    })
    assert fb_resp.status_code == 200
    assert fb_resp.json()["success"] is True

    # Postmortem generation
    pm_resp = client.post(f"/api/v1/incidents/{inc_id}/postmortem")
    assert pm_resp.status_code == 200
    assert "executive_summary" in pm_resp.json()["postmortem"]


def test_api_missing_incident_404():
    """Verify missing incident returns HTTP 404."""
    resp = client.get("/api/v1/incidents/nonexistent-uuid-1234")
    assert resp.status_code == 404
    assert "Incident not found" in resp.json()["detail"]


def test_api_copilot_learning_and_engineering_modes():
    """Verify Ops Copilot responds in both LEARNING and ENGINEERING modes."""
    # Learning mode
    res_learn = client.post("/api/v1/copilot/ask", json={
        "query": "What is an HTTP 504 gateway timeout?",
        "mode": "LEARNING"
    })
    assert res_learn.status_code == 200
    assert "504" in res_learn.json()["answer"]
    assert len(res_learn.json()["follow_up_questions"]) > 0

    # Engineering mode
    res_eng = client.post("/api/v1/copilot/ask", json={
        "query": "How do we inspect pg_stat_activity locks?",
        "mode": "ENGINEERING"
    })
    assert res_eng.status_code == 200
    assert "pg_stat_activity" in res_eng.json()["technical_details"]


def test_api_runbooks_search():
    """Verify runbook catalog retrieval and keyword search."""
    # List all
    all_rb = client.get("/api/v1/runbooks")
    assert all_rb.status_code == 200
    assert len(all_rb.json()) >= 10

    # Search specific procedure
    search_rb = client.get("/api/v1/runbooks?query=database")
    assert search_rb.status_code == 200
    assert any("Database" in r["title"] for r in search_rb.json())
