# Use a slim Python image
FROM python:3.9-slim

# Install gcsfuse and tini for signal handling and persistence
RUN apt-get update && apt-get install -y ca-certificates gcsfuse tini && apt-get clean

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8080
ENV APP_HOME /app

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
