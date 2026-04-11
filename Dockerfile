# Use a slim Python image
FROM python:3.9-slim

# Install dependencies and add Google Cloud repository for gcsfuse
RUN apt-get update && apt-get install -y ca-certificates curl gnupg lsb-release tini && \
    echo "deb http://packages.cloud.google.com/apt gcsfuse-$(lsb_release -c -s) main" | tee /etc/apt/sources.list.d/gcsfuse.list && \
    curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add - && \
    apt-get update && apt-get install -y gcsfuse && \
    apt-get clean

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8080
ENV APP_HOME=/app

WORKDIR $APP_HOME

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the code
COPY . .

# Create a mount point for the persistent DB
RUN mkdir -p /app/data

# Ensure the script is executable
RUN chmod +x /app/gcp_entrypoint.sh

# Use tini as the entrypoint for better signal handling
ENTRYPOINT ["/usr/bin/tini", "--"]

# Run the entrypoint script
CMD ["/app/gcp_entrypoint.sh"]
