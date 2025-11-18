# Qdrant Cloud Collections

This document describes the Qdrant Cloud collections used for memory, context management, and RAG operations across the Dev-Tools agent system.

## Connection Configuration

**Cluster**: `83b61795-7dbd-4477-890e-edce352a00e2.us-east4-0.gcp.cloud.qdrant.io`  
**Region**: GCP US-East4  
**Authentication**: JWT token (`QDRANT_CLUSTER_KEY`)

### Environment Variables

```bash
# Cluster connection (set in config/env/.env)
QDRANT_CLUSTER_ID=83b61795-7dbd-4477-890e-edce352a00e2
QDRANT_CLUSTER_ENDPOINT=https://83b61795-7dbd-4477-890e-edce352a00e2.us-east4-0.gcp.cloud.qdrant.io
QDRANT_CLUSTER_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.et1YNe6_k9mcf7B47VN63WpQYvhaOk74ZQnP-zdgV0E

# Derived variables
QDRANT_URL=${QDRANT_CLUSTER_ENDPOINT}
QDRANT_API_KEY=${QDRANT_CLUSTER_KEY}  # Uses JWT token, NOT QDRANT_CLOUD_API_KEY
QDRANT_COLLECTION=the-shop
QDRANT_VECTOR_SIZE=1536
QDRANT_DISTANCE=cosine
```

**Important**: `QDRANT_API_KEY` must reference `QDRANT_CLUSTER_KEY` (JWT token), not `QDRANT_CLOUD_API_KEY` (UUID format).

## Collection Schema

All collections use:

- **Vector dimensions**: 1536 (OpenAI text-embedding-3-large compatible)
- **Distance metric**: Cosine similarity
- **Embeddings**: DigitalOcean Gradient AI (`GRADIENT_EMBEDDING_MODEL=text-embedding-3-large`)

### 1. `the-shop` (Primary Knowledge Base)

**Purpose**: Main production knowledge base containing workspace documentation, code context, and architectural patterns.

**Content**:

- Repository documentation (README, ARCHITECTURE, etc.)
- Code snippets and examples
- Configuration patterns
- Deployment procedures
- Best practices and conventions

**Used by**:

- RAG Context Manager (`services/rag/main.py`)
- All agents for context retrieval
- KB sync script (`scripts/sync_kb_to_qdrant.py`)

**Update strategy**: Synced from DigitalOcean Knowledge Base via `DIGITALOCEAN_KB_UUID=3120c1c2-c1c0-11f0-b074-4e013e2ddde4`

**Configuration**: `config/rag/indexing.yaml`

### 2. `agent_memory` (Conversation History)

**Purpose**: Stores agent conversation history and episodic memory for context continuity across sessions.

**Content**:

- User-agent conversation turns
- Session context and state
- Interaction patterns
- Feedback and corrections

**Used by**:

- LangChain memory wrapper (`shared/lib/langchain_memory.py`)
- LangGraph checkpointing system
- All agents for maintaining conversation context

**Payload schema**:

```json
{
  "content": "conversation message or summary",
  "agent_name": "orchestrator|feature-dev|code-review|etc",
  "session_id": "uuid",
  "timestamp": "ISO8601",
  "message_type": "user|assistant|system",
  "metadata": {
    "task_id": "optional",
    "user_id": "optional"
  }
}
```

### 3. `task_context` (Task Management)

**Purpose**: Task-specific context including requirements, execution history, and intermediate results.

**Content**:

- Task decomposition trees
- Subtask specifications
- Execution logs and outcomes
- Dependencies and blockers
- Review feedback

**Used by**:

- Orchestrator agent (task planning)
- Feature-dev agent (implementation context)
- Code-review agent (review criteria)

**Payload schema**:

```json
{
  "content": "task description or outcome",
  "task_id": "uuid",
  "parent_task_id": "optional uuid",
  "status": "pending|in_progress|completed|failed",
  "assigned_agent": "agent name",
  "timestamp": "ISO8601",
  "metadata": {
    "priority": "low|medium|high",
    "estimated_hours": "float",
    "dependencies": ["task_id1", "task_id2"]
  }
}
```

### 4. `code_patterns` (Code Knowledge)

**Purpose**: Reusable code snippets, architectural patterns, and implementation templates.

**Content**:

- Code examples and boilerplate
- Design patterns (Singleton, Factory, etc.)
- Framework-specific patterns (FastAPI, LangGraph, etc.)
- Anti-patterns and gotchas
- Performance optimizations

**Used by**:

- Feature-dev agent (code generation)
- Code-review agent (pattern validation)
- Documentation agent (example generation)

**Payload schema**:

```json
{
  "content": "code snippet or pattern description",
  "language": "python|javascript|typescript|bash|etc",
  "pattern_type": "design_pattern|idiom|template|example",
  "framework": "optional framework name",
  "tags": ["tag1", "tag2"],
  "source_file": "optional file path",
  "metadata": {
    "complexity": "simple|moderate|complex",
    "use_case": "description"
  }
}
```

### 5. `feature_specs` (Requirements)

**Purpose**: Feature specifications, PRDs (Product Requirements Documents), and detailed requirements.

**Content**:

- Feature descriptions and acceptance criteria
- User stories and use cases
- Technical specifications
- API contracts
- UI/UX requirements

**Used by**:

- Orchestrator agent (task decomposition)
- Feature-dev agent (implementation guidance)
- Documentation agent (spec documentation)

**Payload schema**:

```json
{
  "content": "feature specification text",
  "feature_id": "uuid or string",
  "title": "feature name",
  "status": "draft|approved|implemented",
  "priority": "p0|p1|p2|p3",
  "metadata": {
    "author": "user or agent",
    "approver": "optional",
    "epic": "optional parent feature",
    "target_release": "optional version"
  }
}
```

### 6. `issue_tracker` (Linear Integration)

**Purpose**: Linear issues, bugs, and project management context synced from Linear workspace.

**Content**:

- Issue descriptions and comments
- Bug reports and reproduction steps
- Project milestones and cycles
- Team member assignments
- Status updates

**Used by**:

- CICD agent (deployment validation)
- Code-review agent (issue context)
- Documentation agent (changelog generation)
- Orchestrator (issue-to-task mapping)

**Payload schema**:

```json
{
  "content": "issue description and comments",
  "issue_id": "linear issue identifier",
  "title": "issue title",
  "status": "backlog|todo|in_progress|done|canceled",
  "issue_type": "bug|feature|improvement|task",
  "assignee": "team member",
  "labels": ["label1", "label2"],
  "metadata": {
    "project_id": "linear project uuid",
    "cycle_id": "optional cycle uuid",
    "priority": "0-4",
    "estimate": "points or hours",
    "url": "linear issue URL"
  }
}
```

## Management Scripts

### Initialize Collections

Creates all collections with proper schema:

```bash
# Local (uses config/env/.env)
python scripts/init_qdrant_collections.py

# Droplet
ssh do-mcp-gateway "cd /opt/Dev-Tools && python3 scripts/init_qdrant_collections.py"
```

### Verify Connection

```bash
# Test connectivity
python scripts/test_qdrant_cloud.py

# Inside Docker container
docker exec compose-rag-context-1 python /app/test_qdrant_cloud.py
```

### Sync Knowledge Base

Syncs DigitalOcean Knowledge Base exports into `the-shop` collection:

```bash
# Trigger new indexing job and sync
python scripts/sync_kb_to_qdrant.py --start-job --kb-ref the-shop

# Sync latest completed job
python scripts/sync_kb_to_qdrant.py --kb-ref the-shop

# Dry-run (download without upserting)
python scripts/sync_kb_to_qdrant.py --dry-run --kb-ref the-shop
```

## Usage Patterns

### Agent Memory (LangChain Integration)

```python
from agents._shared.langchain_memory import create_vector_memory

# Create vector memory for agent
memory = create_vector_memory(
    collection_name="agent_memory",
    search_kwargs={"k": 5}
)

# Automatically stores conversation context
memory.save_context(
    {"input": "User message"},
    {"output": "Agent response"}
)

# Retrieve relevant history
history = memory.load_memory_variables({"input": "Current message"})
```

### RAG Context Retrieval

```python
import httpx

# Query for relevant context
response = httpx.post("http://rag-context:8007/query", json={
    "query": "How do I implement FastAPI authentication?",
    "collection": "code_patterns",
    "n_results": 5,
    "metadata_filter": {"language": "python", "framework": "fastapi"}
})

results = response.json()["results"]
for item in results:
    print(f"Relevance: {item['relevance_score']:.2f}")
    print(f"Content: {item['content'][:200]}...")
```

### Direct Qdrant Client

```python
from agents._shared.qdrant_client import get_qdrant_client

client = get_qdrant_client()

# Semantic search
results = await client.search_semantic(
    query_vector=embedding_vector,
    limit=10,
    score_threshold=0.7,
    filter_conditions=Filter(...)
)

# Upsert points
await client.upsert_points([
    PointStruct(
        id="point-id",
        vector=embedding,
        payload={"content": "...", "metadata": {...}}
    )
])
```

## Monitoring & Maintenance

### Collection Stats

```python
from qdrant_client import QdrantClient

client = QdrantClient(
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY")
)

for collection_name in ["the-shop", "agent_memory", "task_context", ...]:
    info = client.get_collection(collection_name)
    print(f"{collection_name}: {info.points_count} points, {info.vectors_count} vectors")
```

### Cleanup Old Points

```python
# Delete points older than 30 days
from datetime import datetime, timedelta

cutoff = (datetime.utcnow() - timedelta(days=30)).isoformat()

client.delete(
    collection_name="agent_memory",
    points_selector=Filter(
        must=[
            FieldCondition(
                key="timestamp",
                range=DatetimeRange(lt=cutoff)
            )
        ]
    )
)
```

## Cost & Performance

- **Storage**: Free tier includes 1GB vector storage (~350K points @ 1536 dims)
- **Query latency**: <50ms within DO network, <200ms external
- **Throughput**: 100 QPS on free tier
- **Memory savings**: 350MB vs local Qdrant container

## Troubleshooting

### 403 Forbidden Errors

**Cause**: Wrong API key format (UUID instead of JWT token)

**Fix**: Ensure `QDRANT_API_KEY` references `QDRANT_CLUSTER_KEY` (JWT), not `QDRANT_CLOUD_API_KEY`

```bash
# Correct
QDRANT_API_KEY=${QDRANT_CLUSTER_KEY}

# Incorrect
QDRANT_API_KEY=${QDRANT_CLOUD_API_KEY}
```

### Collection Not Found

**Cause**: Collection not created yet

**Fix**: Run initialization script

```bash
python scripts/init_qdrant_collections.py
```

### Empty Search Results

**Cause**: Collection exists but has no indexed data

**Fix**:

1. For `the-shop`: Run KB sync script
2. For agent collections: Agents will populate automatically during use
3. Check embedding model compatibility (must be 1536 dimensions)

### Connection Timeouts

**Cause**: Network issues or incorrect endpoint

**Fix**: Verify cluster endpoint and test connectivity

```bash
curl -H "api-key: ${QDRANT_CLUSTER_KEY}" \
  "https://83b61795-7dbd-4477-890e-edce352a00e2.us-east4-0.gcp.cloud.qdrant.io/collections"
```

## References

- **Qdrant Cloud Dashboard**: https://cloud.qdrant.io/
- **Qdrant API Docs**: https://qdrant.tech/documentation/
- **Collection Config**: `config/rag/vectordb.config.yaml`
- **Indexing Config**: `config/rag/indexing.yaml`
- **Shared Client**: `shared/lib/qdrant_client.py`
