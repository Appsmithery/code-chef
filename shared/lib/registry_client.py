"""
Agent Registry Client

Auto-registration and heartbeat management for agents.
Enables dynamic agent discovery and health monitoring.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional

import httpx
from pydantic import BaseModel, Field


# ============================================================================
# Logger
# ============================================================================

logger = logging.getLogger(__name__)


# ============================================================================
# Models
# ============================================================================

class AgentCapability(BaseModel):
    """Agent capability definition"""
    name: str = Field(..., description="Capability identifier")
    description: str = Field(..., description="Human-readable description")
    parameters: Dict[str, str] = Field(default_factory=dict, description="Parameter schema")
    cost_estimate: str = Field(..., description="Estimated cost")
    tags: List[str] = Field(default_factory=list, description="Capability tags")


class AgentRegistration(BaseModel):
    """Agent registration data"""
    agent_id: str
    agent_name: str
    base_url: str
    capabilities: List[AgentCapability]
    status: str = "active"
    metadata: Optional[Dict] = None


class CapabilityMatch(BaseModel):
    """Capability search match"""
    agent_id: str
    agent_name: str
    capability: str
    description: str
    base_url: str
    tags: List[str]


# ============================================================================
# Registry Client
# ============================================================================

class RegistryClient:
    """
    Client for agent registry service.
    
    Provides auto-registration, heartbeat management, and capability discovery.
    """
    
    def __init__(
        self,
        registry_url: str,
        agent_id: str,
        agent_name: str,
        base_url: str,
        heartbeat_interval: int = 30
    ):
        """
        Initialize registry client.
        
        Args:
            registry_url: Agent registry service URL (e.g., "http://agent-registry:8009")
            agent_id: Unique agent identifier
            agent_name: Human-readable agent name
            base_url: Agent base URL
            heartbeat_interval: Heartbeat interval in seconds (default: 30)
        """
        self.registry_url = registry_url.rstrip("/")
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.base_url = base_url
        self.heartbeat_interval = heartbeat_interval
        
        self.capabilities: List[AgentCapability] = []
        self.metadata: Dict = {}
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._http_client: Optional[httpx.AsyncClient] = None
    
    def _get_http_client(self) -> httpx.AsyncClient:
        """Get HTTP client (lazy initialization)"""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=10.0)
        return self._http_client
    
    async def close(self):
        """Close HTTP client"""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
    
    async def register(
        self,
        capabilities: List[AgentCapability],
        metadata: Optional[Dict] = None,
        status: str = "active"
    ) -> bool:
        """
        Register agent with registry service.
        
        Args:
            capabilities: List of agent capabilities
            metadata: Optional metadata
            status: Agent status (active, busy, offline)
            
        Returns:
            True if registration successful, False otherwise
        """
        self.capabilities = capabilities
        self.metadata = metadata or {}
        
        registration = AgentRegistration(
            agent_id=self.agent_id,
            agent_name=self.agent_name,
            base_url=self.base_url,
            capabilities=capabilities,
            status=status,
            metadata=self.metadata
        )
        
        try:
            client = self._get_http_client()
            response = await client.post(
                f"{self.registry_url}/register",
                json=registration.model_dump(),
                timeout=10.0
            )
            response.raise_for_status()
            
            result = response.json()
            logger.info(
                f"✅ Registered agent '{self.agent_id}' with registry "
                f"at {result.get('timestamp')}"
            )
            return True
            
        except httpx.HTTPError as e:
            logger.error(f"❌ Failed to register agent '{self.agent_id}': {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error during registration: {e}")
            return False
    
    async def heartbeat(self) -> bool:
        """
        Send heartbeat to registry service.
        
        Returns:
            True if heartbeat successful, False otherwise
        """
        try:
            client = self._get_http_client()
            response = await client.post(
                f"{self.registry_url}/agents/{self.agent_id}/heartbeat",
                timeout=5.0
            )
            response.raise_for_status()
            
            result = response.json()
            logger.debug(
                f"💓 Heartbeat sent for agent '{self.agent_id}' "
                f"at {result.get('last_heartbeat')}"
            )
            return True
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(
                    f"⚠️  Agent '{self.agent_id}' not registered. "
                    "Attempting re-registration..."
                )
                # Attempt re-registration
                return await self.register(self.capabilities, self.metadata)
            else:
                logger.error(f"❌ Heartbeat failed for agent '{self.agent_id}': {e}")
                return False
        except httpx.HTTPError as e:
            logger.error(f"❌ Heartbeat failed for agent '{self.agent_id}': {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error during heartbeat: {e}")
            return False
    
    async def _heartbeat_loop(self):
        """Background task for periodic heartbeats"""
        while True:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                await self.heartbeat()
            except asyncio.CancelledError:
                logger.info(f"🛑 Heartbeat loop cancelled for agent '{self.agent_id}'")
                break
            except Exception as e:
                logger.error(f"❌ Error in heartbeat loop: {e}")
    
    async def start_heartbeat(self):
        """Start background heartbeat task"""
        if self._heartbeat_task is None or self._heartbeat_task.done():
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            logger.info(
                f"💓 Started heartbeat loop for agent '{self.agent_id}' "
                f"(interval: {self.heartbeat_interval}s)"
            )
    
    async def stop_heartbeat(self):
        """Stop background heartbeat task"""
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
            logger.info(f"🛑 Stopped heartbeat loop for agent '{self.agent_id}'")
    
    async def update_status(self, status: str) -> bool:
        """
        Update agent status.
        
        Args:
            status: New status (active, busy, offline)
            
        Returns:
            True if update successful, False otherwise
        """
        try:
            return await self.register(self.capabilities, self.metadata, status=status)
        except Exception as e:
            logger.error(f"❌ Failed to update status: {e}")
            return False
    
    async def search_capabilities(self, query: str) -> List[CapabilityMatch]:
        """
        Search for agents by capability keyword.
        
        Args:
            query: Search query (keyword)
            
        Returns:
            List of matching capabilities
        """
        try:
            client = self._get_http_client()
            response = await client.get(
                f"{self.registry_url}/capabilities/search",
                params={"q": query},
                timeout=10.0
            )
            response.raise_for_status()
            
            matches_data = response.json()
            return [CapabilityMatch(**match) for match in matches_data]
            
        except httpx.HTTPError as e:
            logger.error(f"❌ Capability search failed: {e}")
            return []
        except Exception as e:
            logger.error(f"❌ Unexpected error during search: {e}")
            return []
    
    async def get_agent(self, agent_id: str) -> Optional[Dict]:
        """
        Get agent details by ID.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            Agent details or None if not found
        """
        try:
            client = self._get_http_client()
            response = await client.get(
                f"{self.registry_url}/agents/{agent_id}",
                timeout=10.0
            )
            response.raise_for_status()
            
            return response.json()
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"⚠️  Agent '{agent_id}' not found")
                return None
            else:
                logger.error(f"❌ Failed to get agent '{agent_id}': {e}")
                return None
        except httpx.HTTPError as e:
            logger.error(f"❌ Failed to get agent '{agent_id}': {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Unexpected error getting agent: {e}")
            return None
    
    async def list_agents(self, status: Optional[str] = None) -> List[Dict]:
        """
        List all registered agents.
        
        Args:
            status: Optional status filter (active, busy, offline)
            
        Returns:
            List of agent details
        """
        try:
            client = self._get_http_client()
            params = {"status": status} if status else {}
            response = await client.get(
                f"{self.registry_url}/agents",
                params=params,
                timeout=10.0
            )
            response.raise_for_status()
            
            return response.json()
            
        except httpx.HTTPError as e:
            logger.error(f"❌ Failed to list agents: {e}")
            return []
        except Exception as e:
            logger.error(f"❌ Unexpected error listing agents: {e}")
            return []
    
    async def check_health(self, agent_id: str) -> Optional[Dict]:
        """
        Check agent health status.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            Health status or None if check failed
        """
        try:
            client = self._get_http_client()
            response = await client.get(
                f"{self.registry_url}/health/{agent_id}",
                timeout=10.0
            )
            response.raise_for_status()
            
            return response.json()
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"⚠️  Agent '{agent_id}' not found")
                return None
            else:
                logger.error(f"❌ Health check failed for '{agent_id}': {e}")
                return None
        except httpx.HTTPError as e:
            logger.error(f"❌ Health check failed for '{agent_id}': {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Unexpected error during health check: {e}")
            return None


# ============================================================================
# Context Manager Support
# ============================================================================

class RegistryClientContext:
    """
    Context manager for registry client with automatic cleanup.
    
    Usage:
        async with RegistryClientContext(...) as registry:
            await registry.register([...])
            await registry.start_heartbeat()
            # ... agent work ...
    """
    
    def __init__(self, *args, **kwargs):
        self.client = RegistryClient(*args, **kwargs)
    
    async def __aenter__(self):
        return self.client
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.stop_heartbeat()
        await self.client.close()


# ============================================================================
# Helper Functions
# ============================================================================

def create_registry_client(
    registry_url: str,
    agent_id: str,
    agent_name: str,
    base_url: str,
    **kwargs
) -> RegistryClient:
    """
    Factory function to create registry client.
    
    Args:
        registry_url: Agent registry service URL
        agent_id: Unique agent identifier
        agent_name: Human-readable agent name
        base_url: Agent base URL
        **kwargs: Additional arguments for RegistryClient
        
    Returns:
        RegistryClient instance
    """
    return RegistryClient(
        registry_url=registry_url,
        agent_id=agent_id,
        agent_name=agent_name,
        base_url=base_url,
        **kwargs
    )
