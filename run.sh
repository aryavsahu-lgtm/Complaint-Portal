#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/backend"

# Ensure port 5001 is free before starting to prevent 'Address already in use'
PORT=5001
OCCUPIED_PID=$(lsof -ti :$PORT 2>/dev/null)
if [ -n "$OCCUPIED_PID" ]; then
    echo "Freeing occupied port $PORT (PID $OCCUPIED_PID)..."
    kill -9 $OCCUPIED_PID 2>/dev/null || true
    sleep 1
fi

if [ -f "../.venv/bin/python3" ]; then
    echo "Starting Smart Complaint System using .venv on http://127.0.0.1:$PORT..."
    exec ../.venv/bin/python3 -u app.py
else
    echo "Starting Smart Complaint System on http://127.0.0.1:$PORT..."
    exec python3 -u app.py
fi
