"""
Example Multi-Agent Workflow: Parallel Documentation Generation

This example demonstrates parallel agent collaboration where:
1. Orchestrator receives a request to document multiple modules
2. Routes requests to Documentation agent in parallel
3. Aggregates results and combines documentation
4. Returns unified documentation

Run this script to see parallel agent execution.

Usage:
    python examples/workflow_parallel_docs.py
"""

import asyncio
import logging
from datetime import datetime

from shared.lib.agent_events import (
    AgentRequestEvent,
    AgentResponseEvent,
    AgentRequestType,
    AgentRequestPriority
)
from shared.lib.event_bus import get_event_bus
from shared.lib.orchestrator_router import route_and_aggregate
from shared.lib.registry_client import RegistryClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def workflow_parallel_documentation():
    """
    Multi-agent parallel workflow example:
    
    Task: Generate documentation for multiple Python modules simultaneously
    
    Step 1: Create subtasks for each module
    Step 2: Route all tasks to Documentation agent in parallel
    Step 3: Aggregate results and combine documentation
    """
    event_bus = get_event_bus()
    
    # Initialize registry client
    registry_client = RegistryClient(
        registry_url="http://localhost:8009",
        agent_id="example-parallel-workflow",
        agent_name="Example Parallel Workflow",
        base_url="http://localhost:9001"
    )
    
    logger.info("=" * 60)
    logger.info("WORKFLOW: Parallel Documentation Generation")
    logger.info("=" * 60)
    
    # Define modules to document
    modules = [
        {
            "name": "auth.py",
            "code": """
def authenticate(username, password):
    '''Authenticate user credentials'''
    return validate_credentials(username, password)

def create_token(user_id):
    '''Create JWT token for user'''
    return jwt.encode({'user_id': user_id}, SECRET_KEY)
"""
        },
        {
            "name": "database.py",
            "code": """
class Database:
    '''Database connection manager'''
    
    def __init__(self, url):
        self.url = url
        self.connection = None
    
    def connect(self):
        '''Establish database connection'''
        self.connection = create_connection(self.url)
"""
        },
        {
            "name": "api.py",
            "code": """
@app.post('/api/users')
async def create_user(request: CreateUserRequest):
    '''Create new user account'''
    user = User(**request.dict())
    db.add(user)
    return {'user_id': user.id}
"""
        }
    ]
    
    # Step 1: Create subtasks
    logger.info(f"\n[Step 1] Creating {len(modules)} documentation subtasks...")
    
    subtasks = []
    for i, module in enumerate(modules):
        subtasks.append({
            "request_type": AgentRequestType.GENERATE_DOCS,
            "payload": {
                "code": module["code"],
                "format": "markdown",
                "module_name": module["name"]
            },
            "capability_keywords": ["documentation", "docs"],
            "priority": AgentRequestPriority.NORMAL,
            "timeout": 30.0
        })
    
    logger.info(f"✓ Created {len(subtasks)} subtasks")
    
    # Step 2: Execute in parallel
    logger.info(f"\n[Step 2] Executing subtasks in parallel...")
    start_time = datetime.now()
    
    result = await route_and_aggregate(
        subtasks=subtasks,
        registry_client=registry_client,
        parallel=True,
        source_agent="example-parallel-workflow"
    )
    
    end_time = datetime.now()
    total_ms = (end_time - start_time).total_seconds() * 1000
    
    logger.info(f"✓ Parallel execution completed in {total_ms:.1f}ms")
    logger.info(f"  Completed: {result['completed_count']}/{result['total_count']}")
    logger.info(f"  Failed: {result['failed_count']}")
    logger.info(f"  Success rate: {result['success_rate']*100:.1f}%")
    
    # Step 3: Aggregate documentation
    logger.info(f"\n[Step 3] Aggregating documentation...")
    
    combined_docs = "# API Documentation\n\n"
    combined_docs += "Generated using parallel multi-agent workflow\n\n"
    
    for i, subtask_result in enumerate(result["results"]):
        if subtask_result["status"] == "success":
            module_name = modules[i]["name"]
            doc_content = subtask_result["result"].get("documentation", "")
            
            combined_docs += f"## {module_name}\n\n"
            combined_docs += doc_content + "\n\n"
            
            logger.info(f"  ✓ Module {module_name}: {len(doc_content)} chars")
    
    logger.info(f"✓ Combined documentation: {len(combined_docs)} chars")
    
    # Calculate efficiency
    sequential_time_estimate = sum(
        r.get("processing_time_ms", 0) 
        for r in result["results"] 
        if isinstance(r, dict)
    )
    speedup = sequential_time_estimate / total_ms if total_ms > 0 else 1.0
    
    workflow_result = {
        "workflow": "parallel_documentation",
        "status": "completed",
        "modules_documented": result['completed_count'],
        "total_time_ms": total_ms,
        "estimated_sequential_time_ms": sequential_time_estimate,
        "speedup_factor": f"{speedup:.1f}x",
        "combined_documentation_length": len(combined_docs),
        "success_rate": result['success_rate']
    }
    
    logger.info("\n" + "=" * 60)
    logger.info("WORKFLOW COMPLETED")
    logger.info("=" * 60)
    logger.info(f"Total execution time: {total_ms:.1f}ms")
    logger.info(f"Estimated sequential time: {sequential_time_estimate:.1f}ms")
    logger.info(f"Speedup from parallelization: {speedup:.1f}x")
    logger.info(f"Modules documented: {result['completed_count']}")
    logger.info(f"Combined documentation: {len(combined_docs)} chars")
    logger.info("=" * 60)
    
    await registry_client.close()
    
    return workflow_result


async def main():
    """Run the parallel workflow example."""
    try:
        result = await workflow_parallel_documentation()
        
        if result:
            print("\n✅ Parallel workflow completed successfully!")
            print(f"   Speedup: {result['speedup_factor']}")
            print(f"   Modules: {result['modules_documented']}")
        else:
            print("\n❌ Workflow failed - check logs")
            
    except Exception as e:
        logger.error(f"Workflow error: {e}", exc_info=True)
        print(f"\n❌ Workflow error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
