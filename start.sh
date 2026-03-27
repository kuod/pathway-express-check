#!/usr/bin/env bash
set -e

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"

# ── Backend ──────────────────────────────────────────────────────────────────
echo "Setting up backend..."
cd "$REPO_ROOT/backend"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt --quiet

echo "Starting backend on http://localhost:8000 ..."
uvicorn app.main:app --reload --port 8000 &
BACKEND_PID=$!

# ── Frontend ─────────────────────────────────────────────────────────────────
echo "Setting up frontend..."
cd "$REPO_ROOT/frontend"
npm install --silent

echo "Starting frontend on http://localhost:5173 ..."
echo ""
echo "Press Ctrl-C to stop both services."

cleanup() {
    echo ""
    echo "Stopping backend (PID $BACKEND_PID)..."
    kill "$BACKEND_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

npm run dev
