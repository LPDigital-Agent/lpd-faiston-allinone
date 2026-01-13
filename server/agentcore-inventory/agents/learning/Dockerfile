# =============================================================================
# LearningAgent - AgentCore Runtime Dockerfile
# =============================================================================
# ARM64 container for AWS Bedrock AgentCore Runtime.
#
# Architecture: arm64 (Graviton2)
# Runtime: Python 3.13
# Protocol: A2A (JSON-RPC 2.0 on port 9000)
#
# Build:
#   docker build -t sga-learning-agent:latest -f agents/learning/Dockerfile .
#
# Reference:
#   https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-containers.html
# =============================================================================

# Use official Python 3.13 slim image for ARM64
FROM --platform=linux/arm64 python:3.13-slim

# Set working directory
WORKDIR /app

# Install system dependencies (minimal for cold start optimization)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for layer caching
COPY agents/learning/requirements.txt /app/agents/learning/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r /app/agents/learning/requirements.txt

# Copy shared infrastructure
COPY shared/ /app/shared/

# Copy agent code
COPY agents/learning/ /app/agents/learning/

# Copy tools (shared across agents)
COPY tools/ /app/tools/

# Set Python path
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Agent configuration
ENV AGENT_ID=learning
ENV AGENT_NAME=LearningAgent

# AgentCore Memory (default, can be overridden)
ENV AGENTCORE_MEMORY_ID=nexo_sga_learning_memory-u3ypElEdl1

# Expose A2A port (MANDATORY: port 9000)
EXPOSE 9000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:9000/health || exit 1

# Entry point
ENTRYPOINT ["python", "-m", "agents.learning.main"]
