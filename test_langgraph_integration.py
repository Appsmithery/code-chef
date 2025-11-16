"""
Test script for LangGraph workflow integration.

Validates workflow compilation, invocation, and streaming.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from agents.langgraph.workflow import build_workflow, invoke_workflow, stream_workflow
from agents.feature_dev.service import FeatureRequest

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_workflow_compilation():
    """Test that workflow compiles without errors."""
    logger.info("Testing workflow compilation...")
    
    try:
        graph = build_workflow(enable_checkpointing=False)
        logger.info("✓ Workflow compiled successfully")
        return True
    except Exception as e:
        logger.error(f"✗ Workflow compilation failed: {e}")
        return False


async def test_workflow_invocation():
    """Test workflow invocation with request payload."""
    logger.info("Testing workflow invocation...")
    
    try:
        from agents.langgraph.state import empty_agent_state
        
        graph = build_workflow(enable_checkpointing=False)
        
        # Create initial state with helper
        state = empty_agent_state("Build a REST API with FastAPI")
        state["feature_request"] = FeatureRequest(
            feature_name="api-service",
            description="REST API service with authentication",
            requirements=["FastAPI", "PostgreSQL", "JWT authentication"]
        ).model_dump()
        
        # Invoke workflow
        result = await graph.ainvoke(state)
        
        # Validate result - check if task_id exists in result
        if "task_id" not in result:
            logger.warning("task_id not found in result, checking other keys...")
            logger.info(f"Result keys: {list(result.keys())}")
        
        assert "task_description" in result
        assert result["task_description"] == "Build a REST API with FastAPI"
        
        task_id = result.get("task_id", "unknown")
        logger.info(f"✓ Workflow invoked successfully: task_id={task_id}")
        return True
        
    except Exception as e:
        logger.error(f"✗ Workflow invocation failed: {e}", exc_info=True)
        return False


async def test_workflow_streaming():
    """Test workflow streaming."""
    logger.info("Testing workflow streaming...")
    
    try:
        graph = build_workflow(enable_checkpointing=False)
        
        events = []
        async for event in stream_workflow(
            graph=graph,
            task_description="Build a REST API with FastAPI",
            stream_mode="values"
        ):
            events.append(event)
            logger.info(f"  Stream event: {list(event.keys())}")
        
        assert len(events) > 0, "No stream events received"
        
        logger.info(f"✓ Workflow streaming successful: {len(events)} events")
        return True
        
    except Exception as e:
        logger.error(f"✗ Workflow streaming failed: {e}")
        return False


def test_checkpointer_initialization():
    """Test PostgreSQL checkpointer initialization."""
    logger.info("Testing checkpointer initialization...")
    
    try:
        from agents.langgraph.checkpointer import get_postgres_checkpointer
        
        checkpointer = get_postgres_checkpointer()
        
        if checkpointer:
            logger.info("✓ PostgreSQL checkpointer connected")
        else:
            logger.warning("⚠ PostgreSQL checkpointer disabled (DB_PASSWORD not configured)")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Checkpointer initialization failed: {e}")
        return False


def test_gradient_llm_wrapper():
    """Test LangChain Gradient LLM wrapper."""
    logger.info("Testing Gradient LLM wrapper...")
    
    try:
        from agents._shared.langchain_gradient import get_gradient_llm
        
        llm = get_gradient_llm(
            agent_name="test-agent",
            model="llama-3.1-8b-instruct"
        )
        
        assert llm._llm_type == "gradient"
        assert llm.agent_name == "test-agent"
        
        logger.info("✓ Gradient LLM wrapper initialized")
        return True
        
    except Exception as e:
        logger.error(f"✗ Gradient LLM wrapper failed: {e}")
        return False


async def main():
    """Run all tests."""
    logger.info("=" * 60)
    logger.info("LangGraph Integration Tests")
    logger.info("=" * 60)
    
    results = {
        "Workflow Compilation": test_workflow_compilation(),
        "Workflow Invocation": await test_workflow_invocation(),
        "Workflow Streaming": await test_workflow_streaming(),
        "Checkpointer Initialization": test_checkpointer_initialization(),
        "Gradient LLM Wrapper": test_gradient_llm_wrapper(),
    }
    
    logger.info("\n" + "=" * 60)
    logger.info("Test Results Summary")
    logger.info("=" * 60)
    
    for test_name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        symbol = "✓" if passed else "✗"
        logger.info(f"{symbol} {test_name}: {status}")
    
    total = len(results)
    passed = sum(results.values())
    logger.info(f"\nTotal: {passed}/{total} tests passed")
    
    return all(results.values())


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
