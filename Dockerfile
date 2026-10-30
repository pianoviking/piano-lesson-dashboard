FROM python:3.12-slim

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CONFIG_PATH=/data/config.json \
    TOKEN_PATH=/data/token.json \
    CREDENTIALS_PATH=/data/credentials.json \
    HOST=0.0.0.0 \
    PORT=5000 \
    DEBUG=false \
    OAUTH_ALLOW_BROWSER=false \
    HOME=/tmp

# Create a non-root user to run the application
RUN groupadd -g 1000 appuser && \
    useradd -u 1000 -g appuser -s /bin/sh -m appuser

# Set the working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application source code
COPY . .

# Create the persistent data directory and set ownership
RUN mkdir -p /data && chown -R appuser:appuser /data /app

# Switch to the non-root user
USER appuser

# Expose the internal port
EXPOSE 5000

# Basic healthcheck using python's built-in urllib
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/')" || exit 1

# Start the application using Gunicorn
# Single worker recommended to ensure consistent config.json updates across requests
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--timeout", "120", "--access-logfile", "-", "app:app"]
