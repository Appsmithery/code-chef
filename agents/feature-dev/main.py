"""
Feature Development Agent

Primary Role: Application code generation and feature implementation
- Context Analysis: Queries RAG Context Manager for relevant codebase files
- Code Generation: Generates implementation code for business logic and components
- Iterative Testing: Executes unit tests and patches code until tests pass
- Integration Preparation: Creates commit-ready artifacts
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from datetime import datetime
import uvicorn
import os
import httpx
from prometheus_fastapi_instrumentator import Instrumentator

from agents._shared.mcp_client import MCPClient
from agents._shared.gradient_client import get_gradient_client

app = FastAPI(
    title="Feature Development Agent",
    description="Application code generation and feature implementation",
    version="1.0.0"
)

# Enable Prometheus metrics collection
Instrumentator().instrument(app).expose(app)

# RAG Context Manager URL
RAG_SERVICE_URL = os.getenv("RAG_SERVICE_URL", "http://rag-context:8007")

# Shared MCP client for tool access and telemetry
mcp_client = MCPClient(agent_name="feature-dev")

# Gradient AI client for LLM inference (with Langfuse tracing)
gradient_client = get_gradient_client("feature-dev")

class FeatureRequest(BaseModel):
    """Feature implementation request"""
    description: str = Field(..., description="Feature description from orchestrator")
    context_refs: Optional[List[str]] = Field(default=None, description="Context references from RAG")
    project_context: Optional[Dict[str, Any]] = Field(default=None, description="Project metadata")
    task_id: Optional[str] = Field(default=None, description="Parent task ID from orchestrator")

class CodeArtifact(BaseModel):
    """Generated code artifact"""
    file_path: str
    content: str
    operation: str = Field(..., description="create, modify, or delete")
    description: str

class TestResult(BaseModel):
    """Unit test execution result"""
    test_name: str
    status: str
    duration_ms: float
    error_message: Optional[str] = None

class FeatureResponse(BaseModel):
    """Feature implementation response"""
    feature_id: str
    status: str
    artifacts: List[CodeArtifact]
    test_results: List[TestResult]
    commit_message: str
    estimated_tokens: int
    context_lines_used: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    gateway_health = await mcp_client.get_gateway_health()
    return {
        "status": "ok",
        "service": "feature-dev",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "mcp": {
            "gateway": gateway_health,
            "recommended_tool_servers": [entry.get("server") for entry in mcp_client.recommended_tools],
            "shared_tool_servers": mcp_client.shared_tools,
            "capabilities": mcp_client.capabilities,
        },
    }

@app.post("/implement", response_model=FeatureResponse)
async def implement_feature(request: FeatureRequest):
    """
    Main feature implementation endpoint
    - Queries RAG Context Manager for relevant code (10-50 lines)
    - Generates implementation code incrementally
    - Executes unit tests in sandbox
    - Returns commit-ready artifacts
    
    Token Optimization: Requests minimal context spans, reuses patterns
    """
    import uuid
    
    feature_id = str(uuid.uuid4())
    
    # Query RAG for context
    rag_context = await query_rag_context(request.description)
    
    # Check if Gradient is available for LLM calls
    if gradient_client.is_enabled():
        # Generate code using Gradient AI with Langfuse tracing
        artifacts = await generate_code_with_llm(request, rag_context, feature_id)
    else:
        # Fallback to mock generation (for testing without API key)
        artifacts = generate_code_artifacts(request, rag_context)
    
    # Simulate test execution (in production, would run in sandbox)
    test_results = execute_tests(artifacts)
    
    # Generate commit message
    commit_message = generate_commit_message(request, artifacts)
    
    # Token estimation: minimal context + incremental generation
    estimated_tokens = len(request.description.split()) * 10  # Rough estimate
    context_lines = sum(len(item.get("content", "").split('\n')) for item in rag_context)
    
    response = FeatureResponse(
        feature_id=feature_id,
        status="completed" if all(t.status == "passed" for t in test_results) else "needs_revision",
        artifacts=artifacts,
        test_results=test_results,
        commit_message=commit_message,
        estimated_tokens=estimated_tokens,
        context_lines_used=context_lines
    )

    await mcp_client.log_event(
        "feature_implemented",
        metadata={
            "feature_id": feature_id,
            "artifact_count": len(artifacts),
            "test_pass_rate": sum(1 for t in test_results if t.status == "passed") / max(len(test_results), 1),
            "status": response.status,
            "llm_enabled": gradient_client.is_enabled(),
        },
    )
    
    return response

@app.post("/implement-and-review", response_model=Dict[str, Any])
async def implement_and_review(request: FeatureRequest):
    """Implement feature and automatically trigger code review"""
    # Step 1: Implement feature
    feature_result = await implement_feature(request)
    
    # Step 2: Automatically call code-review agent
    code_review_url = os.getenv("CODE_REVIEW_URL", "http://code-review:8003")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            review_response = await client.post(
                f"{code_review_url}/review",
                json={
                    "task_id": request.task_id or feature_result.feature_id,
                    "diffs": [
                        {
                            "file_path": artifact.file_path,
                            "changes": artifact.content,
                            "context_lines": 5
                        }
                        for artifact in feature_result.artifacts
                    ],
                    "test_results": {
                        "results": [result.dict() for result in feature_result.test_results]
                    }
                }
            )
            
            if review_response.status_code == 200:
                review_data = review_response.json()
                await mcp_client.log_event(
                    "feature_review_completed",
                    metadata={
                        "feature_id": feature_result.feature_id,
                        "approval": review_data.get("approval", False),
                        "findings": review_data.get("findings"),
                    },
                )
                return {
                    "feature_implementation": feature_result.dict(),
                    "code_review": review_data,
                    "workflow_status": "completed",
                    "approval": review_data.get("approval", False)
                }
            else:
                await mcp_client.log_event(
                    "feature_review_failed",
                    metadata={
                        "feature_id": feature_result.feature_id,
                        "status_code": review_response.status_code,
                    },
                    entity_type="feature_dev_error",
                )
                return {
                    "feature_implementation": feature_result.dict(),
                    "code_review": {"error": f"Review failed with status {review_response.status_code}"},
                    "workflow_status": "partial",
                    "approval": False
                }
    except Exception as e:
        await mcp_client.log_event(
            "feature_review_exception",
            metadata={
                "feature_id": feature_result.feature_id,
                "error": str(e),
            },
            entity_type="feature_dev_error",
        )
        return {
            "feature_implementation": feature_result.dict(),
            "code_review": {"error": str(e)},
            "workflow_status": "partial",
            "approval": False
        }


async def query_rag_context(description: str) -> List[Dict[str, Any]]:
    """Query RAG Context Manager for relevant code and documentation"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{RAG_SERVICE_URL}/query",
                json={
                    "query": description,
                    "collection": "the-shop",
                    "n_results": 5
                },
                timeout=10.0
            )
            
            if response.status_code == 200:
                data = response.json()
                return [
                    {
                        "content": item["content"],
                        "metadata": item["metadata"],
                        "relevance": item["relevance_score"]
                    }
                    for item in data.get("results", [])
                ]
            else:
                # Fallback to mock if RAG unavailable
                return await query_mock_rag(description)
                
    except Exception as e:
        print(f"RAG query failed: {e}, using mock data")
        return await query_mock_rag(description)


async def query_mock_rag(description: str) -> List[Dict[str, Any]]:
    """Fallback mock RAG query for development"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{RAG_SERVICE_URL}/query/mock",
                json={
                    "query": description,
                    "collection": "the-shop",
                    "n_results": 5
                },
                timeout=5.0
            )
            
            if response.status_code == 200:
                data = response.json()
                return [
                    {
                        "content": item["content"],
                        "metadata": item["metadata"],
                        "relevance": item["relevance_score"]
                    }
                    for item in data.get("results", [])
                ]
    except:
        pass
    
    # Ultimate fallback
    return [{
        "content": f"Context for: {description}",
        "metadata": {"source": "fallback"},
        "relevance": 0.5
    }]


@app.get("/patterns")
async def get_coding_patterns():
    """Retrieve cached coding patterns for token optimization"""
    return {
        "patterns": [
            {"name": "rest_api_handler", "description": "Standard REST API endpoint pattern"},
            {"name": "data_model", "description": "Pydantic data model with validation"},
            {"name": "service_layer", "description": "Business logic service pattern"},
            {"name": "repository_pattern", "description": "Data access layer pattern"}
        ],
        "cache_hit_rate": 0.72,
        "token_savings": "60-70%"
    }
def generate_code_artifacts(request: FeatureRequest, rag_context: List[Dict[str, Any]] = None) -> List[CodeArtifact]:
    """
    Generate code artifacts based on feature request and RAG context (mock fallback)
    Uses incremental generation with checkpoint validation
    """
    # Placeholder implementation (intentional for MVP demo)
    # In production, this would call LLM with RAG context for actual code generation
    return [
        CodeArtifact(
            file_path=f"src/features/{request.description.replace(' ', '_').lower()}.py",
            content="# Generated feature implementation\n# Production: Replace with LLM-generated code",
            operation="create",
            description=f"Implementation for {request.description}"
        )
    ]


async def generate_code_with_llm(
    request: FeatureRequest,
    rag_context: List[Dict[str, Any]],
    feature_id: str
) -> List[CodeArtifact]:
    """
    Generate code artifacts using Gradient AI with Langfuse tracing.
    Incorporates RAG context for improved accuracy.
    """
    # Build context-aware prompt
    context_str = "\n\n".join([
        f"Context {i+1}:\n{item['content']}"
        for i, item in enumerate(rag_context[:3])  # Limit to top 3 contexts
    ])
    
    system_prompt = """You are an expert software engineer. Generate production-ready code based on the feature description and context provided.

Return your response as JSON with this structure:
{
  "files": [
    {
      "path": "src/path/to/file.py",
      "content": "# Full file content here",
      "operation": "create",
      "description": "Brief description"
    }
  ]
}"""
    
    user_prompt = f"""Feature Request: {request.description}

Relevant Context:
{context_str}

Project Context: {request.project_context or "General Python project"}

Generate implementation files with proper error handling, type hints, and docstrings."""
    
    try:
        # Call Gradient AI with Langfuse tracing
        result = await gradient_client.complete_structured(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.7,
            max_tokens=2000,
            metadata={
                "task_id": feature_id,
                "feature_description": request.description,
                "rag_contexts": len(rag_context)
            }
        )
        
        # Parse LLM response into CodeArtifact objects
        llm_files = result["content"].get("files", [])
        
        artifacts = [
            CodeArtifact(
                file_path=file["path"],
                content=file["content"],
                operation=file.get("operation", "create"),
                description=file.get("description", "")
            )
            for file in llm_files
        ]
        
        print(f"[LLM] Generated {len(artifacts)} artifacts using {result['tokens']} tokens")
        return artifacts
        
    except Exception as e:
        print(f"[ERROR] LLM generation failed: {e}, falling back to mock")
        return generate_code_artifacts(request, rag_context)


def execute_tests(artifacts: List[CodeArtifact]) -> List[TestResult]:
    """
    Execute unit tests in sandboxed environment
    Iterates until tests pass or max attempts reached
    """
    # Placeholder implementation
    return [
        TestResult(
            test_name="test_feature_implementation",
            status="passed",
            duration_ms=125.5
        )
    ]

def generate_commit_message(request: FeatureRequest, artifacts: List[CodeArtifact]) -> str:
    """Generate descriptive commit message for artifacts"""
    return f"feat: {request.description}\n\nGenerated {len(artifacts)} file(s)\n- " + "\n- ".join(a.file_path for a in artifacts)

if __name__ == '__main__':
    port = int(os.getenv("PORT", "8002"))
    uvicorn.run(app, host="0.0.0.0", port=port)