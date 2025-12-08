FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy shared dependencies
COPY shared/lib /app/shared/lib

# Copy orchestrator source code (contains all LangGraph agent nodes)
COPY agent_orchestrator /app/agents/orchestrator

# Ensure agent packages are discoverable by Python
ENV PYTHONPATH=/app/agents:/app/shared/lib

# Copy LangGraph service
COPY shared/services/langgraph /app/services/langgraph

# Install Python dependencies
RUN pip install --no-cache-dir -r /app/services/langgraph/requirements.txt

# Install shared dependencies (Gradient, MCP, etc.)
RUN pip install --no-cache-dir \
    gradient>=1.0.0 \
    langfuse>=2.0.0 \
    httpx>=0.27.0 \
    pyyaml>=6.0

# Expose port (default 8010, configurable via PORT env var)
EXPOSE 8010

# Health check - uses PORT env var with fallback to 8010
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; import os; httpx.get(f'http://localhost:{os.getenv(\"PORT\", \"8010\")}/health')"

# Run FastAPI server
CMD ["python", "-m", "services.langgraph.main"]
