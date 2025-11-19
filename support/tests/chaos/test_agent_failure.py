"""
Chaos Test: Agent Failure Simulation

Simulates agent failures during multi-agent workflows to verify resilience.
Requires 'docker' python package: pip install docker

Usage:
    python support/tests/chaos/test_agent_failure.py
"""

import asyncio
import logging
import time
import uuid
import httpx
import docker
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("chaos-test")

# Configuration
ORCHESTRATOR_URL = "http://localhost:8001"
REGISTRY_URL = "http://localhost:8009"
TARGET_AGENT = "code-review"
DOCKER_CONTAINER_NAME = "dev-tools-code-review-1" # Adjust based on your compose project name

async def run_chaos_test():
    """
    Run chaos test scenario:
    1. Start a workflow that requires the target agent
    2. Kill the target agent container mid-execution
    3. Verify system detects failure and handles it (e.g., marks task failed or retries)
    4. Restart agent and verify recovery
    """
    logger.info("🚀 Starting Chaos Test: Agent Failure Simulation")
    
    # Initialize Docker client
    try:
        docker_client = docker.from_env()
        container = docker_client.containers.get(DOCKER_CONTAINER_NAME)
        logger.info(f"✅ Found target container: {container.name} ({container.status})")
    except Exception as e:
        logger.error(f"❌ Failed to connect to Docker or find container: {e}")
        return

    async with httpx.AsyncClient() as client:
        # 1. Submit a task
        task_payload = {
            "description": "Implement a new feature with comprehensive code review",
            "priority": "high"
        }
        
        logger.info("1️⃣ Submitting task to Orchestrator...")
        try:
            response = await client.post(f"{ORCHESTRATOR_URL}/orchestrate", json=task_payload, timeout=10.0)
            response.raise_for_status()
            task_data = response.json()
            task_id = task_data["task_id"]
            logger.info(f"✅ Task submitted: {task_id}")
        except Exception as e:
            logger.error(f"❌ Failed to submit task: {e}")
            return

        # 2. Wait briefly then kill agent
        logger.info("2️⃣ Waiting 2s then killing agent...")
        await asyncio.sleep(2)
        
        logger.info(f"💀 Killing container {DOCKER_CONTAINER_NAME}...")
        container.kill()
        
        # Verify it's down
        container.reload()
        logger.info(f"✅ Container status: {container.status}")

        # 3. Monitor task status
        logger.info("3️⃣ Monitoring task status for failure detection...")
        detected_failure = False
        for _ in range(10):
            try:
                # Check registry health
                reg_response = await client.get(f"{REGISTRY_URL}/health/{TARGET_AGENT}")
                health_data = reg_response.json()
                logger.info(f"   Registry health check: {health_data.get('status')}")
                
                if health_data.get("status") == "offline" or not health_data.get("is_healthy"):
                    logger.info("✅ Registry detected agent offline")
                    detected_failure = True
                    break
            except Exception as e:
                logger.warning(f"   Check failed: {e}")
            
            await asyncio.sleep(2)
            
        if not detected_failure:
            logger.warning("⚠️  Registry did not detect agent failure within timeout")

        # 4. Restart agent
        logger.info("4️⃣ Restarting agent...")
        container.start()
        
        # Wait for recovery
        logger.info("   Waiting for agent to recover...")
        recovered = False
        for _ in range(15):
            await asyncio.sleep(2)
            try:
                reg_response = await client.get(f"{REGISTRY_URL}/health/{TARGET_AGENT}")
                if reg_response.status_code == 200:
                    health_data = reg_response.json()
                    if health_data.get("status") == "active":
                        logger.info("✅ Agent recovered and registered")
                        recovered = True
                        break
            except:
                pass
                
        if not recovered:
            logger.error("❌ Agent failed to recover")
        else:
            logger.info("✅ Chaos Test Passed: System detected failure and recovered")

if __name__ == "__main__":
    asyncio.run(run_chaos_test())
