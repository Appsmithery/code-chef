"""
FastAPI server for LangGraph workflow execution.

Provides HTTP endpoints for invoking workflows with streaming support.
"""

import logging
import os
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import uvicorn
import json

from agents.langgraph.workflow import (
    build_workflow,
    invoke_workflow,
    stream_workflow,
    stream_workflow_events,
)
from agents.langgraph.state import AgentState

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Request/Response models
class WorkflowRequest(BaseModel):
    """Request model for workflow invocation."""
    
    task_description: str = Field(..., description="Task description for workflow routing")
    request_payloads: Optional[Dict[str, Any]] = Field(
        None,
        description="Agent-specific request payloads (feature_request, code_review_request, etc.)"
    )
    thread_id: Optional[str] = Field(None, description="Thread ID for workflow checkpointing")
    enable_checkpointing: bool = Field(True, description="Enable PostgreSQL state persistence")


class WorkflowResponse(BaseModel):
    """Response model for completed workflow."""
    
    state: Dict[str, Any] = Field(..., description="Final workflow state")
    task_id: str = Field(..., description="Workflow task ID")
    status: str = Field("completed", description="Workflow execution status")


class StreamRequest(BaseModel):
    """Request model for streaming workflow execution."""
    
    task_description: str = Field(..., description="Task description for workflow routing")
    request_payloads: Optional[Dict[str, Any]] = Field(None, description="Agent-specific request payloads")
    thread_id: Optional[str] = Field(None, description="Thread ID for workflow checkpointing")
    enable_checkpointing: bool = Field(True, description="Enable PostgreSQL state persistence")
    stream_mode: str = Field("values", description="Streaming mode: values, updates, or debug")


class HealthResponse(BaseModel):
    """Health check response."""
    
    status: str = Field("healthy", description="Service health status")
    postgres_checkpointer: str = Field("unknown", description="PostgreSQL checkpointer status")
    mcp_gateway: str = Field("unknown", description="MCP gateway connection status")


# Initialize compiled workflow at startup
_compiled_workflow = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle manager."""
    global _compiled_workflow
    
    logger.info("Initializing LangGraph workflow...")
    _compiled_workflow = build_workflow(enable_checkpointing=True)
    logger.info("LangGraph workflow compiled and ready")
    
    yield
    
    logger.info("Shutting down LangGraph service")


# FastAPI application
app = FastAPI(
    title="LangGraph Workflow Service",
    description="Multi-agent workflow orchestration using LangGraph",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    from agents.langgraph.checkpointer import get_postgres_checkpointer
    
    # Check PostgreSQL checkpointer
    checkpointer = get_postgres_checkpointer()
    postgres_status = "connected" if checkpointer else "disconnected"
    
    # Check MCP gateway (basic check - expand as needed)
    mcp_gateway_url = os.getenv("MCP_GATEWAY_URL", "http://gateway-mcp:8000")
    mcp_status = "configured" if mcp_gateway_url else "not_configured"
    
    return HealthResponse(
        status="healthy",
        postgres_checkpointer=postgres_status,
        mcp_gateway=mcp_status
    )


@app.post("/workflow/invoke", response_model=WorkflowResponse)
async def invoke_workflow_endpoint(request: WorkflowRequest):
    """
    Execute workflow end-to-end and return final state.
    
    This endpoint blocks until workflow completion. For real-time
    progress updates, use the /workflow/stream endpoint instead.
    """
    global _compiled_workflow
    
    try:
        logger.info(f"Invoking workflow: {request.task_description[:100]}")
        
        # Invoke workflow (synchronous)
        final_state = invoke_workflow(
            graph=_compiled_workflow,
            task_description=request.task_description,
            request_payloads=request.request_payloads,
            thread_id=request.thread_id,
            enable_checkpointing=request.enable_checkpointing
        )
        
        logger.info(f"Workflow completed: task_id={final_state.get('task_id')}")
        
        return WorkflowResponse(
            state=dict(final_state),
            task_id=final_state.get("task_id", "unknown"),
            status="completed"
        )
        
    except Exception as e:
        logger.error(f"Workflow invocation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Workflow execution error: {str(e)}")


@app.post("/workflow/stream")
async def stream_workflow_endpoint(request: StreamRequest):
    """
    Stream workflow execution events in real-time.
    
    Returns Server-Sent Events (SSE) stream with state updates.
    Each event is a JSON object with the current workflow state.
    """
    global _compiled_workflow
    
    async def event_generator() -> AsyncIterator[str]:
        """Generate SSE events from workflow stream."""
        try:
            logger.info(f"Starting workflow stream: {request.task_description[:100]}")
            
            async for event in stream_workflow(
                graph=_compiled_workflow,
                task_description=request.task_description,
                request_payloads=request.request_payloads,
                thread_id=request.thread_id,
                enable_checkpointing=request.enable_checkpointing,
                stream_mode=request.stream_mode
            ):
                # Format as SSE event
                event_data = json.dumps(event, default=str)
                yield f"data: {event_data}\n\n"
            
            logger.info("Workflow stream completed")
            
        except Exception as e:
            logger.error(f"Workflow streaming failed: {e}", exc_info=True)
            error_event = json.dumps({"error": str(e)})
            yield f"data: {error_event}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.post("/workflow/stream-events")
async def stream_workflow_events_endpoint(request: StreamRequest):
    """
    Stream detailed workflow events including node execution and LLM calls.
    
    Returns Server-Sent Events (SSE) stream with fine-grained execution events.
    Useful for debugging and real-time progress tracking.
    """
    global _compiled_workflow
    
    async def event_generator() -> AsyncIterator[str]:
        """Generate SSE events from workflow event stream."""
        try:
            logger.info(f"Starting detailed event stream: {request.task_description[:100]}")
            
            async for event in stream_workflow_events(
                graph=_compiled_workflow,
                task_description=request.task_description,
                request_payloads=request.request_payloads,
                thread_id=request.thread_id,
                enable_checkpointing=request.enable_checkpointing
            ):
                # Format as SSE event
                event_data = json.dumps(event, default=str)
                yield f"data: {event_data}\n\n"
            
            logger.info("Detailed event stream completed")
            
        except Exception as e:
            logger.error(f"Event streaming failed: {e}", exc_info=True)
            error_event = json.dumps({"error": str(e)})
            yield f"data: {error_event}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


def main():
    """Run FastAPI server."""
    port = int(os.getenv("PORT", "8009"))
    host = os.getenv("HOST", "0.0.0.0")
    
    logger.info(f"Starting LangGraph service on {host}:{port}")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level=os.getenv("LOG_LEVEL", "info").lower()
    )


if __name__ == "__main__":
    main()
