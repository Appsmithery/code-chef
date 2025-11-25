#!/usr/bin/env python3
"""
Agent Registry Service

Centralized registry for agent discovery, capability matching, and health monitoring.
Enables dynamic agent-to-agent communication and multi-agent collaboration.
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from contextlib import asynccontextmanager

import asyncpg
from fastapi import FastAPI, HTTPException, Query
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel, Field


# ============================================================================
# Configuration
# ============================================================================

PORT = int(os.getenv("PORT", "8009"))

# Build database URL
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "devtools")
POSTGRES_USER = os.getenv("POSTGRES_USER", "devtools")

# Read password from Docker secret file or environment variable
POSTGRES_PASSWORD_FILE = os.getenv("POSTGRES_PASSWORD_FILE")
if POSTGRES_PASSWORD_FILE and os.path.exists(POSTGRES_PASSWORD_FILE):
    with open(POSTGRES_PASSWORD_FILE, "r") as f:
        POSTGRES_PASSWORD = f.read().strip()
        # If secret file is empty, try environment variable
        if not POSTGRES_PASSWORD:
            POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")
else:
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")

DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

HEARTBEAT_TIMEOUT_SECONDS = int(os.getenv("HEARTBEAT_TIMEOUT_SECONDS", "60"))


# ============================================================================
# Pydantic Models
# ============================================================================


class AgentCapability(BaseModel):
    """Agent capability definition"""

    name: str = Field(..., description="Capability identifier (e.g., 'code_review')")
    description: str = Field(..., description="Human-readable description")
    parameters: Dict[str, str] = Field(
        default_factory=dict,
        description="Parameter schema (e.g., {'repo_url': 'str', 'pr_number': 'int'})",
    )
    cost_estimate: str = Field(
        ..., description="Estimated cost (e.g., '~100 tokens' or '~30s compute')"
    )
    tags: List[str] = Field(
        default_factory=list,
        description="Capability tags for search (e.g., ['git', 'security'])",
    )


class AgentRegistration(BaseModel):
    """Agent registration data"""

    agent_id: str = Field(..., description="Unique agent identifier")
    agent_name: str = Field(..., description="Human-readable agent name")
    base_url: str = Field(
        ..., description="Agent base URL (e.g., 'http://code-review:8003')"
    )
    capabilities: List[AgentCapability] = Field(..., description="Agent capabilities")
    status: str = Field(
        default="active", description="Agent status: active, busy, offline"
    )
    metadata: Optional[Dict] = Field(
        default_factory=dict, description="Additional metadata"
    )


class AgentInfo(AgentRegistration):
    """Agent info with timestamps"""

    last_heartbeat: datetime
    created_at: datetime
    updated_at: datetime


class HeartbeatResponse(BaseModel):
    """Heartbeat response"""

    status: str
    agent_id: str
    last_heartbeat: datetime


class CapabilityMatch(BaseModel):
    """Capability search match"""

    agent_id: str
    agent_name: str
    capability: str
    description: str
    base_url: str
    tags: List[str]


class HealthStatus(BaseModel):
    """Agent health status"""

    agent_id: str
    agent_name: str
    status: str
    last_heartbeat: datetime
    is_healthy: bool
    seconds_since_heartbeat: float


# ============================================================================
# Database Connection Pool
# ============================================================================

db_pool: Optional[asyncpg.Pool] = None


async def get_db_pool() -> asyncpg.Pool:
    """Get database connection pool"""
    global db_pool
    if db_pool is None:
        db_pool = await asyncpg.create_pool(
            DATABASE_URL, min_size=2, max_size=10, command_timeout=30
        )
    return db_pool


async def close_db_pool():
    """Close database connection pool"""
    global db_pool
    if db_pool:
        await db_pool.close()
        db_pool = None


# ============================================================================
# Lifespan Management
# ============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown"""
    # Startup
    print("🚀 Agent Registry Service starting...")
    await get_db_pool()
    print("✅ Database pool initialized")

    # Start cleanup task
    cleanup_task = asyncio.create_task(cleanup_stale_agents())

    yield

    # Shutdown
    print("🛑 Agent Registry Service shutting down...")
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass
    await close_db_pool()
    print("✅ Cleanup complete")


# ============================================================================
# FastAPI Application
# ============================================================================

app = FastAPI(
    title="Agent Registry Service",
    description="Centralized registry for agent discovery and health monitoring",
    version="1.0.0",
    lifespan=lifespan,
)

# Prometheus metrics
Instrumentator().instrument(app).expose(app)


# ============================================================================
# Background Tasks
# ============================================================================


async def cleanup_stale_agents():
    """Periodically mark stale agents as offline"""
    while True:
        try:
            await asyncio.sleep(30)  # Run every 30 seconds

            pool = await get_db_pool()
            async with pool.acquire() as conn:
                # Mark agents offline if no heartbeat in HEARTBEAT_TIMEOUT_SECONDS
                cutoff = datetime.utcnow() - timedelta(
                    seconds=HEARTBEAT_TIMEOUT_SECONDS
                )

                result = await conn.execute(
                    """
                    UPDATE agent_registry
                    SET status = 'offline', updated_at = NOW()
                    WHERE last_heartbeat < $1 AND status != 'offline'
                    """,
                    cutoff,
                )

                if result != "UPDATE 0":
                    print(f"⚠️  Marked stale agents offline: {result}")

        except asyncio.CancelledError:
            raise
        except Exception as e:
            print(f"❌ Error in cleanup task: {e}")


# ============================================================================
# API Endpoints
# ============================================================================


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")

        return {
            "status": "healthy",
            "service": "agent-registry",
            "database": "connected",
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "agent-registry",
            "database": "disconnected",
            "error": str(e),
        }


@app.post("/register")
async def register_agent(registration: AgentRegistration):
    """Register or update an agent"""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            now = datetime.utcnow()

            # Serialize capabilities to JSON
            import json as json_lib

            capabilities_json = json_lib.dumps(
                [cap.model_dump() for cap in registration.capabilities]
            )
            metadata_json = json_lib.dumps(registration.metadata or {})

            # Upsert agent registration
            await conn.execute(
                """
                INSERT INTO agent_registry (
                    agent_id, agent_name, base_url, status, 
                    capabilities, metadata, last_heartbeat, created_at, updated_at
                )
                VALUES ($1, $2, $3, $4, $5::jsonb, $6::jsonb, $7, $8, $8)
                ON CONFLICT (agent_id) DO UPDATE SET
                    agent_name = EXCLUDED.agent_name,
                    base_url = EXCLUDED.base_url,
                    status = EXCLUDED.status,
                    capabilities = EXCLUDED.capabilities,
                    metadata = EXCLUDED.metadata,
                    last_heartbeat = EXCLUDED.last_heartbeat,
                    updated_at = EXCLUDED.updated_at
                """,
                registration.agent_id,
                registration.agent_name,
                registration.base_url,
                registration.status,
                capabilities_json,
                metadata_json,
                now,
                now,
            )

            return {
                "status": "registered",
                "agent_id": registration.agent_id,
                "timestamp": now.isoformat(),
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")


@app.get("/agents", response_model=List[AgentInfo])
async def list_agents(
    status: Optional[str] = Query(
        None, description="Filter by status: active, busy, offline"
    )
):
    """List all registered agents"""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            if status:
                rows = await conn.fetch(
                    """
                    SELECT agent_id, agent_name, base_url, status, capabilities,
                           metadata, last_heartbeat, created_at, updated_at
                    FROM agent_registry
                    WHERE status = $1
                    ORDER BY agent_name
                    """,
                    status,
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT agent_id, agent_name, base_url, status, capabilities,
                           metadata, last_heartbeat, created_at, updated_at
                    FROM agent_registry
                    ORDER BY agent_name
                    """
                )

            agents = []
            for row in rows:
                # Parse capabilities from JSON (already deserialized by asyncpg)
                import json as json_lib

                caps_data = row["capabilities"]
                if isinstance(caps_data, str):
                    caps_data = json_lib.loads(caps_data)

                capabilities = [AgentCapability(**cap) for cap in caps_data]

                metadata = row["metadata"]
                if isinstance(metadata, str):
                    metadata = json_lib.loads(metadata)

                agents.append(
                    AgentInfo(
                        agent_id=row["agent_id"],
                        agent_name=row["agent_name"],
                        base_url=row["base_url"],
                        status=row["status"],
                        capabilities=capabilities,
                        metadata=metadata,
                        last_heartbeat=row["last_heartbeat"],
                        created_at=row["created_at"],
                        updated_at=row["updated_at"],
                    )
                )

            return agents

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list agents: {str(e)}")


@app.get("/agents/{agent_id}", response_model=AgentInfo)
async def get_agent(agent_id: str):
    """Get specific agent details"""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT agent_id, agent_name, base_url, status, capabilities,
                       metadata, last_heartbeat, created_at, updated_at
                FROM agent_registry
                WHERE agent_id = $1
                """,
                agent_id,
            )

            if not row:
                raise HTTPException(
                    status_code=404, detail=f"Agent '{agent_id}' not found"
                )

            # Parse capabilities from JSON
            import json as json_lib

            caps_data = row["capabilities"]
            if isinstance(caps_data, str):
                caps_data = json_lib.loads(caps_data)

            capabilities = [AgentCapability(**cap) for cap in caps_data]

            metadata = row["metadata"]
            if isinstance(metadata, str):
                metadata = json_lib.loads(metadata)

            return AgentInfo(
                agent_id=row["agent_id"],
                agent_name=row["agent_name"],
                base_url=row["base_url"],
                status=row["status"],
                capabilities=capabilities,
                metadata=metadata,
                last_heartbeat=row["last_heartbeat"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get agent: {str(e)}")


@app.post("/agents/{agent_id}/heartbeat", response_model=HeartbeatResponse)
async def agent_heartbeat(agent_id: str):
    """Update agent heartbeat"""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            now = datetime.utcnow()

            result = await conn.execute(
                """
                UPDATE agent_registry
                SET last_heartbeat = $1, updated_at = $1, status = 'active'
                WHERE agent_id = $2
                """,
                now,
                agent_id,
            )

            if result == "UPDATE 0":
                raise HTTPException(
                    status_code=404,
                    detail=f"Agent '{agent_id}' not registered. Please register first.",
                )

            return HeartbeatResponse(status="ok", agent_id=agent_id, last_heartbeat=now)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Heartbeat failed: {str(e)}")


@app.get("/capabilities/search", response_model=List[CapabilityMatch])
async def search_capabilities(
    q: str = Query(..., description="Search query (keyword)")
):
    """Search for agents by capability keyword"""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT agent_id, agent_name, base_url, capabilities
                FROM agent_registry
                WHERE status = 'active'
                """
            )

            matches = []
            query_lower = q.lower()

            import json as json_lib

            for row in rows:
                caps_data = row["capabilities"]
                if isinstance(caps_data, str):
                    caps_data = json_lib.loads(caps_data)

                for cap in caps_data:
                    # Search in name, description, and tags
                    name_match = query_lower in cap["name"].lower()
                    desc_match = query_lower in cap["description"].lower()
                    tags_match = any(
                        query_lower in tag.lower() for tag in cap.get("tags", [])
                    )

                    if name_match or desc_match or tags_match:
                        matches.append(
                            CapabilityMatch(
                                agent_id=row["agent_id"],
                                agent_name=row["agent_name"],
                                capability=cap["name"],
                                description=cap["description"],
                                base_url=row["base_url"],
                                tags=cap.get("tags", []),
                            )
                        )

            return matches

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@app.get("/health/{agent_id}", response_model=HealthStatus)
async def check_agent_health(agent_id: str):
    """Check agent health status"""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT agent_id, agent_name, status, last_heartbeat
                FROM agent_registry
                WHERE agent_id = $1
                """,
                agent_id,
            )

            if not row:
                raise HTTPException(
                    status_code=404, detail=f"Agent '{agent_id}' not found"
                )

            now = datetime.utcnow()
            seconds_since_heartbeat = (now - row["last_heartbeat"]).total_seconds()
            is_healthy = seconds_since_heartbeat < HEARTBEAT_TIMEOUT_SECONDS

            return HealthStatus(
                agent_id=row["agent_id"],
                agent_name=row["agent_name"],
                status=row["status"],
                last_heartbeat=row["last_heartbeat"],
                is_healthy=is_healthy,
                seconds_since_heartbeat=seconds_since_heartbeat,
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    print(f"🚀 Starting Agent Registry on port {PORT}")

    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info")
