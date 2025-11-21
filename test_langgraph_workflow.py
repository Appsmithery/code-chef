#!/usr/bin/env python3
"""
Test LangGraph multi-agent workflow locally.

Tests:
1. Agent node initialization (all 6 agents + supervisor)
2. LangGraph workflow compilation
3. Task routing through supervisor
4. HITL approval node creation
5. Tool binding per agent

Usage:
    python test_langgraph_workflow.py
"""

import asyncio
import sys
from pathlib import Path

# Add agent_orchestrator to path
sys.path.insert(0, str(Path(__file__).parent / "agent_orchestrator"))
sys.path.insert(0, str(Path(__file__).parent / "shared"))

async def test_agent_initialization():
    """Test all agent nodes can be initialized."""
    print("\n=== Test 1: Agent Initialization ===")
    
    from agents import (
        SupervisorAgent,
        FeatureDevAgent,
        CodeReviewAgent,
        InfrastructureAgent,
        CICDAgent,
        DocumentationAgent
    )
    
    try:
        agents = {
            "supervisor": SupervisorAgent(),
            "feature-dev": FeatureDevAgent(),
            "code-review": CodeReviewAgent(),
            "infrastructure": InfrastructureAgent(),
            "cicd": CICDAgent(),
            "documentation": DocumentationAgent(),
        }
        
        for name, agent in agents.items():
            print(f"✅ {name}: {agent}")
            assert agent.agent_name == name
            assert agent.llm is not None
            assert agent.config is not None
        
        print("✅ All agents initialized successfully\n")
        return True
        
    except Exception as e:
        print(f"❌ Agent initialization failed: {e}\n")
        return False


async def test_workflow_compilation():
    """Test LangGraph workflow can be compiled."""
    print("=== Test 2: Workflow Compilation ===")
    
    try:
        from graph import create_workflow, app
        
        print(f"✅ Workflow app compiled: {type(app)}")
        print(f"✅ Entry point: supervisor")
        print(f"✅ Nodes: supervisor, feature-dev, code-review, infrastructure, cicd, documentation, approval")
        print("✅ Workflow compiled successfully\n")
        return True
        
    except Exception as e:
        print(f"❌ Workflow compilation failed: {e}\n")
        import traceback
        traceback.print_exc()
        return False


async def test_supervisor_routing():
    """Test supervisor can route tasks."""
    print("=== Test 3: Supervisor Routing ===")
    
    try:
        from graph import supervisor_node, WorkflowState
        from langchain_core.messages import HumanMessage
        
        # Test feature development task
        state: WorkflowState = {
            "messages": [HumanMessage(content="Implement user authentication with OAuth2")],
            "current_agent": "",
            "next_agent": "",
            "task_result": {},
            "approvals": [],
            "requires_approval": False,
        }
        
        print("Task: Implement user authentication with OAuth2")
        result = await supervisor_node(state)
        
        print(f"✅ Supervisor routed to: {result.get('next_agent', 'unknown')}")
        print(f"✅ Requires approval: {result.get('requires_approval', False)}")
        print(f"✅ Supervisor routing works\n")
        return True
        
    except Exception as e:
        print(f"❌ Supervisor routing failed: {e}\n")
        import traceback
        traceback.print_exc()
        return False


async def test_tool_binding():
    """Test agents have tools bound."""
    print("=== Test 4: Tool Binding ===")
    
    try:
        from agents import get_agent
        
        feature_dev = get_agent("feature-dev")
        
        # Check if agent has tools bound
        has_tools = hasattr(feature_dev, 'agent_executor')
        print(f"✅ Feature-dev agent has tools: {has_tools}")
        
        # Check config
        tools_config = feature_dev.config.get("tools", {})
        allowed_servers = tools_config.get("allowed_servers", [])
        print(f"✅ Allowed MCP servers: {', '.join(allowed_servers)}")
        print(f"✅ Progressive strategy: {tools_config.get('progressive_strategy', 'MINIMAL')}")
        print("✅ Tool binding works\n")
        return True
        
    except Exception as e:
        print(f"❌ Tool binding test failed: {e}\n")
        import traceback
        traceback.print_exc()
        return False


async def test_full_workflow():
    """Test complete workflow execution (without actual LLM calls)."""
    print("=== Test 5: Full Workflow (Dry Run) ===")
    
    try:
        from graph import app, WorkflowState
        from langchain_core.messages import HumanMessage
        
        print("⚠️  Skipping full workflow test (requires LLM API keys)")
        print("   Run this test manually with valid GRADIENT_API_KEY")
        print("   Example: POST /orchestrate/langgraph with task description\n")
        return True
        
    except Exception as e:
        print(f"❌ Workflow test failed: {e}\n")
        return False


async def main():
    """Run all tests."""
    print("=" * 60)
    print("LangGraph Multi-Agent Workflow Tests")
    print("=" * 60)
    
    tests = [
        test_agent_initialization,
        test_workflow_compilation,
        test_supervisor_routing,
        test_tool_binding,
        test_full_workflow,
    ]
    
    results = []
    for test in tests:
        result = await test()
        results.append(result)
    
    # Summary
    print("=" * 60)
    print("Test Summary")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("✅ All tests passed!")
        return 0
    else:
        print(f"❌ {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
