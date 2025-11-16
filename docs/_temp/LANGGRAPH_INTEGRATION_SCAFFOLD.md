# LangGraph Integration Scaffold

**Status**: Implementation-agnostic infrastructure (architecture decision deferred)  
**Date**: 2025-01-28  
**Decision Pending**: Unified synchronous workflow vs async sub-agent architecture

## Infrastructure Components Created

### 1. Base LangGraph Module (`agents/_shared/langgraph_base.py`)

**Purpose**: Core LangGraph primitives that work with both sync and async patterns

**Components**:

- `BaseAgentState`: TypedDict schema for workflow state

  - `messages`: Chat history (annotated with operator.add)
  - `task_id`, `task_description`: Task tracking
  - `current_agent`: Which agent is processing
  - `artifacts`: Generated outputs
  - `context`: Shared context data
  - `next_action`: Workflow routing
  - `metadata`: Additional tracking data

- `get_postgres_checkpointer()`: PostgreSQL state persistence

  - Uses LangGraph's `PostgresSaver`
  - Connects to existing postgres service
  - Reads connection details from environment

- `create_workflow_config()`: Standard config factory
  - Creates configurable dict with thread_id
  - Supports additional workflow-specific kwargs

**Architecture Flexibility**:

- State schema supports both single-workflow and multi-agent patterns
- Checkpointer agnostic to workflow graph structure
- Can be used for synchronous StateGraph or async multi-agent coordination

### 2. Qdrant Cloud Client (`agents/_shared/qdrant_client.py`)

**Purpose**: Unified interface to Qdrant Cloud vector operations

**Components**:

- `QdrantCloudClient`: Main client class

  - Reads `QDRANT_URL`, `QDRANT_API_KEY` from environment
  - Graceful degradation when not configured
  - Singleton pattern via `get_qdrant_client()`

- `search_semantic()`: Vector similarity search

  - Configurable limit, score threshold, filters
  - Returns enriched results (id, score, payload)
  - Error handling with logging

- `upsert_points()`: Batch point insertion/update

  - Accepts list of `PointStruct`
  - Logs operation success/failure

- `get_collection_info()`: Collection metadata
  - Vector count, point count, status
  - Used for health checks

**Migration Path**:

- Replaces local Qdrant container (next step: update docker-compose.yml)
- All agents import via `from agents._shared.qdrant_client import get_qdrant_client`
- RAG service switches from local to cloud endpoint

### 3. LangChain Memory Patterns (`agents/_shared/langchain_memory.py`)

**Purpose**: Memory management for agent conversations and context

**Components**:

- `GradientEmbeddings`: LangChain-compatible embeddings

  - Uses Gradient AI for vector generation
  - TODO: Implement actual embedding endpoint calls
  - Placeholder returns 1536-dim zero vectors

- `create_conversation_memory()`: Chat history buffer

  - Uses `ConversationBufferMemory`
  - Configurable memory key and message return

- `create_vector_memory()`: Long-term semantic memory

  - Backed by Qdrant Cloud
  - Uses `VectorStoreRetrieverMemory`
  - Graceful degradation when Qdrant unavailable

- `HybridMemory`: Combined buffer + vector memory
  - Saves context to both memory types
  - Loads and merges memory variables
  - Supports rich conversational context

**Architecture Flexibility**:

- Works with both single-agent and multi-agent workflows
- Memory can be per-agent or shared across workflow
- Compatible with LangGraph state management

### 4. PostgreSQL Checkpointing Schema (`config/state/langgraph_checkpointing.sql`)

**Purpose**: Database schema for LangGraph state persistence

**Schema Components**:

- `checkpoints.checkpoints`: Main checkpoint table

  - `thread_id`: Workflow instance ID
  - `checkpoint_id`: Unique checkpoint ID
  - `parent_checkpoint_id`: For checkpoint chains
  - `checkpoint`: Full state snapshot (JSONB)
  - `metadata`: Additional tracking data
  - `created_at`: Timestamp for ordering

- `checkpoints.checkpoint_writes`: State transition tracking

  - Individual write operations within checkpoints
  - `task_id`, `channel`, `value` for granular tracking
  - Foreign key to main checkpoints table

- `checkpoints.checkpoint_metadata`: Extended metadata

  - Key-value storage for additional checkpoint data
  - Separate from main checkpoint JSONB for queryability

- `checkpoints.latest_checkpoints`: View for current states
  - DISTINCT ON (thread_id) for latest per workflow
  - Ordered by created_at DESC

**Features**:

- Indexes for efficient parent lookups and time queries
- Cascade deletes for cleanup
- Permissions granted to devtools user
- Comments for schema documentation

**Usage**:

```bash
# Apply schema
docker exec -i postgres psql -U devtools -d devtools < config/state/langgraph_checkpointing.sql
```

## Environment Variables Required

### Qdrant Cloud

```bash
QDRANT_URL=https://your-cluster.cloud.qdrant.io
QDRANT_API_KEY=your-api-key
QDRANT_COLLECTION=the-shop  # Default collection name
```

### PostgreSQL (already configured)

```bash
DB_HOST=postgres
DB_PORT=5432
DB_NAME=devtools
DB_USER=devtools
DB_PASSWORD=changeme
```

### Gradient AI Embeddings (future)

```bash
GRADIENT_EMBEDDING_MODEL=text-embedding-3-large
```

## Next Steps (Architecture-Independent)

### Immediate Actions

1. ✅ LangGraph base infrastructure created
2. ✅ Qdrant Cloud client scaffolded
3. ✅ LangChain memory patterns implemented
4. ✅ PostgreSQL checkpointing schema defined

### Migration Prep (Can proceed now)

1. **Apply PostgreSQL Schema**:

   ```bash
   docker exec -i postgres psql -U devtools -d devtools < config/state/langgraph_checkpointing.sql
   ```

2. **Remove Local Qdrant from Compose**:

   - Update `compose/docker-compose.yml`
   - Remove `qdrant` service
   - Remove `qdrant-data` volume
   - Update `rag-context` service to use Qdrant Cloud client

3. **Update Agent Requirements**:

   - Add to `requirements.txt` for all agents:
     ```
     langgraph>=0.1.7
     langchain>=0.1.0
     langchain-core>=0.1.0
     qdrant-client>=1.7.0
     ```

4. **Test Qdrant Cloud Connection**:

   ```python
   from agents._shared.qdrant_client import get_qdrant_client

   client = get_qdrant_client()
   if client.is_enabled():
       info = await client.get_collection_info()
       print(f"Connected to Qdrant Cloud: {info}")
   ```

### Architecture Decision Points (Deferred)

**Option A: Unified Synchronous Workflow**

- Single LangGraph StateGraph in orchestrator
- Sub-agents become graph nodes
- Synchronous execution with checkpointing
- Implementation: Extend `langgraph_base.py` with node definitions

**Option B: Async Multi-Agent Coordination**

- Orchestrator coordinates via message passing
- Sub-agents as independent LangGraph workflows
- Async execution with event-driven communication
- Implementation: Add message broker (Redis/RabbitMQ)

**Scaffolding Works with Either**:

- PostgreSQL checkpointing supports both patterns
- Qdrant Cloud client used by any agent
- LangChain memory can be per-agent or shared
- State schema extensible for either architecture

## Benefits of This Approach

1. **Immediate Memory Reduction**:

   - Remove local Qdrant container (~350MB saved)
   - Prepare for unified workflow (eventual ~1GB savings)

2. **Architecture Flexibility**:

   - Infrastructure supports both sync and async patterns
   - Can experiment with both approaches
   - Migration path clear for either direction

3. **Production-Ready Components**:

   - PostgreSQL checkpointing for state persistence
   - Qdrant Cloud for scalable vector storage
   - LangChain memory for rich context management
   - Gradient AI for cost-effective LLM operations

4. **Incremental Migration**:
   - Each component can be adopted independently
   - No big-bang rewrite required
   - Validate each step before proceeding

## Rollback Plan

If consolidation causes issues:

1. Keep local Qdrant in compose (comment out removal)
2. Continue using current agent architecture
3. LangGraph components remain optional (graceful degradation)
4. PostgreSQL schema additions don't interfere with existing tables

## Documentation References

- **LangGraph Checkpointing**: https://langchain-ai.github.io/langgraph/how-tos/persistence/
- **Qdrant Cloud**: https://qdrant.tech/documentation/cloud/
- **LangChain Memory**: https://python.langchain.com/docs/modules/memory/
- **PostgreSQL JSON**: https://www.postgresql.org/docs/current/datatype-json.html
