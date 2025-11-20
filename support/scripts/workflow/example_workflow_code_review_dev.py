"""
Example Multi-Agent Workflow: Code Review → Feature Development

This example demonstrates inter-agent communication where:
1. Orchestrator receives a feature request
2. Routes to Code Review agent for initial assessment
3. Routes to Feature Dev agent for implementation
4. Aggregates results and returns to user

Run this script to see agents collaborating on a realistic task.

Usage:
    python examples/workflow_code_review_dev.py
"""

import asyncio
import logging
from datetime import datetime
import httpx

from shared.lib.agent_events import (
    AgentRequestEvent,
    AgentResponseEvent,
    AgentRequestType,
    AgentRequestPriority
)
from shared.lib.event_bus import get_event_bus
from shared.lib.registry_client import RegistryClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def workflow_code_review_then_feature_dev():
    """
    Multi-agent workflow example:
    
    Task: Add input validation to login endpoint
    
    Step 1: Code Review agent assesses current implementation
    Step 2: Feature Dev agent generates improved code with validation
    Step 3: Code Review agent reviews the generated code
    Step 4: Results aggregated and returned
    """
    event_bus = get_event_bus()
    
    # Initialize registry client
    registry_client = RegistryClient(
        registry_url="http://localhost:8009",
        agent_id="example-workflow",
        agent_name="Example Workflow",
        base_url="http://localhost:9000"
    )
    
    logger.info("=" * 60)
    logger.info("WORKFLOW: Code Review → Feature Development")
    logger.info("=" * 60)
    
    # Step 1: Request initial code review
    logger.info("\n[Step 1] Requesting code review of current implementation...")
    
    review_request = AgentRequestEvent(
        source_agent="example-workflow",
        target_agent="code-review",
        request_type=AgentRequestType.REVIEW_CODE,
        payload={
            "file_path": "backend/auth/login.py",
            "changes": """
def login(username, password):
    user = db.query(User).filter(User.username == username).first()
    if user and user.password == password:
        return create_token(user)
    return None
""",
            "context": {
                "task": "Add input validation to login endpoint",
                "language": "python"
            }
        },
        priority=AgentRequestPriority.HIGH,
        timeout_seconds=30.0
    )
    
    review_response = await event_bus.request_agent(review_request)
    
    if review_response.status != "success":
        logger.error(f"Code review failed: {review_response.error}")
        return
    
    logger.info(f"✓ Code review completed in {review_response.processing_time_ms:.1f}ms")
    logger.info(f"  Issues found: {review_response.result.get('issues', 0)}")
    logger.info(f"  Severity: {review_response.result.get('severity', 'unknown')}")
    
    # Step 2: Request feature development with validation
    logger.info("\n[Step 2] Requesting feature development with input validation...")
    
    feature_request = AgentRequestEvent(
        source_agent="example-workflow",
        target_agent="feature-dev",
        request_type=AgentRequestType.GENERATE_CODE,
        payload={
            "requirements": """
Add comprehensive input validation to login endpoint:
- Validate username format (alphanumeric, 3-20 chars)
- Validate password strength (min 8 chars, mixed case, numbers)
- Sanitize inputs to prevent SQL injection
- Add rate limiting hints
- Return appropriate error messages
""",
            "language": "python",
            "context": {
                "current_code": review_request.payload["changes"],
                "review_issues": review_response.result.get("issues", [])
            }
        },
        priority=AgentRequestPriority.HIGH,
        timeout_seconds=45.0
    )
    
    feature_response = await event_bus.request_agent(feature_request)
    
    if feature_response.status != "success":
        logger.error(f"Feature development failed: {feature_response.error}")
        return
    
    logger.info(f"✓ Code generation completed in {feature_response.processing_time_ms:.1f}ms")
    logger.info(f"  Generated code: {len(feature_response.result.get('generated_code', ''))} chars")
    logger.info(f"  Tests included: {feature_response.result.get('tests_included', False)}")
    
    # Step 3: Final review of generated code
    logger.info("\n[Step 3] Requesting final review of generated code...")
    
    final_review_request = AgentRequestEvent(
        source_agent="example-workflow",
        target_agent="code-review",
        request_type=AgentRequestType.REVIEW_CODE,
        payload={
            "file_path": "backend/auth/login.py",
            "changes": feature_response.result.get("generated_code", ""),
            "context": {
                "task": "Final review after adding validation",
                "language": "python"
            }
        },
        priority=AgentRequestPriority.NORMAL,
        timeout_seconds=30.0
    )
    
    final_review_response = await event_bus.request_agent(final_review_request)
    
    if final_review_response.status != "success":
        logger.error(f"Final review failed: {final_review_response.error}")
        return
    
    logger.info(f"✓ Final review completed in {final_review_response.processing_time_ms:.1f}ms")
    logger.info(f"  Approved: {final_review_response.result.get('approved', False)}")
    logger.info(f"  Remaining issues: {final_review_response.result.get('issues', 0)}")
    
    # Step 4: Aggregate results
    logger.info("\n[Step 4] Aggregating workflow results...")
    
    total_time_ms = (
        review_response.processing_time_ms +
        feature_response.processing_time_ms +
        final_review_response.processing_time_ms
    )
    
    workflow_result = {
        "workflow": "code_review_feature_dev",
        "status": "completed",
        "total_time_ms": total_time_ms,
        "steps": [
            {
                "step": 1,
                "agent": "code-review",
                "action": "initial_review",
                "status": review_response.status,
                "time_ms": review_response.processing_time_ms
            },
            {
                "step": 2,
                "agent": "feature-dev",
                "action": "generate_code",
                "status": feature_response.status,
                "time_ms": feature_response.processing_time_ms
            },
            {
                "step": 3,
                "agent": "code-review",
                "action": "final_review",
                "status": final_review_response.status,
                "time_ms": final_review_response.processing_time_ms
            }
        ],
        "final_approved": final_review_response.result.get("approved", False),
        "improvements": {
            "initial_issues": review_response.result.get("issues", 0),
            "final_issues": final_review_response.result.get("issues", 0),
            "improvement_rate": "100%" if final_review_response.result.get("issues", 0) == 0 else "partial"
        }
    }
    
    logger.info("\n" + "=" * 60)
    logger.info("WORKFLOW COMPLETED")
    logger.info("=" * 60)
    logger.info(f"Total execution time: {total_time_ms:.1f}ms")
    logger.info(f"Agents involved: code-review, feature-dev")
    logger.info(f"Steps completed: {len(workflow_result['steps'])}")
    logger.info(f"Final approval: {workflow_result['final_approved']}")
    logger.info("=" * 60)
    
    await registry_client.close()
    
    return workflow_result


async def main():
    """Run the workflow example."""
    try:
        result = await workflow_code_review_then_feature_dev()
        
        if result:
            print("\n✅ Workflow completed successfully!")
            print(f"   See logs above for details")
        else:
            print("\n❌ Workflow failed - check logs")
            
    except Exception as e:
        logger.error(f"Workflow error: {e}", exc_info=True)
        print(f"\n❌ Workflow error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
