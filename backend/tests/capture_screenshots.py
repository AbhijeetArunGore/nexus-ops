"""
NEXUS Ops — Automated Application Screenshot Capture Utility
Uses Playwright to spin up FastAPI backend and Vite frontend preview,
navigates to the 6 primary operational views, and captures high-resolution
PNG screenshots for documentation in docs/assets/screenshots/.
"""
import subprocess
import time
import sys
import os
import urllib.request
import json
from playwright.sync_api import sync_playwright

os.environ["NO_PROXY"] = "127.0.0.1,localhost"

FRONTEND_URL = "http://127.0.0.1:5173"
BACKEND_URL = "http://127.0.0.1:8000"
OUTPUT_DIR = os.path.abspath("docs/assets/screenshots")


def wait_for_url(url: str, timeout: int = 20) -> bool:
    start = time.time()
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    while time.time() - start < timeout:
        try:
            r = opener.open(url, timeout=2)
            if r.status in [200, 304]:
                return True
        except Exception:
            time.sleep(0.5)
    return False


def capture_all_screenshots():
    print("=" * 70)
    print("  NEXUS Ops — Application Screenshot Capture")
    print("=" * 70)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 1. Start FastAPI Backend
    env = os.environ.copy()
    env["PYTHONPATH"] = os.path.abspath("backend")
    env["NO_PROXY"] = "127.0.0.1,localhost"
    print("\n[INIT] Starting FastAPI Backend on port 8000...")
    backend_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--port", "8000", "--host", "127.0.0.1"],
        cwd="backend",
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    if not wait_for_url(f"{BACKEND_URL}/api/v1/health", timeout=15):
        backend_proc.terminate()
        raise RuntimeError("FastAPI Backend failed to become healthy within 15 seconds.")
    print("  -> Backend is healthy.")

    # 2. Start Vite Frontend Preview
    print("\n[INIT] Starting Vite Frontend Preview on port 5173...")
    frontend_proc = subprocess.Popen(
        ["cmd.exe", "/c", "npx", "vite", "preview", "--port", "5173", "--host", "127.0.0.1"],
        cwd="frontend",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    if not wait_for_url(FRONTEND_URL, timeout=15):
        frontend_proc.terminate()
        backend_proc.terminate()
        raise RuntimeError("Vite Frontend failed to respond within 15 seconds.")
    print("  -> Frontend is ready.\n")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1440, "height": 900})
            page = context.new_page()

            # Create an active incident for workspace screenshots
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            req = urllib.request.Request(
                f"{BACKEND_URL}/api/v1/scenarios/scenario-04-db-exhaustion/run",
                data=b"",
                method="POST"
            )
            resp = opener.open(req)
            incident_data = json.loads(resp.read().decode("utf-8"))
            incident_id = incident_data["id"]
            print(f"[SETUP] Created reference incident: {incident_id} (Scenario 04: DB Pool Exhaustion)")

            # -------------------------------------------------------------
            # Screenshot 1: Operations Dashboard
            # -------------------------------------------------------------
            print("[1/6] Capturing Operations Dashboard...")
            page.goto(FRONTEND_URL)
            page.wait_for_selector("h1")
            page.wait_for_timeout(1000)
            page.screenshot(path=os.path.join(OUTPUT_DIR, "01_operations_dashboard.png"))
            print("  -> Saved docs/assets/screenshots/01_operations_dashboard.png")

            # -------------------------------------------------------------
            # Screenshot 2: Log Investigator
            # -------------------------------------------------------------
            print("[2/6] Capturing Log Investigator...")
            page.goto(f"{FRONTEND_URL}/investigate")
            page.wait_for_selector("textarea")
            sample_snippet = (
                "2026-11-18T10:20:00.050Z [order-db] WARN HikariPool-1 active connections=98/100 idle=0 pending_threads=15\n"
                "2026-11-18T10:20:01.120Z [order-db] ERROR remaining connection slots are reserved for non-replication superuser connections\n"
                "2026-11-18T10:20:02.200Z [payment-orchestrator] ERROR DatabaseConnectionError: Connection acquisition timed out after 30000ms txn_id=SYN-TXN-9004\n"
                "2026-11-18T10:20:03.100Z [payment-api] ERROR InternalServerError: Downstream dependency order-db unreachable HTTP 500"
            )
            page.fill("textarea", sample_snippet)
            page.wait_for_timeout(600)
            page.screenshot(path=os.path.join(OUTPUT_DIR, "02_log_investigator.png"))
            print("  -> Saved docs/assets/screenshots/02_log_investigator.png")

            # -------------------------------------------------------------
            # Screenshot 3: Incident Workspace
            # -------------------------------------------------------------
            print("[3/6] Capturing Incident Workspace...")
            page.goto(f"{FRONTEND_URL}/incidents/{incident_id}")
            page.wait_for_selector("text=CRITICAL")
            page.wait_for_timeout(1000)
            page.screenshot(path=os.path.join(OUTPUT_DIR, "03_incident_workspace.png"))
            print("  -> Saved docs/assets/screenshots/03_incident_workspace.png")

            # -------------------------------------------------------------
            # Screenshot 4: Evidence Graph
            # -------------------------------------------------------------
            print("[4/6] Capturing Evidence Graph...")
            # Click the Evidence Graph tab button
            graph_tab = page.locator("button:has-text('Evidence Graph')")
            if graph_tab.count() > 0:
                graph_tab.click()
                page.wait_for_timeout(1000)
            page.screenshot(path=os.path.join(OUTPUT_DIR, "04_evidence_graph.png"))
            print("  -> Saved docs/assets/screenshots/04_evidence_graph.png")

            # -------------------------------------------------------------
            # Screenshot 5: Payment Reliability Lab
            # -------------------------------------------------------------
            print("[5/6] Capturing Payment Reliability Lab...")
            page.goto(f"{FRONTEND_URL}/lab")
            page.wait_for_selector("h1")
            page.wait_for_timeout(800)
            page.screenshot(path=os.path.join(OUTPUT_DIR, "05_payment_reliability_lab.png"))
            print("  -> Saved docs/assets/screenshots/05_payment_reliability_lab.png")

            # -------------------------------------------------------------
            # Screenshot 6: Ops Knowledge Copilot
            # -------------------------------------------------------------
            print("[6/6] Capturing Ops Knowledge Copilot...")
            page.goto(f"{FRONTEND_URL}/copilot")
            page.wait_for_selector("input, textarea")
            input_box = page.locator("input[placeholder*='Ask'], input[type='text'], textarea").first
            input_box.fill("What is HTTP 504 and what does it mean for a payment transaction?")
            page.locator("button:has-text('Send'), button:has-text('Ask')").first.click()
            page.wait_for_timeout(1500)
            page.screenshot(path=os.path.join(OUTPUT_DIR, "06_ops_knowledge_copilot.png"))
            print("  -> Saved docs/assets/screenshots/06_ops_knowledge_copilot.png")

            browser.close()
            print("\n[SUCCESS] All 6 genuine screenshots captured successfully!")

    finally:
        print("[CLEANUP] Stopping background servers...")
        frontend_proc.terminate()
        backend_proc.terminate()


if __name__ == "__main__":
    capture_all_screenshots()
