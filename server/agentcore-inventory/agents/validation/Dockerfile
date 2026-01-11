# =============================================================================
# ValidationAgent - ARM64 Container for AWS Bedrock AgentCore
# =============================================================================
# Validates data and mappings against PostgreSQL schema.
# =============================================================================

FROM --platform=linux/arm64 python:3.13-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared infrastructure
COPY ../../shared /app/shared/

# Copy agent tools
COPY tools/ /app/tools/

# Copy agent code
COPY main.py .
COPY agent.py .
COPY __init__.py .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV PORT=9000

# Expose A2A protocol port
EXPOSE 9000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:9000/health || exit 1

# Run the agent
CMD ["python", "main.py"]
