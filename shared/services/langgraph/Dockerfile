FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy shared dependencies
COPY agents/_shared /app/agents/_shared

# Copy agent source code (needed for workflow imports)
COPY agents/feature-dev/src /app/agents/feature-dev
COPY agents/code-review/src /app/agents/code-review
COPY agents/infrastructure/src /app/agents/infrastructure
COPY agents/cicd/src /app/agents/cicd
COPY agents/documentation/src /app/agents/documentation
COPY agents/orchestrator/src /app/agents/orchestrator

# Copy LangGraph service
COPY services/langgraph /app/services/langgraph

# Install Python dependencies
RUN pip install --no-cache-dir -r services/langgraph/requirements.txt

# Install shared dependencies (Gradient, MCP, etc.)
RUN pip install --no-cache-dir \
    gradient>=1.0.0 \
    langfuse>=2.0.0 \
    httpx>=0.27.0 \
    pyyaml>=6.0

# Expose port
EXPOSE 8009

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8009/health')"

# Run FastAPI server
CMD ["python", "-m", "services.langgraph.main"]
