"""
Event Bus - Pub/Sub Pattern for Agent Notifications and Inter-Agent Communication

Provides in-memory event routing with support for:
- General pub/sub events (approval_required, task_completed, etc.)
- Agent-to-agent request/response messaging
- Timeout handling and correlation tracking

Supported Events:
- approval_required: HITL approval request created
- approval_approved: HITL approval granted
- approval_rejected: HITL approval denied
- task_completed: Task finished successfully
- task_failed: Task failed with error
- agent_error: Agent encountered critical error
- agent_request: Request from one agent to another
- agent_response: Response to agent request

Usage:
    from shared.lib.event_bus import EventBus, Event
    from shared.lib.agent_events import AgentRequestEvent, AgentResponseEvent
    
    # Initialize singleton
    bus = EventBus.get_instance()
    
    # Subscribe to general events
    async def on_approval_required(event: Event):
        print(f"Approval needed: {event.data['approval_id']}")
    
    bus.subscribe("approval_required", on_approval_required)
    
    # Agent-to-agent request/response
    request = AgentRequestEvent(
        source_agent="orchestrator",
        target_agent="code-review",
        request_type="review_code",
        payload={"file_path": "main.py"}
    )
    response = await bus.request_agent(request, timeout=30.0)
"""

import asyncio
import logging
from typing import Dict, List, Callable, Any, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime
import os
from enum import Enum
import json
import uuid

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    redis = None
    REDIS_AVAILABLE = False
    
logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Supported event types."""
    APPROVAL_REQUIRED = "approval_required"
    APPROVAL_APPROVED = "approval_approved"
    APPROVAL_REJECTED = "approval_rejected"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    AGENT_ERROR = "agent_error"
    
    # Inter-agent events
    TASK_DELEGATED = "task.delegated"
    TASK_ACCEPTED = "task.accepted"
    TASK_REJECTED = "task.rejected"
    RESOURCE_LOCKED = "resource.locked"
    RESOURCE_UNLOCKED = "resource.unlocked"
    AGENT_STATUS_CHANGE = "agent.status_change"
    WORKFLOW_CHECKPOINT = "workflow.checkpoint"


@dataclass
class InterAgentEvent:
    """
    Standardized event for agent-to-agent communication.
    """
    event_type: str
    source_agent: str
    payload: Dict[str, Any]
    target_agent: Optional[str] = None  # None = broadcast
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    correlation_id: Optional[str] = None
    priority: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "source_agent": self.source_agent,
            "target_agent": self.target_agent,
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat(),
            "correlation_id": self.correlation_id,
            "priority": self.priority
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'InterAgentEvent':
        ts = data.get("timestamp")
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts)
            
        return cls(
            event_type=data["event_type"],
            source_agent=data["source_agent"],
            payload=data["payload"],
            target_agent=data.get("target_agent"),
            event_id=data.get("event_id", str(uuid.uuid4())),
            timestamp=ts or datetime.utcnow(),
            correlation_id=data.get("correlation_id"),
            priority=data.get("priority", 0)
        )


@dataclass
class Event:
    """
    Event data structure.
    
    Attributes:
        type: Event type (approval_required, task_completed, etc.)
        data: Event payload (dict with event-specific fields)
        timestamp: When event was created
        source: Which agent/component emitted the event
        correlation_id: Optional ID to correlate related events
    """
    type: str
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    source: str = "unknown"
    correlation_id: Optional[str] = None
    
    def __repr__(self) -> str:
        return (
            f"Event(type={self.type}, source={self.source}, "
            f"timestamp={self.timestamp.isoformat()}, "
            f"correlation_id={self.correlation_id})"
        )


class EventBus:
    """
    In-memory event bus with pub/sub pattern and agent-to-agent messaging.
    
    Features:
    - Async subscriber callbacks
    - Multiple subscribers per event type
    - Agent request/response correlation
    - Timeout handling with asyncio.wait_for
    - Priority queuing for agent requests
    - Error handling (failed subscribers don't block others)
    - Singleton pattern for global access
    - Optional Redis backend (future)
    """
    
    _instance: Optional['EventBus'] = None
    
    def __init__(self):
        """Initialize event bus with empty subscribers and request tracking."""
        self._subscribers: Dict[str, List[Callable]] = {}
        self._pending_requests: Dict[str, asyncio.Future] = {}  # request_id -> Future
        self._request_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._stats: Dict[str, int] = {
            "events_emitted": 0,
            "events_delivered": 0,
            "subscriber_errors": 0,
            "agent_requests_sent": 0,
            "agent_responses_received": 0,
            "agent_timeouts": 0,
            "redis_events_published": 0,
            "redis_events_received": 0
        }
        
        # Redis setup
        self.redis_url = os.getenv("REDIS_URL", "redis://redis:6379")
        self.redis_client = None
        self.redis_pubsub = None
        self._redis_task = None
        
        # Do not connect in __init__ as it may be called before event loop is running
        # Call connect() explicitly during application startup
            
        logger.info("Event bus initialized")

    async def connect(self):
        """Connect to Redis and start listening for events."""
        if not REDIS_AVAILABLE:
            logger.warning("Redis not available, skipping connection")
            return

        if self.redis_client:
            return  # Already connected

        await self._connect_redis()

    async def _connect_redis(self):
        """Connect to Redis and start listening for events."""
        try:
            self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
            await self.redis_client.ping()
            logger.info(f"✅ Connected to Redis at {self.redis_url}")
            
            # Start listener
            self.redis_pubsub = self.redis_client.pubsub()
            await self.redis_pubsub.subscribe("agent-events")
            self._redis_task = asyncio.create_task(self._redis_listener())
            
        except Exception as e:
            logger.warning(f"⚠️  Redis connection failed: {e}. Inter-agent events will be local-only.")
            self.redis_client = None

    async def _redis_listener(self):
        """Listen for Redis messages and dispatch to local subscribers."""
        try:
            async for message in self.redis_pubsub.listen():
                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        event = InterAgentEvent.from_dict(data)
                        
                        # Dispatch locally
                        # We use a special prefix or just map to local event types
                        # For now, we'll emit as a standard Event
                        
                        self._stats["redis_events_received"] += 1
                        
                        # Avoid re-publishing to Redis if we are the source (simple check)
                        # In a real system, we'd check source_agent against our identity
                        
                        await self.emit(
                            event.event_type,
                            event.payload,
                            source=event.source_agent,
                            correlation_id=event.correlation_id,
                            publish_to_redis=False  # Don't echo back
                        )
                        
                    except Exception as e:
                        logger.error(f"Error processing Redis message: {e}")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Redis listener error: {e}")
            # Retry logic could go here
    
    @classmethod
    def get_instance(cls) -> 'EventBus':
        """
        Get singleton instance of event bus.
        
        Returns:
            Global EventBus instance
        """
        if cls._instance is None:
            cls._instance = cls()
            logger.info("Created new EventBus singleton")
        return cls._instance
    
    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton (for testing)."""
        cls._instance = None
        logger.info("EventBus singleton reset")
    
    def subscribe(
        self,
        event_type: str,
        callback: Callable[[Event], Any]
    ) -> None:
        """
        Subscribe to event type.
        
        Args:
            event_type: Type of event to listen for
            callback: Async function to call when event emitted
                      Signature: async def callback(event: Event) -> None
        
        Example:
            async def on_approval(event: Event):
                approval_id = event.data["approval_id"]
                await notify_approver(approval_id)
            
            bus.subscribe("approval_required", on_approval)
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        
        self._subscribers[event_type].append(callback)
        
        logger.info(
            f"Subscribed to '{event_type}' "
            f"(now {len(self._subscribers[event_type])} subscribers)"
        )
    
    def unsubscribe(
        self,
        event_type: str,
        callback: Callable[[Event], Any]
    ) -> None:
        """
        Unsubscribe from event type.
        
        Args:
            event_type: Type of event
            callback: Callback function to remove
        """
        if event_type in self._subscribers:
            try:
                self._subscribers[event_type].remove(callback)
                logger.info(f"Unsubscribed from '{event_type}'")
            except ValueError:
                logger.warning(f"Callback not found for '{event_type}'")
    
    async def emit(
        self,
        event_type: str,
        data: Dict[str, Any],
        source: str = "unknown",
        correlation_id: Optional[str] = None,
        publish_to_redis: bool = True
    ) -> None:
        """
        Emit event to all subscribers.
        
        Args:
            event_type: Type of event (approval_required, task_completed, etc.)
            data: Event payload (dict with event-specific fields)
            source: Which agent/component is emitting
            correlation_id: Optional ID to correlate related events
            publish_to_redis: Whether to broadcast to other agents via Redis
        
        Example:
            await bus.emit(
                "approval_required",
                {
                    "approval_id": "123e4567-e89b-12d3-a456-426614174000",
                    "task_description": "Deploy to production",
                    "risk_level": "high",
                    "project_name": "phase-5-chat"
                },
                source="orchestrator",
                correlation_id="task-456"
            )
        """
        # Create event object
        event = Event(
            type=event_type,
            data=data,
            timestamp=datetime.utcnow(),
            source=source,
            correlation_id=correlation_id
        )
        
        self._stats["events_emitted"] += 1
        
        # Publish to Redis if enabled and connected
        if publish_to_redis and self.redis_client:
            try:
                inter_agent_event = InterAgentEvent(
                    event_type=event_type,
                    source_agent=source,
                    payload=data,
                    correlation_id=correlation_id
                )
                await self.redis_client.publish(
                    "agent-events",
                    json.dumps(inter_agent_event.to_dict())
                )
                self._stats["redis_events_published"] += 1
            except Exception as e:
                logger.error(f"Failed to publish to Redis: {e}")

        # Get subscribers for this event type
        subscribers = self._subscribers.get(event_type, [])
        
        if not subscribers:
            # If no local subscribers, we still might have remote ones via Redis
            # so we don't warn if we published to Redis
            if not (publish_to_redis and self.redis_client):
                logger.debug(
                    f"No subscribers for event '{event_type}' from {source}"
                )
            return
        
        logger.info(
            f"Emitting '{event_type}' to {len(subscribers)} subscribers "
            f"(source: {source}, correlation_id: {correlation_id})"
        )
        
        # Call all subscribers concurrently
        tasks = []
        for callback in subscribers:
            tasks.append(self._call_subscriber(callback, event))
        
        # Wait for all subscribers (don't let one failure block others)
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Count successful deliveries
        successful = sum(1 for r in results if not isinstance(r, Exception))
        self._stats["events_delivered"] += successful
        
        if successful < len(subscribers):
            failed = len(subscribers) - successful
            logger.error(
                f"{failed}/{len(subscribers)} subscribers failed for '{event_type}'"
            )
    
    async def _call_subscriber(
        self,
        callback: Callable[[Event], Any],
        event: Event
    ) -> None:
        """
        Call subscriber callback with error handling.
        
        Args:
            callback: Subscriber function
            event: Event object
        """
        try:
            # Check if callback is async
            if asyncio.iscoroutinefunction(callback):
                await callback(event)
            else:
                # Run sync callback in executor
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, callback, event)
            
            logger.debug(f"Delivered event to {callback.__name__}")
            
        except Exception as e:
            self._stats["subscriber_errors"] += 1
            logger.error(
                f"Subscriber {callback.__name__} failed for {event.type}: {e}",
                exc_info=True
            )
    
    def get_stats(self) -> Dict[str, int]:
        """
        Get event bus statistics.
        
        Returns:
            Dict with events_emitted, events_delivered, subscriber_errors
        """
        return self._stats.copy()
    
    def list_subscribers(self) -> Dict[str, int]:
        """
        List number of subscribers per event type.
        
        Returns:
            Dict mapping event_type -> subscriber_count
        """
        return {
            event_type: len(callbacks)
            for event_type, callbacks in self._subscribers.items()
        }
    
    async def request_agent(
        self,
        request: 'AgentRequestEvent',  # Type hint as string to avoid circular import
        timeout: Optional[float] = None
    ) -> 'AgentResponseEvent':
        """
        Send request to another agent and wait for response.
        
        Args:
            request: AgentRequestEvent with target agent and payload
            timeout: Override default timeout from request.timeout_seconds
        
        Returns:
            AgentResponseEvent with result or error
        
        Raises:
            asyncio.TimeoutError: If no response within timeout
            ValueError: If no agent registered to handle request
        
        Example:
            from shared.lib.agent_events import AgentRequestEvent, AgentRequestType
            
            request = AgentRequestEvent(
                source_agent="orchestrator",
                target_agent="code-review",
                request_type=AgentRequestType.REVIEW_CODE,
                payload={"file_path": "main.py", "changes": "..."}
            )
            
            response = await bus.request_agent(request, timeout=30.0)
            
            if response.status == "success":
                print(f"Review result: {response.result}")
            else:
                print(f"Error: {response.error}")
        """
        timeout_val = timeout or request.timeout_seconds
        
        # Create future for response
        future: asyncio.Future = asyncio.Future()
        self._pending_requests[request.request_id] = future
        
        self._stats["agent_requests_sent"] += 1
        
        try:
            # Emit request event to subscribers
            await self.emit(
                "agent_request",
                request.to_dict(),
                source=request.source_agent,
                correlation_id=request.correlation_id
            )
            
            logger.info(
                f"Sent agent request {request.request_id} from "
                f"{request.source_agent} to {request.target_agent} "
                f"(type: {request.request_type}, timeout: {timeout_val}s)"
            )
            
            # Wait for response with timeout
            response_data = await asyncio.wait_for(future, timeout=timeout_val)
            
            # Import here to avoid circular dependency
            from shared.lib.agent_events import AgentResponseEvent
            
            response = AgentResponseEvent(**response_data)
            self._stats["agent_responses_received"] += 1
            
            logger.info(
                f"Received response for {request.request_id} from "
                f"{response.source_agent} (status: {response.status}, "
                f"time: {response.processing_time_ms}ms)"
            )
            
            return response
            
        except asyncio.TimeoutError:
            self._stats["agent_timeouts"] += 1
            logger.error(
                f"Agent request {request.request_id} timed out after "
                f"{timeout_val}s (target: {request.target_agent})"
            )
            
            # Create timeout response
            from shared.lib.agent_events import AgentResponseEvent, AgentResponseStatus
            
            return AgentResponseEvent(
                request_id=request.request_id,
                source_agent=request.target_agent,
                target_agent=request.source_agent,
                status=AgentResponseStatus.TIMEOUT,
                error=f"Request timed out after {timeout_val} seconds"
            )
            
        finally:
            # Clean up pending request
            self._pending_requests.pop(request.request_id, None)
    
    async def respond_to_request(
        self,
        response: 'AgentResponseEvent'
    ) -> None:
        """
        Send response to pending agent request.
        
        Args:
            response: AgentResponseEvent with result or error
        
        Example:
            # In agent endpoint handling request
            response = AgentResponseEvent(
                request_id=request.request_id,
                source_agent="code-review",
                target_agent=request.source_agent,
                status=AgentResponseStatus.SUCCESS,
                result={"issues": 3, "suggestions": ["..."]}
            )
            
            await bus.respond_to_request(response)
        """
        # Find pending request future
        future = self._pending_requests.get(response.request_id)
        
        if future and not future.done():
            # Resolve future with response data
            future.set_result(response.to_dict())
            
            logger.info(
                f"Delivered response for request {response.request_id} "
                f"from {response.source_agent} to {response.target_agent}"
            )
        else:
            logger.warning(
                f"No pending request found for {response.request_id} "
                f"(may have timed out or been cancelled)"
            )
        
        # Also emit as regular event for any subscribers
        await self.emit(
            "agent_response",
            response.to_dict(),
            source=response.source_agent,
            correlation_id=response.request_id
        )
    
    async def broadcast_to_agents(
        self,
        broadcast: 'AgentBroadcastEvent'
    ) -> None:
        """
        Broadcast event to multiple agents.
        
        Args:
            broadcast: AgentBroadcastEvent with target agents and payload
        
        Example:
            from shared.lib.agent_events import AgentBroadcastEvent
            
            broadcast = AgentBroadcastEvent(
                source_agent="orchestrator",
                target_agents=["all"],  # or specific list
                event_type="config_updated",
                payload={"config_key": "timeout", "new_value": 60}
            )
            
            await bus.broadcast_to_agents(broadcast)
        """
        await self.emit(
            "agent_broadcast",
            broadcast.to_dict(),
            source=broadcast.source_agent,
            correlation_id=broadcast.broadcast_id
        )
        
        logger.info(
            f"Broadcast {broadcast.event_type} from {broadcast.source_agent} "
            f"to {len(broadcast.target_agents)} agents"
        )


# Convenience function for global access
def get_event_bus() -> EventBus:
    """Get global event bus instance."""
    return EventBus.get_instance()


# For testing
if __name__ == "__main__":
    import asyncio
    
    logging.basicConfig(level=logging.INFO)
    
    async def main():
        bus = get_event_bus()
        
        # Test subscriber
        async def on_approval(event: Event):
            print(f"✅ Received: {event.type}")
            print(f"   Data: {event.data}")
            print(f"   Source: {event.source}")
        
        # Subscribe
        bus.subscribe("approval_required", on_approval)
        
        # Emit event
        await bus.emit(
            "approval_required",
            {
                "approval_id": "test-123",
                "task_description": "Test approval",
                "risk_level": "low"
            },
            source="test",
            correlation_id="test-correlation"
        )
        
        # Check stats
        stats = bus.get_stats()
        print(f"\n📊 Stats: {stats}")
        
        subscribers = bus.list_subscribers()
        print(f"👥 Subscribers: {subscribers}")
    
    asyncio.run(main())
