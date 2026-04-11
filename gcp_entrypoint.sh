#!/bin/bash
set -e

# Production Entrypoint for Google Cloud Run
# Uses Gunicorn with Uvicorn workers for process management and stability.

echo "--- [GCP STARTUP] Environment: $REGION ---"
echo "--- [GCP STARTUP] Starting Gunicorn on port ${PORT:-8080} ---"

exec gunicorn app.main:app \
    --bind 0.0.0.0:${PORT:-8080} \
    --workers 1 \
    --worker-class uvicorn.workers.UvicornWorker \
    --timeout 120 \
    --log-level debug
