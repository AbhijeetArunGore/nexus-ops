#!/usr/bin/env bash
# Run NEXUS Ops Locally on Linux / macOS
set -e

echo "=========================================================="
echo "  NEXUS Ops — Payment Reliability & Incident Intelligence "
echo "=========================================================="

echo "[1/2] Starting Backend API on http://localhost:8000..."
(cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000) &
BACKEND_PID=$!

echo "[2/2] Starting Frontend Vite Dev Server on http://localhost:5173..."
cd frontend && npm run dev

trap "kill $BACKEND_PID" EXIT
