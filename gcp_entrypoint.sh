#!/bin/bash
set -e

# Note: Cloud Run Gen2 supports mounting Cloud Storage buckets directly via configuration.
# If you prefer the manual FUSE mount approach, uncomment the lines below and ensure
# bucket name is provided via environment variable BUCKET_NAME.

# if [ -n "$BUCKET_NAME" ]; then
#     echo "Mounting GCS bucket $BUCKET_NAME to /app/data..."
#     gcsfuse -o allow_other --uid 0 --gid 0 $BUCKET_NAME /app/data
# fi

# Start the FastAPI server
echo "Starting FastAPI server on port $PORT..."
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}
