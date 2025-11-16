FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy shared dependencies
COPY agents/_shared /app/agents/_shared
COPY agents/feature-dev /app/agents/feature-dev
COPY agents/code-review /app/agents/code-review
COPY agents/infrastructure /app/agents/infrastructure
COPY agents/cicd /app/agents/cicd
COPY agents/documentation /app/agents/documentation
COPY agents/feature_dev /app/agents/feature_dev
COPY agents/code_review /app/agents/code_review

# Copy LangGraph workflow
COPY agents/langgraph /app/agents/langgraph

# Install Python dependencies
RUN pip install --no-cache-dir -r agents/langgraph/requirements.txt

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
CMD ["python", "-m", "agents.langgraph.main"]
