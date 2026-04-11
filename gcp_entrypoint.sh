#!/bin/bash
set -e

# Debug: Print current environment and structure
echo "--- [GCP STARTUP] Environment Check ---"
echo "Current Directory: $(pwd)"
echo "Port: $PORT"

echo "--- [GCP STARTUP] Python Path Check ---"
python3 -c "import sys; print(f'Python Path: {sys.path}')"

echo "--- [GCP STARTUP] Testing Module Import ---"
if python3 -c "from app.main import app; print('SUCCESS: app.main loadable')"; then
    echo "--- [GCP STARTUP] Module test passed ---"
else
    echo "--- [GCP STARTUP] Module test FAILED ---"
fi

# Start the FastAPI server
echo "--- [GCP STARTUP] Executing Uvicorn ---"
exec python3 -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080} --log-level debug
