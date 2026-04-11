#!/bin/bash
set -e

# Debug: Print current environment and structure
echo "--- Environment Check ---"
echo "Current Directory: $(pwd)"
echo "Port: $PORT"
ls -R .

# Start the FastAPI server
echo "--- Starting FastAPI server on port ${PORT:-8080} ---"
# Using -m app.main to ensure path resolution works as expected
exec python3 -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080} --log-level debug
