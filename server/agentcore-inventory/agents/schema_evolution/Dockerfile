# =============================================================================
# SchemaEvolutionAgent - AgentCore Runtime Dockerfile
# =============================================================================
# ARM64 container for AWS Bedrock AgentCore Runtime.
#
# Architecture: arm64 (Graviton2)
# Runtime: Python 3.13
# Protocol: A2A (JSON-RPC 2.0 on port 9000)
# =============================================================================

FROM --platform=linux/arm64 python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY agents/schema_evolution/requirements.txt /app/agents/schema_evolution/requirements.txt
RUN pip install --no-cache-dir -r /app/agents/schema_evolution/requirements.txt

COPY shared/ /app/shared/
COPY agents/schema_evolution/ /app/agents/schema_evolution/
COPY tools/ /app/tools/

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV AGENT_ID=schema_evolution
ENV AGENT_NAME=SchemaEvolutionAgent

EXPOSE 9000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:9000/health || exit 1

ENTRYPOINT ["python", "-m", "agents.schema_evolution.main"]
