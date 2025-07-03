# Multi-stage Dockerfile for Memory Leak Test Application
# Optimized for Azure Container Registry and Azure Kubernetes Service (AKS)
# Follows security best practices with minimal attack surface

# Build stage - Use official Python runtime as base image
FROM python:3.11-slim-bullseye AS builder

# Set working directory
WORKDIR /app

# Install build dependencies for psutil
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        python3-dev && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage - Minimal runtime image
FROM python:3.11-slim-bullseye AS runtime

# Metadata labels for Azure Container Registry
LABEL maintainer="Azure SRE Team"
LABEL description="Memory Leak Test Application for Kubernetes Resource Testing"
LABEL version="1.0"
LABEL org.opencontainers.image.source="https://github.com/azure-sre-agent"

# Create non-root user for security
RUN groupadd --gid 1001 appuser && \
    useradd --uid 1001 --gid appuser --shell /bin/bash --create-home appuser

# Set working directory
WORKDIR /app

# Copy Python packages from builder stage
COPY --from=builder /root/.local /home/appuser/.local

# Copy application code
COPY memory-leak-app.py .

# Set ownership to non-root user
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Add local Python packages to PATH
ENV PATH=/home/appuser/.local/bin:$PATH

# Set Python path to find modules
ENV PYTHONPATH=/home/appuser/.local/lib/python3.11/site-packages

# Environment variables with secure defaults
ENV LEAK=FALSE
ENV LEAK_RATE=1
ENV LEAK_INTERVAL=1
ENV MAX_MEMORY=500
ENV PORT=8080
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Expose application port
EXPOSE 8080

# Health check for container orchestration
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1

# Security: Run as non-root, read-only root filesystem compatible
# The application handles temporary files appropriately
USER appuser

# Start the application
CMD ["python3", "memory-leak-app.py"]
