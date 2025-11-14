<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# Recommended Stack for Your Setup

generate step by step for tier 1 and 2 recommendations (FastAPI + Docker + Ollama)

Here’s a step-by-step guide for integrating the **Tier 1 and Tier 2 recommended open-source observability stack** with your existing FastAPI + Docker + Ollama agents. This stack provides full LLM tracing, metrics, and dashboards, all self-hosted with minimal footprint.

***

## Tier 1: Must-Have Observability

### 1. Langfuse (LLM Tracing, Prompt Management, Token Analytics)

#### Step 1: Add Langfuse and PostgreSQL to Your Docker Compose

```yaml
# docker-compose.yml
services:
  langfuse-server:
    image: langfuse/langfuse:latest
    ports: ["3000:3000"]
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@postgres:5432/langfuse
      - NEXTAUTH_SECRET=your_super_secret
      - NEXTAUTH_URL=http://localhost:3000
      - TELEMETRY_ENABLED=false
    depends_on: [langfuse-db]
    restart: unless-stopped

  langfuse-db:
    image: postgres:16-alpine
    environment:
      - POSTGRES_DB=langfuse
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
    volumes:
      - langfuse-db:/var/lib/postgresql/data
    restart: unless-stopped

volumes:
  langfuse-db:
```


#### Step 2: Install Langfuse Python SDK in Each Agent

```sh
pip install langfuse
```


#### Step 3: Initialize Langfuse in Each Agent

```python
from langfuse import Langfuse

langfuse = Langfuse(
    host="http://langfuse-server:3000",
    public_key="your-public-key",
    secret_key="your-secret-key"
)
```

Generate API keys in the Langfuse web UI after starting the server.

#### Step 4: Add Automatic Tracing

Decorate key FastAPI routes and agent functions:

```python
from langfuse.decorators import observe

@app.post("/orchestrate")
@observe()
async def orchestrate_task(request: TaskRequest):
    ...
```


***

### 2. Prometheus (System Metrics Collection)

#### Step 1: Add Prometheus Service

Add to your `docker-compose.yml`:

```yaml
services:
  prometheus:
    image: prom/prometheus:latest
    ports: ["9090:9090"]
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    restart: unless-stopped
```


#### Step 2: Create Prometheus Config

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'ollama'
    static_configs:
      - targets: ['ollama:11434']

  - job_name: 'langfuse'
    static_configs:
      - targets: ['langfuse-server:3000']

  - job_name: 'agents'
    static_configs:
      - targets: ['orchestrator:8001','feature-dev:8002', 'code-review:8003']
```


#### Step 3: Enable Prometheus Exporter in Your Agents

- Use a library like `prometheus_fastapi_instrumentator`:

```sh
pip install prometheus-fastapi-instrumentator
```

- Add to your FastAPI code:

```python
from prometheus_fastapi_instrumentator import Instrumentator
app = FastAPI()
Instrumentator().instrument(app).expose(app)
```


***

## Tier 2: Nice-to-Have Additions

### 3. Grafana (Visualization Dashboards)

#### Step 1: Add Grafana to Docker Compose

```yaml
services:
  grafana:
    image: grafana/grafana:latest
    ports: ["3001:3000"]
    environment:
      - GF_AUTH_ANONYMOUS_ENABLED=true
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana-data:/var/lib/grafana
    restart: unless-stopped

volumes:
  grafana-data:
```


#### Step 2: Connect Grafana to Prometheus

- Log in at `http://localhost:3001` (admin/admin).
- Add Prometheus as a data source (URL: `http://prometheus:9090`).
- Import ready-made community dashboards for FastAPI, CPU, memory, or LLM tracing.

***

### 4. OpenTelemetry Collector (Distributed Tracing Backbone, Optional)

#### Step 1: Add OTEL Collector to Docker Compose

```yaml
services:
  otel-collector:
    image: otel/opentelemetry-collector-contrib:latest
    command: ["--config=/etc/otel-collector-config.yaml"]
    volumes:
      - ./otel-collector-config.yaml:/etc/otel-collector-config.yaml
    ports:
      - "4317:4317"
      - "4318:4318"
    restart: unless-stopped
```


#### Step 2: Configure Otel Collector

```yaml
# otel-collector-config.yaml
receivers:
  otlp:
    protocols:
      grpc:
      http:

exporters:
  logging:
    loglevel: debug

service:
  pipelines:
    traces:
      receivers: [otlp]
      exporters: [logging]
```


#### Step 3: Trace FastAPI Agents

- Use libraries like `opentelemetry-instrumentation-fastapi` \& `opentelemetry-sdk`

```sh
pip install opentelemetry-instrumentation-fastapi opentelemetry-sdk
```

- In each agent:

```python
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from fastapi import FastAPI

app = FastAPI()
FastAPIInstrumentor.instrument_app(app)
```


***

## Summary Table

| Stack | Step | Docker Image | Key Integration |
| :-- | :-- | :-- | :-- |
| Langfuse | Compose + SDK | langfuse/langfuse | `pip install langfuse` |
| Prometheus | Compose + Scrape Config | prom/prometheus | `prometheus-fastapi-instrumentator` |
| Grafana | Compose + Dashboards | grafana/grafana | Prometheus as data source |
| OTEL | Compose + SDK | otel/opentelemetry-collector-contrib | `opentelemetry-instrumentation-fastapi` |

This approach brings you enterprise-grade LLM and agent tracing with **minimal changes** to your FastAPI + Docker + Ollama infrastructure, all for \$0-5/month.

