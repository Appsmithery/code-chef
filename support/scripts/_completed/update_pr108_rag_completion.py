#!/usr/bin/env python3
"""
Update PR-108 with RAG Integration completion details.
"""

import os
import requests

LINEAR_API_KEY = os.environ.get("LINEAR_API_KEY")
if not LINEAR_API_KEY:
    raise ValueError("LINEAR_API_KEY environment variable not set")

GRAPHQL_ENDPOINT = "https://api.linear.app/graphql"

COMPLETION_DESCRIPTION = """
## RAG Integration - COMPLETE ✅

### Implementation Summary
Orchestrator successfully integrated with RAG context injection for vendor documentation retrieval.

### Key Achievements
1. **Orchestrator Integration** (Nov 20, 2025)
   - Created `query_vendor_context()` function with keyword detection
   - Detects 13 vendor keywords: gradient, linear, langsmith, qdrant, streaming, etc.
   - Injects RAG context into LLM prompts before decomposition
   - Configuration: `RAG_SERVICE_URL=http://rag-context:8007`, `RAG_TIMEOUT=10s`

2. **Gradient Client Fix** (Nov 20, 2025)
   - Fixed JSON parsing issue with markdown code fences (```json...```)
   - Added fence stripping logic before JSON.loads()
   - LLM responses now parsed successfully

3. **LangChain MCP Documentation** (Nov 20, 2025)
   - Indexed 6 chunks from https://python.langchain.com/docs/concepts/mcp/
   - Relevance scores: 0.57-0.58
   - Total vendor-docs collection: 58 chunks (gradient-ai: 39, linear-api: 10, langchain-mcp: 6, langsmith-api: 1, langgraph-reference: 1, qdrant-api: 1)

### Validation Results
- **Test Query**: "Create a Python script that uses Gradient AI streaming to generate text responses"
- **RAG Retrieval**: 2 vendor docs retrieved in 721ms
- **LLM Decomposition**: 5 subtasks generated successfully
- **Task ID**: 6c652418-34ae-4e2e-969d-dd947096b434
- **Subtasks**:
  1. feature-dev: Implement Python script using Gradient AI streaming
  2. code-review: Perform quality assurance and security scanning
  3. infrastructure: Generate infrastructure-as-code (Docker/K8s/Terraform)
  4. cicd: Create CI/CD pipeline (GitHub Actions/GitLab CI)
  5. documentation: Generate README and API docs

### Performance Metrics
- RAG query latency: ~700ms (within 1000ms target)
- Relevance scores: 0.57-0.68 (target: >0.85, needs chunking optimization)
- Token savings: 200-500 tokens per vendor task (by avoiding manual doc lookup)

### Infrastructure Changes
- **Docker Images**:
  - orchestrator-latest: sha256:b62ef5621c88b8489aecb3ee6b4c299ff20ae6735bad033b3018e592a41a569d
  - rag-latest: sha256:8fcf609f (unchanged)
- **Deployment**: Production droplet 45.55.173.72
- **Services**: orchestrator:8001, rag:8007

### Remaining Work (Tracked in Separate Issues)
1. **Chunking Optimization**: Improve relevance scores from 0.6-0.7 to >0.85 via semantic chunking
2. **Adoption Metrics**: Implement Prometheus counters for RAG usage tracking (target: >30% of vendor tasks)

### Files Modified
- `agent_orchestrator/main.py`: Added query_vendor_context() and RAG integration (lines 180-181, 415-490, 1870, 1946)
- `shared/lib/gradient_client.py`: Fixed JSON parsing with markdown fence stripping (lines 209-218)
- `support/scripts/rag/index_vendor_docs.py`: Corrected langchain-mcp URL (line 65)

### Completion Date
November 20, 2025
"""

mutation = """
mutation UpdateIssue($issueId: String!, $description: String!) {
  issueUpdate(id: $issueId, input: {description: $description}) {
    success
    issue {
      id
      identifier
      title
    }
  }
}
"""

variables = {
    "issueId": "PR-108",
    "description": COMPLETION_DESCRIPTION
}

response = requests.post(
    GRAPHQL_ENDPOINT,
    json={"query": mutation, "variables": variables},
    headers={"Authorization": LINEAR_API_KEY}
)

result = response.json()
if "errors" in result:
    print(f"❌ Error: {result['errors']}")
    exit(1)

print(f"✅ Updated PR-108 description with RAG completion details")
print(f"   Issue: {result['data']['issueUpdate']['issue']['identifier']}")
print(f"   Title: {result['data']['issueUpdate']['issue']['title']}")
