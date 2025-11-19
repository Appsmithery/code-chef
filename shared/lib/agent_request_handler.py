"""
Common handler for agent-to-agent requests.

Provides FastAPI endpoint decorator and request processing logic
that can be imported by all agents.

Usage in agent main.py:
    from lib.agent_request_handler import create_agent_request_endpoint
    from lib.event_bus import get_event_bus
    
    # Create endpoint with agent-specific handler
    @app.post("/agent-request")
    async def handle_agent_request(request: AgentRequestEvent):
        return await create_agent_request_endpoint(
            request=request,
            handler=my_custom_handler,
            agent_name="orchestrator"
        )
"""

import logging
from typing import Callable, Awaitable, Dict, Any
from datetime import datetime

from lib.agent_events import (
    AgentRequestEvent,
    AgentResponseEvent,
    AgentResponseStatus
)
from lib.event_bus import get_event_bus

logger = logging.getLogger(__name__)


async def process_agent_request(
    request: AgentRequestEvent,
    handler: Callable[[AgentRequestEvent], Awaitable[Dict[str, Any]]],
    agent_name: str
) -> AgentResponseEvent:
    """
    Process agent request with timing and error handling.
    
    Args:
        request: Incoming request from another agent
        handler: Async function to process the request
                 Signature: async def handler(request: AgentRequestEvent) -> Dict[str, Any]
                 Should return result dict or raise exception
        agent_name: Name of this agent (for response source)
    
    Returns:
        AgentResponseEvent with result or error
    
    Example handler:
        async def handle_review_code(request: AgentRequestEvent) -> Dict[str, Any]:
            file_path = request.payload.get("file_path")
            changes = request.payload.get("changes")
            
            # Do review...
            issues = analyze_code(file_path, changes)
            
            return {
                "issues_count": len(issues),
                "issues": issues,
                "severity": "high" if len(issues) > 5 else "low"
            }
    """
    start_time = datetime.utcnow()
    
    logger.info(
        f"Processing agent request {request.request_id} from "
        f"{request.source_agent} (type: {request.request_type})"
    )
    
    try:
        # Check if request expired (shouldn't happen, but be defensive)
        if request.is_expired:
            logger.warning(f"Request {request.request_id} already expired")
            return AgentResponseEvent(
                request_id=request.request_id,
                source_agent=agent_name,
                target_agent=request.source_agent,
                status=AgentResponseStatus.REJECTED,
                error="Request already expired"
            )
        
        # Call agent-specific handler
        result = await handler(request)
        
        # Calculate processing time
        end_time = datetime.utcnow()
        processing_ms = (end_time - start_time).total_seconds() * 1000
        
        # Create success response
        response = AgentResponseEvent(
            request_id=request.request_id,
            source_agent=agent_name,
            target_agent=request.source_agent,
            status=AgentResponseStatus.SUCCESS,
            result=result,
            processing_time_ms=processing_ms,
            metadata={
                "request_type": request.request_type,
                "correlation_id": request.correlation_id
            }
        )
        
        logger.info(
            f"Completed request {request.request_id} in {processing_ms:.1f}ms "
            f"(status: {response.status})"
        )
        
        return response
        
    except Exception as e:
        # Calculate processing time even for errors
        end_time = datetime.utcnow()
        processing_ms = (end_time - start_time).total_seconds() * 1000
        
        logger.error(
            f"Error processing request {request.request_id}: {e}",
            exc_info=True
        )
        
        # Create error response
        return AgentResponseEvent(
            request_id=request.request_id,
            source_agent=agent_name,
            target_agent=request.source_agent,
            status=AgentResponseStatus.ERROR,
            error=str(e),
            processing_time_ms=processing_ms,
            metadata={
                "request_type": request.request_type,
                "correlation_id": request.correlation_id
            }
        )


async def send_response_via_event_bus(
    response: AgentResponseEvent
) -> None:
    """
    Send response back to requesting agent via event bus.
    
    Args:
        response: AgentResponseEvent to send
    """
    event_bus = get_event_bus()
    await event_bus.respond_to_request(response)


# Convenience function combining both steps
async def handle_agent_request(
    request: AgentRequestEvent,
    handler: Callable[[AgentRequestEvent], Awaitable[Dict[str, Any]]],
    agent_name: str
) -> AgentResponseEvent:
    """
    Complete request/response flow: process request and send response.
    
    This is the main function agents should call from their endpoint.
    
    Args:
        request: Incoming AgentRequestEvent
        handler: Agent-specific request handler
        agent_name: Name of this agent
    
    Returns:
        AgentResponseEvent (also sent via event bus)
    
    Example:
        @app.post("/agent-request")
        async def agent_request_endpoint(request: AgentRequestEvent):
            return await handle_agent_request(
                request=request,
                handler=my_request_handler,
                agent_name="code-review"
            )
        
        async def my_request_handler(request: AgentRequestEvent) -> Dict[str, Any]:
            # Process request based on request.request_type
            if request.request_type == "review_code":
                return await review_code(request.payload)
            elif request.request_type == "explain_code":
                return await explain_code(request.payload)
            else:
                raise ValueError(f"Unsupported request type: {request.request_type}")
    """
    # Process request
    response = await process_agent_request(request, handler, agent_name)
    
    # Send response via event bus (for correlation tracking)
    await send_response_via_event_bus(response)
    
    # Return response directly (for HTTP response)
    return response
