#!/bin/bash
set -e

# Start the FastAPI server
# Native Cloud Run Gen2 volume mounts handle the GCS bucket at /app/data automatically
echo "Starting FastAPI server on port $PORT..."
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}
