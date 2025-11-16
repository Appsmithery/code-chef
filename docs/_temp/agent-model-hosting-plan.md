# **Embedding Model Hosting Analysis** - Revised for LangChain/LangGraph Architecture

## **Executive Summary**

**Recommendation:** Host embeddings via **DigitalOcean Gradient AI** and manage everything through **LangChain abstractions**. This centralizes configuration in your LangGraph workflow while keeping inference on DO infrastructure.

**Key Insight:** You don't need to "jump between platforms" - LangChain provides unified abstractions that let you manage both LLM inference AND embeddings from your LangGraph workflow code, regardless of where the actual compute happens.

---

## Current vs Proposed Architecture

### Current State (Fragmented)

LLM Inference: DO Gradient AI (gradient_client.py wrapper)
Embeddings: Mock/Unimplemented (langchain_memory.py placeholder)
Config: Split between .env files, Docker compose, agent code
Management: Manual coordination across 3 systems

### Proposed State (Unified via LangChain)

```python
# agents/langgraph/config.py - Single source of truth
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_openai import ChatOpenAI

# Both use DO Gradient AI, configured once
llm = ChatOpenAI(
    base_url="https://api.digitalocean.com/v2/ai/v1",
    api_key=os.getenv("GRADIENT_API_KEY"),
    model="llama-3.1-70b-instruct"
)

embeddings = OpenAIEmbeddings(
    base_url="https://api.digitalocean.com/v2/ai/v1",  # Same endpoint
    api_key=os.getenv("GRADIENT_API_KEY"),
    model="text-embedding-3-small"
)
```

**Result:** Manage both from LangChain, deploy both on DO Gradient, configure once in code.

---

## Revised Recommendation: Unified DO Gradient + LangChain Management

### Architecture Decision

**Use DigitalOcean Gradient AI for BOTH LLM + Embeddings**, managed via LangChain abstractions:

```python
# agents/_shared/langchain_gradient.py (REVISED)
"""
Unified LangChain configuration for DO Gradient AI
Manages both LLM inference and embeddings from single config
"""
import os
from langchain_openai import ChatOpenAI
from langchain_community.embeddings import OpenAIEmbeddings

# Single configuration source
GRADIENT_BASE_URL = "https://api.digitalocean.com/v2/ai/v1"
GRADIENT_API_KEY = os.getenv("GRADIENT_API_KEY")

def get_llm(model: str = "llama-3.1-8b-instruct", **kwargs):
    """Get LangChain LLM using DO Gradient"""
    return ChatOpenAI(
        base_url=GRADIENT_BASE_URL,
        api_key=GRADIENT_API_KEY,
        model=model,
        **kwargs
    )

def get_embeddings(model: str = "text-embedding-3-small"):
    """Get LangChain embeddings using DO Gradient"""
    return OpenAIEmbeddings(
        base_url=GRADIENT_BASE_URL,
        api_key=GRADIENT_API_KEY,
        model=model
    )

# Pre-configured instances for common use cases
orchestrator_llm = get_llm("llama-3.1-70b-instruct")
feature_dev_llm = get_llm("codellama-13b-instruct")
embeddings = get_embeddings("text-embedding-3-small")
```

**Now use these everywhere:**

```python
# agents/langgraph/nodes/feature_dev.py
from agents._shared.langchain_gradient import feature_dev_llm, embeddings
from langchain_core.messages import HumanMessage

async def feature_dev_node(state: AgentState):
    # LLM inference
    response = await feature_dev_llm.ainvoke([
        HumanMessage(content=state["task_description"])
    ])

    # Embedding (for RAG)
    query_embedding = embeddings.embed_query(state["task_description"])

    return {"messages": [response]}
```

---

## Why This is Optimal

### 1. Single Platform (DigitalOcean)

- **LLM Inference:** DO Gradient AI
- **Embeddings:** DO Gradient AI (same endpoint)
- **Vector Storage:** Qdrant Cloud (DO-compatible)
- **Deployment:** DO Droplet

**Network topology:** Everything stays within DigitalOcean infrastructure = <10ms latency.

### 2. Single Management Interface (LangChain)

- **Configuration:** One Python module (langchain_gradient.py)
- **Abstraction:** LangChain's standard interfaces
- **Switching:** Change `base_url` in one place to try different providers
- **Testing:** Mock LangChain components (not custom wrappers)

### 3. No Platform Jumping

**Before (fragmented):**

```
1. Configure DO Gradient in .env
2. Write custom gradient_client.py wrapper
3. Configure embeddings separately in rag/main.py
4. Manage model configs in docker-compose.yml
5. Update LangGraph nodes with custom imports
```

**After (unified):**

```python
# 1. Configure once
from agents._shared.langchain_gradient import orchestrator_llm, embeddings

# 2. Use everywhere
llm_response = orchestrator_llm.invoke(messages)
vectors = embeddings.embed_documents(docs)
```

---

## Implementation Plan

### Phase 1: Replace Custom Gradient Client with LangChain (Week 1)

**Current bottleneck:**

```python
# agents/_shared/gradient_client.py (custom wrapper)
class GradientClient:
    def __init__(self, agent_name, model):
        self.client = Gradient(model_access_key=...)
```

**Replace with:**

```python
# agents/_shared/langchain_gradient.py
from langchain_openai import ChatOpenAI

def get_gradient_llm(agent_name: str, model: str):
    return ChatOpenAI(
        base_url="https://api.digitalocean.com/v2/ai/v1",
        api_key=os.getenv("GRADIENT_API_KEY"),
        model=model,
        tags=[agent_name],  # For Langfuse tracing
    )
```

**Migration steps:**

1. **Update langchain_gradient.py:**

```python
"""
Unified LangChain configuration for DigitalOcean Gradient AI
Manages both LLM inference and embeddings
"""
import os
import logging
from typing import Optional
from langchain_openai import ChatOpenAI
from langchain_community.embeddings import OpenAIEmbeddings
from langchain.callbacks.manager import CallbackManager

logger = logging.getLogger(__name__)

# DO Gradient AI configuration
GRADIENT_BASE_URL = os.getenv(
    "GRADIENT_BASE_URL",
    "https://api.digitalocean.com/v2/ai/v1"
)
GRADIENT_API_KEY = os.getenv("GRADIENT_API_KEY")

# Langfuse tracing (if configured)
LANGFUSE_ENABLED = all([
    os.getenv("LANGFUSE_SECRET_KEY"),
    os.getenv("LANGFUSE_PUBLIC_KEY"),
    os.getenv("LANGFUSE_HOST")
])

if LANGFUSE_ENABLED:
    try:
        from langfuse.callback import CallbackHandler
        langfuse_handler = CallbackHandler(
            secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
            public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
            host=os.getenv("LANGFUSE_HOST")
        )
        logger.info("Langfuse callback handler initialized")
    except ImportError:
        langfuse_handler = None
        logger.warning("Langfuse not installed, tracing disabled")
else:
    langfuse_handler = None


def get_gradient_llm(
    agent_name: str,
    model: str = "llama-3.1-8b-instruct",
    temperature: float = 0.7,
    max_tokens: int = 2000,
    **kwargs
) -> ChatOpenAI:
    """
    Get LangChain LLM configured for DO Gradient AI

    Args:
        agent_name: Agent identifier for tracing
        model: Gradient model name
        temperature: Sampling temperature
        max_tokens: Max tokens to generate
        **kwargs: Additional ChatOpenAI parameters

    Returns:
        Configured ChatOpenAI instance
    """
    callbacks = []
    if langfuse_handler:
        callbacks.append(langfuse_handler)

    return ChatOpenAI(
        base_url=GRADIENT_BASE_URL,
        api_key=GRADIENT_API_KEY,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        callbacks=callbacks,
        tags=[agent_name, "gradient-ai"],
        **kwargs
    )


def get_gradient_embeddings(
    model: str = "text-embedding-3-small",
    chunk_size: int = 1000
) -> OpenAIEmbeddings:
    """
    Get LangChain embeddings configured for DO Gradient AI

    Args:
        model: Embedding model name
        chunk_size: Max tokens per embedding request

    Returns:
        Configured OpenAIEmbeddings instance
    """
    return OpenAIEmbeddings(
        base_url=GRADIENT_BASE_URL,
        api_key=GRADIENT_API_KEY,
        model=model,
        chunk_size=chunk_size
    )


# Pre-configured instances for each agent
orchestrator_llm = get_gradient_llm(
    agent_name="orchestrator",
    model="llama-3.1-70b-instruct"
)

feature_dev_llm = get_gradient_llm(
    agent_name="feature-dev",
    model="codellama-13b-instruct"
)

code_review_llm = get_gradient_llm(
    agent_name="code-review",
    model="llama-3.1-70b-instruct"
)

infrastructure_llm = get_gradient_llm(
    agent_name="infrastructure",
    model="llama-3.1-8b-instruct"
)

cicd_llm = get_gradient_llm(
    agent_name="cicd",
    model="llama-3.1-8b-instruct"
)

documentation_llm = get_gradient_llm(
    agent_name="documentation",
    model="mistral-7b-instruct"
)

# Shared embeddings instance
gradient_embeddings = get_gradient_embeddings("text-embedding-3-small")
```

2. **Update langchain_memory.py:**

```python
"""
LangChain Memory Patterns - REVISED
Uses DO Gradient AI for embeddings via unified config
"""
from langchain.memory import ConversationBufferMemory, VectorStoreRetrieverMemory
from langchain_qdrant import QdrantVectorStore
from agents._shared.qdrant_client import get_qdrant_client
from agents._shared.langchain_gradient import gradient_embeddings  # USE UNIFIED CONFIG
import logging

logger = logging.getLogger(__name__)


def create_conversation_memory(
    memory_key: str = "chat_history",
    return_messages: bool = True
) -> ConversationBufferMemory:
    """Create conversation buffer memory for chat history"""
    return ConversationBufferMemory(
        memory_key=memory_key,
        return_messages=return_messages
    )


def create_vector_memory(
    collection_name: str = "agent_memory",
    search_kwargs: dict = None
) -> VectorStoreRetrieverMemory:
    """
    Create vector store memory using Qdrant Cloud + DO Gradient embeddings
    """
    qdrant_client = get_qdrant_client()

    if not qdrant_client.is_enabled():
        logger.warning("Qdrant Cloud not available, vector memory disabled")
        return None

    # Use unified embeddings from langchain_gradient
    vectorstore = QdrantVectorStore(
        client=qdrant_client.client,
        collection_name=collection_name,
        embeddings=gradient_embeddings  # DO Gradient AI embeddings
    )

    if search_kwargs is None:
        search_kwargs = {"k": 5}

    return VectorStoreRetrieverMemory(
        retriever=vectorstore.as_retriever(search_kwargs=search_kwargs)
    )


class HybridMemory:
    """Combines conversation buffer and vector store memory"""

    def __init__(self):
        self.buffer_memory = create_conversation_memory()
        self.vector_memory = create_vector_memory()

    def save_context(self, inputs: dict, outputs: dict):
        """Save context to both memory types"""
        self.buffer_memory.save_context(inputs, outputs)
        if self.vector_memory:
            self.vector_memory.save_context(inputs, outputs)

    def load_memory_variables(self, inputs: dict) -> dict:
        """Load memory variables from both sources"""
        buffer_vars = self.buffer_memory.load_memory_variables(inputs)

        if self.vector_memory:
            vector_vars = self.vector_memory.load_memory_variables(inputs)
            return {**buffer_vars, **vector_vars}

        return buffer_vars
```

3. **Update indexing script:**

```python
# scripts/index_local_docs.py (REVISED - use real embeddings)
from agents._shared.langchain_gradient import gradient_embeddings

def index_documents(client: QdrantClient, documents: List[Dict[str, Any]], collection: str = "the-shop"):
    """Index documents to Qdrant using DO Gradient embeddings"""
    print(f"\nIndexing {len(documents)} documents to '{collection}' collection...")

    # Create chunks from documents
    all_chunks = []
    for doc in documents:
        content = doc.pop("content")
        chunks = chunk_document(content, doc)
        all_chunks.extend(chunks)

    print(f"Created {len(all_chunks)} chunks")

    # Extract text for embedding
    texts = [chunk["content"] for chunk in all_chunks]

    # Generate REAL embeddings via DO Gradient AI
    print("Generating embeddings via DigitalOcean Gradient AI...")
    embeddings = gradient_embeddings.embed_documents(texts)
    print(f"✅ Generated {len(embeddings)} embeddings")

    # Convert to Qdrant points
    points = []
    for i, (chunk, embedding) in enumerate(zip(all_chunks, embeddings)):
        content = chunk.pop("content")

        point = PointStruct(
            id=str(uuid.uuid4()),
            vector=embedding,
            payload={
                "content": content,
                "indexed_at": datetime.utcnow().isoformat(),
                "embedding_model": "text-embedding-3-small",
                "embedding_provider": "digitalocean-gradient",
                **chunk
            }
        )
        points.append(point)

        if (i + 1) % 10 == 0:
            print(f"  Processed {i + 1}/{len(all_chunks)} chunks...")

    # Upsert in batches
    batch_size = 64
    for i in range(0, len(points), batch_size):
        batch = points[i:i + batch_size]
        client.upsert(collection_name=collection, points=batch)
        print(f"  Upserted batch {i // batch_size + 1}/{(len(points) + batch_size - 1) // batch_size}")

    print(f"✅ Successfully indexed {len(points)} chunks to '{collection}'")
```

4. **Update LangGraph nodes:**

```python
# agents/langgraph/nodes/feature_dev.py (EXAMPLE)
from agents._shared.langchain_gradient import feature_dev_llm, gradient_embeddings
from langchain_core.messages import HumanMessage, AIMessage

async def feature_dev_node(state: AgentState):
    """
    Feature development node using unified LangChain configuration
    """
    # Get task description
    task = state["task_description"]

    # Optional: RAG context retrieval
    if state.get("use_rag"):
        query_embedding = gradient_embeddings.embed_query(task)
        # ... search Qdrant with query_embedding

    # Generate code using configured LLM
    response = await feature_dev_llm.ainvoke([
        HumanMessage(content=f"Implement: {task}")
    ])

    return {
        "messages": [response],
        "current_agent": "feature-dev",
        "artifacts": {"code": response.content}
    }
```

---

### Phase 2: Centralized Configuration Management

**Create single config module:**

```python
# agents/langgraph/config.py (NEW)
"""
Unified LangGraph Configuration
Single source of truth for all LLM, embedding, and infrastructure config
"""
import os
from typing import Dict, Any
from agents._shared.langchain_gradient import (
    orchestrator_llm,
    feature_dev_llm,
    code_review_llm,
    infrastructure_llm,
    cicd_llm,
    documentation_llm,
    gradient_embeddings
)
from agents._shared.qdrant_client import get_qdrant_client
from agents._shared.langgraph_base import get_postgres_checkpointer

# Agent LLM configuration
AGENT_LLMS = {
    "orchestrator": orchestrator_llm,
    "feature-dev": feature_dev_llm,
    "code-review": code_review_llm,
    "infrastructure": infrastructure_llm,
    "cicd": cicd_llm,
    "documentation": documentation_llm
}

# Shared components
EMBEDDINGS = gradient_embeddings
QDRANT_CLIENT = get_qdrant_client()
CHECKPOINTER = get_postgres_checkpointer()

# Model metadata (for logging/tracing)
MODEL_METADATA: Dict[str, Dict[str, Any]] = {
    "orchestrator": {
        "model": "llama-3.1-70b-instruct",
        "provider": "digitalocean-gradient",
        "use_case": "complex_reasoning"
    },
    "feature-dev": {
        "model": "codellama-13b-instruct",
        "provider": "digitalocean-gradient",
        "use_case": "code_generation"
    },
    # ... rest of agents
}

def get_agent_llm(agent_name: str):
    """Get configured LLM for specific agent"""
    return AGENT_LLMS.get(agent_name)

def get_embeddings():
    """Get shared embeddings instance"""
    return EMBEDDINGS
```

**Now update workflow:**

```python
# agents/langgraph/workflow.py (SIMPLIFIED)
from langgraph.graph import StateGraph, END
from agents.langgraph.config import AGENT_LLMS, EMBEDDINGS, CHECKPOINTER
from agents.langgraph.nodes import (
    feature_dev_node,
    code_review_node,
    # ... other nodes
)

# Build workflow
workflow = StateGraph(AgentState)
workflow.add_node("feature-dev", feature_dev_node)
workflow.add_node("code-review", code_review_node)
# ... other nodes

# Compile with checkpointer
graph = workflow.compile(checkpointer=CHECKPOINTER)

# All LLMs and embeddings managed in one place!
```

---

## Benefits of Unified Approach

### 1. Single Configuration Point

```python
# Change embedding model for ENTIRE system:
# agents/_shared/langchain_gradient.py
gradient_embeddings = get_gradient_embeddings("text-embedding-3-large")  # Changed from 3-small
```

No need to update:

- ❌ RAG service config
- ❌ Memory module config
- ❌ Indexing script config
- ❌ Docker environment variables

### 2. Easy Provider Switching

**Switch to OpenAI (for testing):**

```python
# agents/_shared/langchain_gradient.py
# Just change base_url and api_key
GRADIENT_BASE_URL = "https://api.openai.com/v1"  # Changed
GRADIENT_API_KEY = os.getenv("OPENAI_API_KEY")   # Changed

# Everything else works identically
```

**Switch to local Ollama (for development):**

```python
from langchain_community.llms import Ollama
from langchain_community.embeddings import OllamaEmbeddings

def get_gradient_llm(agent_name: str, model: str):
    return Ollama(model="llama3.1")

def get_gradient_embeddings(model: str):
    return OllamaEmbeddings(model="nomic-embed-text")
```

### 3. Testability

**Mock LangChain components (standard practice):**

```python
# tests/test_feature_dev_node.py
from unittest.mock import Mock
from agents.langgraph.nodes import feature_dev_node

def test_feature_dev_node():
    # Mock LangChain LLM
    mock_llm = Mock()
    mock_llm.ainvoke.return_value = AIMessage(content="generated code")

    # Inject mock
    with patch('agents._shared.langchain_gradient.feature_dev_llm', mock_llm):
        result = await feature_dev_node(test_state)

    assert result["artifacts"]["code"] == "generated code"
```

---

## Cost Comparison (Updated)

| Component           | Current (Mock)    | Proposed (DO Unified) | Alternative (Separate) |
| ------------------- | ----------------- | --------------------- | ---------------------- |
| **LLM Inference**   | $0 (Gradient SDK) | $0.20/1M tokens       | $0.20/1M tokens        |
| **Embeddings**      | $0 (mock)         | **$0.02/1M tokens**   | $0.02/1M (OpenAI)      |
| **Management**      | 3 configs         | **1 config**          | 3 configs              |
| **Latency (LLM)**   | 50ms              | 50ms                  | 50ms                   |
| **Latency (Embed)** | N/A               | **10ms** (DO network) | 50-100ms (internet)    |
| **Memory Overhead** | 0MB               | 0MB                   | 512MB (local model)    |

**Monthly cost example (10M tokens LLM + 1M tokens embeddings):**

- LLM: 10M × $0.20/1M = **$2.00**
- Embeddings: 1M × $0.02/1M = **$0.02**
- **Total: $2.02/month** (vs $6/month for self-hosted embeddings container)

---

## Final Recommendation

### ✅ DO THIS: Unified DO Gradient + LangChain Management

**Reasoning:**

1. **No platform jumping** - Everything configured in Python code via LangChain
2. **Optimal performance** - Both LLM + embeddings on DO network (<10ms)
3. **Cost effective** - $2.02/month vs $6/month self-hosted + $2/month LLM
4. **Easy testing** - Mock LangChain components (standard patterns)
5. **Future proof** - Switch providers by changing 2 lines of code

**Implementation priority:**

1. **Week 1:** Replace custom gradient_client.py with langchain_gradient.py (unified config)
2. **Week 2:** Update indexing script to use real embeddings
3. **Week 3:** Migrate all nodes to use unified config
4. **Week 4:** Remove old custom wrappers and test end-to-end

### ❌ DON'T DO: Self-hosted embeddings in Docker

**Why not:**

- 512MB memory overhead (26% of 2GB droplet)
- 10x slower inference (100ms vs 10ms)
- Operational burden (model updates, monitoring)
- Already solved the OOM issue - don't reintroduce it

---

## Migration Checklist

- [ ] Create langchain_gradient.py with unified config
- [ ] Update langchain_memory.py to use unified embeddings
- [ ] Update index_local_docs.py to use real embeddings
- [ ] Create `agents/langgraph/config.py` for centralized management
- [ ] Update all LangGraph nodes to import from unified config
- [ ] Test embeddings API with DO Gradient: `curl -X POST https://api.digitalocean.com/v2/ai/v1/embeddings ...`
- [ ] Re-index documentation with real embeddings
- [ ] Verify RAG queries return relevant results
- [ ] Remove old gradient_client.py wrapper
- [ ] Update documentation to reference unified config

**Risk:** Low (LangChain abstractions are battle-tested)
