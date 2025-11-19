"""
Event Bus - Pub/Sub Pattern for Agent Notifications

Provides in-memory event routing with Redis fallback option.

Supported Events:
- approval_required: HITL approval request created
- approval_approved: HITL approval granted
- approval_rejected: HITL approval denied
- task_completed: Task finished successfully
- task_failed: Task failed with error
- agent_error: Agent encountered critical error

Usage:
    from shared.lib.event_bus import EventBus, Event
    
    # Initialize singleton
    bus = EventBus.get_instance()
    
    # Subscribe to events
    async def on_approval_required(event: Event):
        print(f"Approval needed: {event.data['approval_id']}")
    
    bus.subscribe("approval_required", on_approval_required)
    
    # Emit events
    await bus.emit("approval_required", {
        "approval_id": "123e4567-e89b-12d3-a456-426614174000",
        "task_description": "Deploy production changes",
        "risk_level": "high"
    })
"""

import asyncio
import logging
from typing import Dict, List, Callable, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import os
from enum import Enum

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Supported event types."""
    APPROVAL_REQUIRED = "approval_required"
    APPROVAL_APPROVED = "approval_approved"
    APPROVAL_REJECTED = "approval_rejected"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    AGENT_ERROR = "agent_error"


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
    In-memory event bus with pub/sub pattern.
    
    Features:
    - Async subscriber callbacks
    - Multiple subscribers per event type
    - Error handling (failed subscribers don't block others)
    - Singleton pattern for global access
    - Optional Redis backend (future)
    """
    
    _instance: Optional['EventBus'] = None
    
    def __init__(self):
        """Initialize event bus with empty subscribers."""
        self._subscribers: Dict[str, List[Callable]] = {}
        self._stats: Dict[str, int] = {
            "events_emitted": 0,
            "events_delivered": 0,
            "subscriber_errors": 0
        }
        logger.info("Event bus initialized")
    
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
        correlation_id: Optional[str] = None
    ) -> None:
        """
        Emit event to all subscribers.
        
        Args:
            event_type: Type of event (approval_required, task_completed, etc.)
            data: Event payload (dict with event-specific fields)
            source: Which agent/component is emitting
            correlation_id: Optional ID to correlate related events
        
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
        
        # Get subscribers for this event type
        subscribers = self._subscribers.get(event_type, [])
        
        if not subscribers:
            logger.warning(
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
