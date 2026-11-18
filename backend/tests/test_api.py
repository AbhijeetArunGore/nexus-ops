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


def test_api_health_and_readiness(client):
    """Verify health and readiness probes."""
    resp_health = client.get("/api/v1/health")
    assert resp_health.status_code == 200
    assert resp_health.json()["status"] == "UP"
    assert "SIMULATED ENVIRONMENT" in resp_health.json()["disclaimer"]

    resp_ready = client.get("/api/v1/ready")
    assert resp_ready.status_code == 200
    assert resp_ready.json()["status"] == "READY"
    assert resp_ready.json()["database"] == "CONNECTED"


def test_api_paste_ingestion_success_and_empty(client):
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


def test_api_upload_file_validation_and_security(client):
    """Test file upload validation including binary executable rejection and valid log upload."""
    # 1. Valid log file upload
    log_content = b"2026-11-18T10:05:00Z [payment-orchestrator] WARN Retry count exhausted for partner auth"
    file_payload = {"file": ("test.log", io.BytesIO(log_content), "text/plain")}
    resp = client.post("/api/v1/analyses/upload", files=file_payload, data={"title": "Upload Test"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_events"] == 1

    # 2. Executable Windows PE (MZ) rejection
    pe_content = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00"
    file_pe = {"file": ("malicious.exe", io.BytesIO(pe_content), "application/octet-stream")}
    resp_pe = client.post("/api/v1/analyses/upload", files=file_pe)
    assert resp_pe.status_code == 400
    assert "executable binary" in resp_pe.json()["detail"].lower()

    # 3. Linux ELF rejection
    elf_content = b"\x7fELF\x02\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    file_elf = {"file": ("malicious.elf", io.BytesIO(elf_content), "application/octet-stream")}
    resp_elf = client.post("/api/v1/analyses/upload", files=file_elf)
    assert resp_elf.status_code == 400
    assert "executable binary" in resp_elf.json()["detail"].lower()

    # 4. Java Class Bytecode rejection
    class_content = b"\xca\xfe\xba\xbe\x00\x00\x00\x34"
    file_class = {"file": ("Payload.class", io.BytesIO(class_content), "application/octet-stream")}
    resp_class = client.post("/api/v1/analyses/upload", files=file_class)
    assert resp_class.status_code == 400
    assert "executable binary" in resp_class.json()["detail"].lower()


def test_api_incident_lifecycle_and_investigation(client):
    """Test full workflow: Ingest -> Retrieve -> Investigate -> Status Update."""
    # Step 1: Ingest log
    payload = {
        "content": (
            "2026-11-18T10:10:00Z [bank-connector] ERROR Acquiring bank socket closed abruptly txn_id=SYN-TXN-555\n"
            "2026-11-18T10:10:01Z [payment-api] ERROR HTTP 504 Gateway Timeout txn_id=SYN-TXN-555"
        ),
        "title": "Full Lifecycle Test Incident"
    }
    create_resp = client.post("/api/v1/analyses/paste", json=payload)
    assert create_resp.status_code == 200
    inc_data = create_resp.json()
    incident_id = inc_data["id"]

    # Step 2: Retrieve Incident Details
    detail_resp = client.get(f"/api/v1/incidents/{incident_id}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["incident_number"] == inc_data["incident_number"]
    assert len(detail["events"]) == 2

    # Step 3: Trigger AI Investigation
    inv_resp = client.post(f"/api/v1/incidents/{incident_id}/investigate")
    assert inv_resp.status_code == 200
    inv_data = inv_resp.json()
    assert inv_data["incident_number"] == inc_data["incident_number"]
    assert "primary_hypothesis" in inv_data
    assert len(inv_data["primary_hypothesis"]["supporting_event_ids"]) > 0

    # Step 4: Update Status to INVESTIGATING and RESOLVED
    status_resp = client.patch(f"/api/v1/incidents/{incident_id}/status", json={"status": "INVESTIGATING"})
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == "INVESTIGATING"

    status_resp_res = client.patch(f"/api/v1/incidents/{incident_id}/status", json={"status": "RESOLVED"})
    assert status_resp_res.status_code == 200
    assert status_resp_res.json()["status"] == "RESOLVED"
    assert status_resp_res.json()["resolved_at"] is not None


def test_api_missing_incident_404(client):
    """Test 404 behavior for nonexistent incident."""
    resp = client.get("/api/v1/incidents/nonexistent-uuid-1234")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


def test_copilot_ask_endpoint(client):
    """Test Ops Knowledge Copilot API endpoint in both Learning and Engineering modes."""
    # Learning Mode
    req_learn = {
        "query": "What is an HTTP 504 Gateway Timeout?",
        "mode": "LEARNING"
    }
    resp = client.post("/api/v1/copilot/ask", json=req_learn)
    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "LEARNING"
    assert "504" in data["answer"] or "timeout" in data["answer"].lower()

    # Engineering Mode
    req_eng = {
        "query": "How do database connection pools exhaust?",
        "mode": "ENGINEERING"
    }
    resp_eng = client.post("/api/v1/copilot/ask", json=req_eng)
    assert resp_eng.status_code == 200
    data_eng = resp_eng.json()
    assert data_eng["mode"] == "ENGINEERING"
    assert len(data_eng["suggested_actions"]) > 0


def test_runbooks_endpoint(client):
    """Test Runbook catalog retrieval and search filter."""
    resp = client.get("/api/v1/runbooks")
    assert resp.status_code == 200
    runbooks = resp.json()
    assert len(runbooks) >= 10

    # Search filter
    resp_filter = client.get("/api/v1/runbooks?query=database")
    assert resp_filter.status_code == 200
    filtered = resp_filter.json()
    assert any("database" in r["title"].lower() for r in filtered)
