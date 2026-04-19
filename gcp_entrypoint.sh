#!/bin/bash
set -e

# Production Entrypoint for Google Cloud Run
# Uses Gunicorn with Uvicorn workers for process management and stability.

echo "--- [GCP STARTUP] Environment: $REGION, Mode: ${MODE:-server} ---"

if [ "$MODE" == "worker" ]; then
    echo "--- [GCP STARTUP] Starting Agent Orchestrator Worker ---"
    export PYTHONPATH=$PYTHONPATH:.
    exec python3 app/engine/agent_orchestrator.py
else
    echo "--- [GCP STARTUP] Starting Gunicorn Server ---"
    exec gunicorn app.main:app \
        --bind 0.0.0.0:${PORT:-8080} \
        --workers 1 \
        --worker-class uvicorn.workers.UvicornWorker \
        --timeout 120 \
        --log-level debug
fi
