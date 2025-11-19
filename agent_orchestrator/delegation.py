"""
Task Delegation Logic

Handles the mechanics of delegating tasks to other agents:
1. Discovering capable agents via Registry
2. Emitting delegation events via EventBus
3. Tracking delegation status
"""

import asyncio
import logging
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime

from shared.lib.event_bus import get_event_bus, InterAgentEvent
from shared.lib.registry_client import RegistryClient

logger = logging.getLogger(__name__)

class DelegationManager:
    def __init__(self, registry_client: RegistryClient):
        self.registry = registry_client
        self.event_bus = get_event_bus()
        
    async def delegate_subtask(
        self, 
        subtask: Dict[str, Any], 
        task_id: str,
        preferred_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Delegate a single subtask to an appropriate agent.
        
        Args:
            subtask: Subtask definition (id, description, capability/type)
            task_id: Parent task ID for correlation
            preferred_agent: Optional specific agent ID to target
            
        Returns:
            Delegation result metadata
        """
        target_agent = preferred_agent
        
        # If no specific agent, find one by capability/type
        if not target_agent:
            # Map 'agent_type' from subtask to registry capability or name
            agent_type = subtask.get("agent_type")
            if agent_type:
                # Simple mapping for now: agent_type value matches agent_id
                # In a real system, we'd query registry by capability
                target_agent = agent_type.value if hasattr(agent_type, "value") else str(agent_type)
            else:
                # Fallback or error
                logger.error(f"No agent type specified for subtask {subtask.get('id')}")
                return {"status": "failed", "reason": "no_agent_specified"}

        # Verify agent is active
        agent_info = await self.registry.get_agent(target_agent)
        if not agent_info or agent_info.get("status") == "offline":
            logger.warning(f"Target agent {target_agent} is offline or not found")
            # Could implement retry or fallback logic here
            
        # Emit delegation event
        delegation_id = str(uuid.uuid4())
        event_payload = {
            "subtask_id": subtask.get("id"),
            "delegation_id": delegation_id,
            "description": subtask.get("description"),
            "context": subtask.get("context_refs", []),
            "artifacts": subtask.get("artifacts", {}),
            "deadline": subtask.get("deadline")
        }
        
        await self.event_bus.emit(
            "task.delegated",
            event_payload,
            source="orchestrator",
            target_agent=target_agent,
            correlation_id=task_id
        )
        
        logger.info(f"Delegated subtask {subtask.get('id')} to {target_agent} (delegation_id={delegation_id})")
        
        return {
            "status": "delegated",
            "delegation_id": delegation_id,
            "target_agent": target_agent,
            "timestamp": datetime.utcnow().isoformat()
        }

    async def broadcast_task(self, task_description: str, capability: str):
        """Broadcast a task to any agent with specific capability."""
        # Implementation for "first to accept" pattern
        pass
