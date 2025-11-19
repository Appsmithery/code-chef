"""
Orchestrator routing utilities for capability-based agent selection.

Provides functions to query the agent registry and route requests
to the most appropriate agent based on capabilities.

Usage:
    from lib.orchestrator_router import route_to_agent, discover_agents_for_task
    
    # Route a task to the best agent
    response = await route_to_agent(
        request_type="review_code",
        payload={"file_path": "main.py", "changes": "..."},
        capability_keywords=["code", "review", "quality"]
    )
    
    # Discover agents that can handle a task
    agents = await discover_agents_for_task(
        task_description="Review Python code for security issues",
        registry_client=registry_client
    )
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from lib.agent_events import (
    AgentRequestEvent,
    AgentResponseEvent,
    AgentRequestType,
    AgentRequestPriority,
    AgentCapabilityQuery,
    AgentRoutingResult
)
from lib.event_bus import get_event_bus
from lib.registry_client import RegistryClient

logger = logging.getLogger(__name__)


async def discover_agents_for_task(
    task_description: str,
    registry_client: Optional[RegistryClient] = None,
    capability_keywords: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Discover agents that can handle a given task.
    
    Args:
        task_description: Natural language description of the task
        registry_client: RegistryClient instance (optional)
        capability_keywords: Override keywords to search for
    
    Returns:
        List of matching agents with their capabilities
    
    Example:
        agents = await discover_agents_for_task(
            "Review Python code for security vulnerabilities",
            registry_client=registry_client
        )
        
        for agent in agents:
            print(f"{agent['agent_name']}: {agent['capabilities']}")
    """
    if not registry_client:
        logger.warning("No registry client available for agent discovery")
        return []
    
    # Extract keywords from task description if not provided
    if not capability_keywords:
        capability_keywords = extract_keywords_from_task(task_description)
    
    logger.info(
        f"Discovering agents for task: '{task_description}' "
        f"(keywords: {capability_keywords})"
    )
    
    # Search registry for matching agents
    try:
        agents = []
        for keyword in capability_keywords:
            matches = await registry_client.search_capabilities(keyword)
            agents.extend(matches)
        
        # Deduplicate by agent_id
        seen = set()
        unique_agents = []
        for agent in agents:
            if agent["agent_id"] not in seen:
                seen.add(agent["agent_id"])
                unique_agents.append(agent)
        
        logger.info(f"Found {len(unique_agents)} unique agents for task")
        return unique_agents
        
    except Exception as e:
        logger.error(f"Agent discovery failed: {e}")
        return []


def extract_keywords_from_task(task_description: str) -> List[str]:
    """
    Extract capability keywords from task description.
    
    Args:
        task_description: Natural language task description
    
    Returns:
        List of keyword strings
    
    Example:
        keywords = extract_keywords_from_task(
            "Review Python code for security vulnerabilities"
        )
        # Returns: ["review", "code", "security"]
    """
    task_lower = task_description.lower()
    
    # Keyword mappings for common task types
    keyword_map = {
        "review": ["review", "code-review", "quality"],
        "code": ["code", "review", "generate"],
        "generate": ["generate", "feature", "code"],
        "deploy": ["deploy", "infrastructure", "cicd"],
        "infrastructure": ["infrastructure", "deploy", "config"],
        "cicd": ["cicd", "pipeline", "build"],
        "ci/cd": ["cicd", "pipeline", "build"],
        "document": ["documentation", "docs", "explain"],
        "docs": ["documentation", "docs", "explain"],
        "security": ["security", "review", "scan"],
        "test": ["test", "cicd", "validation"],
        "refactor": ["refactor", "code", "feature"],
        "orchestrate": ["orchestration", "routing", "workflow"],
        "approval": ["approval", "hitl", "workflow"]
    }
    
    keywords = []
    for key, values in keyword_map.items():
        if key in task_lower:
            keywords.extend(values)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_keywords = []
    for kw in keywords:
        if kw not in seen:
            seen.add(kw)
            unique_keywords.append(kw)
    
    # Default fallback
    if not unique_keywords:
        unique_keywords = ["task", "execute"]
    
    return unique_keywords[:5]  # Limit to 5 keywords


async def route_to_agent(
    request_type: AgentRequestType,
    payload: Dict[str, Any],
    capability_keywords: Optional[List[str]] = None,
    task_description: Optional[str] = None,
    priority: AgentRequestPriority = AgentRequestPriority.NORMAL,
    timeout: float = 30.0,
    registry_client: Optional[RegistryClient] = None,
    source_agent: str = "orchestrator"
) -> AgentResponseEvent:
    """
    Route a request to the most appropriate agent based on capabilities.
    
    Args:
        request_type: Type of request to send
        payload: Request payload data
        capability_keywords: Keywords for capability matching
        task_description: Task description (for keyword extraction)
        priority: Request priority level
        timeout: Request timeout in seconds
        registry_client: RegistryClient instance
        source_agent: Name of requesting agent
    
    Returns:
        AgentResponseEvent with result or error
    
    Example:
        response = await route_to_agent(
            request_type=AgentRequestType.REVIEW_CODE,
            payload={"file_path": "main.py", "changes": "..."},
            capability_keywords=["code", "review"],
            registry_client=registry_client
        )
        
        if response.status == "success":
            print(f"Review result: {response.result}")
    """
    # Discover appropriate agent
    if capability_keywords or task_description:
        agents = await discover_agents_for_task(
            task_description=task_description or str(request_type),
            registry_client=registry_client,
            capability_keywords=capability_keywords
        )
        
        if not agents:
            logger.error(f"No agents found for request type: {request_type}")
            return AgentResponseEvent(
                request_id="no-request",
                source_agent="orchestrator",
                target_agent=source_agent,
                status="error",
                error=f"No agents found with required capabilities"
            )
        
        # Select first matching agent (TODO: implement scoring)
        target_agent = agents[0]["agent_id"]
        logger.info(
            f"Routing {request_type} to {target_agent} "
            f"(matched on capabilities: {agents[0]['capabilities'][:2]})"
        )
    else:
        # No capability filtering - send to "any"
        target_agent = "any"
        logger.warning(f"Routing {request_type} to 'any' agent (no capability filter)")
    
    # Create request event
    request = AgentRequestEvent(
        source_agent=source_agent,
        target_agent=target_agent,
        request_type=request_type,
        payload=payload,
        priority=priority,
        timeout_seconds=timeout,
        metadata={
            "capability_keywords": capability_keywords or [],
            "task_description": task_description or ""
        }
    )
    
    # Send request via event bus
    event_bus = get_event_bus()
    response = await event_bus.request_agent(request, timeout=timeout)
    
    return response


async def route_and_aggregate(
    subtasks: List[Dict[str, Any]],
    registry_client: Optional[RegistryClient] = None,
    parallel: bool = True,
    source_agent: str = "orchestrator"
) -> Dict[str, Any]:
    """
    Route multiple subtasks to appropriate agents and aggregate results.
    
    Args:
        subtasks: List of subtask dicts with keys:
                  - request_type: AgentRequestType
                  - payload: Request payload
                  - capability_keywords: List of keywords (optional)
        registry_client: RegistryClient instance
        parallel: Execute subtasks concurrently
        source_agent: Name of requesting agent
    
    Returns:
        Dict with aggregated results
    
    Example:
        subtasks = [
            {
                "request_type": AgentRequestType.REVIEW_CODE,
                "payload": {"file_path": "main.py", "changes": "..."},
                "capability_keywords": ["review", "code"]
            },
            {
                "request_type": AgentRequestType.GENERATE_DOCS,
                "payload": {"code": "...", "format": "markdown"},
                "capability_keywords": ["documentation"]
            }
        ]
        
        result = await route_and_aggregate(
            subtasks=subtasks,
            registry_client=registry_client,
            parallel=True
        )
        
        print(f"Completed {result['completed_count']}/{result['total_count']} subtasks")
    """
    import asyncio
    
    logger.info(f"Routing {len(subtasks)} subtasks (parallel: {parallel})")
    
    async def execute_subtask(idx: int, subtask: Dict[str, Any]) -> Dict[str, Any]:
        """Execute single subtask and return result with metadata."""
        try:
            response = await route_to_agent(
                request_type=subtask["request_type"],
                payload=subtask["payload"],
                capability_keywords=subtask.get("capability_keywords"),
                priority=subtask.get("priority", AgentRequestPriority.NORMAL),
                timeout=subtask.get("timeout", 30.0),
                registry_client=registry_client,
                source_agent=source_agent
            )
            
            return {
                "index": idx,
                "status": response.status,
                "result": response.result,
                "error": response.error,
                "agent": response.source_agent,
                "processing_time_ms": response.processing_time_ms
            }
        except Exception as e:
            logger.error(f"Subtask {idx} failed: {e}")
            return {
                "index": idx,
                "status": "error",
                "error": str(e),
                "agent": None
            }
    
    # Execute subtasks
    if parallel:
        tasks = [execute_subtask(i, st) for i, st in enumerate(subtasks)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
    else:
        results = []
        for i, st in enumerate(subtasks):
            result = await execute_subtask(i, st)
            results.append(result)
    
    # Aggregate results
    successful = [r for r in results if not isinstance(r, Exception) and r["status"] == "success"]
    failed = [r for r in results if isinstance(r, Exception) or r["status"] != "success"]
    
    return {
        "total_count": len(subtasks),
        "completed_count": len(successful),
        "failed_count": len(failed),
        "results": results,
        "success_rate": len(successful) / len(subtasks) if subtasks else 0,
        "execution_mode": "parallel" if parallel else "sequential"
    }
