# Use a modern Python image
FROM python:3.11-slim

# Install tini and basic system libraries for pandas/numpy
RUN apt-get update && apt-get install -y tini libstdc++6 && apt-get clean

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8080
ENV APP_HOME=/app

WORKDIR $APP_HOME

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the code
COPY . .

# Create a mount point for the persistent DB
RUN mkdir -p /app/data

# Ensure the script is executable
RUN chmod +x /app/gcp_entrypoint.sh

# Use tini as the entrypoint
ENTRYPOINT ["/usr/bin/tini", "--"]

# Run the entrypoint script
CMD ["/app/gcp_entrypoint.sh"]
