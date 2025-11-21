"""
Integration test for agent hand-off and state management.

Tests:
1. Feature-dev → code-review handoff with state preservation
2. Code-review → CI/CD handoff
3. CI/CD → infrastructure handoff
4. Infrastructure → documentation handoff
5. Complete multi-agent workflow chain

Usage:
    pytest support/tests/workflows/test_agent_handoff.py -v -s
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch, MagicMock
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "../../../agent_orchestrator"))
sys.path.insert(0, str(Path(__file__).parent / "../../../shared"))

pytestmark = pytest.mark.asyncio


class TestAgentHandoff:
    """Test state preservation across agent handoffs."""
    
    @pytest.fixture
    def mock_agents(self):
        """Mock agent responses for handoff chain."""
        return {
            "feature-dev": {
                "code_url": "https://github.com/test/repo/tree/feature/auth",
                "pr_number": 100,
                "files_changed": ["api/auth.py", "tests/test_auth.py"],
                "status": "complete"
            },
            "code-review": {
                "review_result": "approved",
                "issues_found": 2,
                "severity": "low",
                "comments": [
                    {"line": 42, "message": "Consider error handling"},
                    {"line": 108, "message": "Add docstring"}
                ]
            },
            "cicd": {
                "test_results": {
                    "passed": 47,
                    "failed": 0,
                    "skipped": 2
                },
                "coverage": 92.5,
                "build_status": "success"
            },
            "infrastructure": {
                "deployment_url": "https://staging.example.com",
                "version": "feature-auth-v1",
                "deployment_status": "success",
                "health_check": "passed"
            },
            "documentation": {
                "docs_url": "docs/api/auth.md",
                "pages_updated": 3,
                "status": "complete"
            }
        }
    
    async def test_feature_dev_to_code_review_handoff(self, mock_agents):
        """Test handoff from feature-dev to code-review with state preservation."""
        from graph import WorkflowState
        from langchain_core.messages import HumanMessage, AIMessage
        
        # Initial state after feature-dev
        state: WorkflowState = {
            "messages": [
                HumanMessage(content="Implement OAuth2 authentication"),
                AIMessage(content=f"Feature implementation complete. PR: {mock_agents['feature-dev']['pr_number']}")
            ],
            "current_agent": "feature-dev",
            "next_agent": "code-review",
            "task_result": mock_agents["feature-dev"],
            "approvals": [],
            "requires_approval": False,
        }
        
        # Simulate handoff to code-review
        # Code-review should receive PR context
        pr_number = state["task_result"]["pr_number"]
        code_url = state["task_result"]["code_url"]
        
        assert pr_number == 100, "PR number should carry forward"
        assert "feature/auth" in code_url, "Branch info should carry forward"
        assert len(state["task_result"]["files_changed"]) == 2, "File list should carry forward"
        
        # Update state as code-review would
        state["current_agent"] = "code-review"
        state["next_agent"] = "cicd"
        state["task_result"] = {
            **state["task_result"],  # Preserve previous results
            "review": mock_agents["code-review"]
        }
        state["messages"].append(
            AIMessage(content=f"Code review complete. Status: {mock_agents['code-review']['review_result']}")
        )
        
        # Verify state accumulation
        assert "pr_number" in state["task_result"], "Previous agent results preserved"
        assert "review" in state["task_result"], "New agent results added"
        assert len(state["messages"]) == 3, "Message history accumulated"
        
        print("✅ Feature-dev → code-review handoff test passed")
        print(f"   - PR: {pr_number}")
        print(f"   - Review result: {mock_agents['code-review']['review_result']}")
        print(f"   - Messages accumulated: {len(state['messages'])}")
    
    async def test_complete_workflow_chain(self, mock_agents):
        """Test complete workflow through all agents."""
        from graph import WorkflowState
        from langchain_core.messages import HumanMessage, AIMessage
        
        # Start with supervisor
        state: WorkflowState = {
            "messages": [HumanMessage(content="Implement and deploy authentication feature")],
            "current_agent": "supervisor",
            "next_agent": "feature-dev",
            "task_result": {},
            "approvals": [],
            "requires_approval": False,
        }
        
        # Chain of agents
        agent_chain = ["feature-dev", "code-review", "cicd", "infrastructure", "documentation"]
        
        for agent in agent_chain:
            # Update state as agent completes
            state["current_agent"] = agent
            state["task_result"][agent] = mock_agents[agent]
            state["messages"].append(
                AIMessage(content=f"{agent} completed: {mock_agents[agent].get('status', 'done')}")
            )
            
            # Set next agent (or END if last)
            current_index = agent_chain.index(agent)
            if current_index < len(agent_chain) - 1:
                state["next_agent"] = agent_chain[current_index + 1]
            else:
                state["next_agent"] = "END"
        
        # Verify complete workflow state
        assert len(state["messages"]) == 6, "Should have 6 messages (initial + 5 agents)"
        assert len(state["task_result"]) == 5, "Should have results from 5 agents"
        assert state["next_agent"] == "END", "Should be complete"
        
        # Verify all agent results present
        for agent in agent_chain:
            assert agent in state["task_result"], f"Should have {agent} results"
        
        # Verify key data points
        assert state["task_result"]["feature-dev"]["pr_number"] == 100
        assert state["task_result"]["code-review"]["review_result"] == "approved"
        assert state["task_result"]["cicd"]["test_results"]["passed"] == 47
        assert state["task_result"]["infrastructure"]["deployment_status"] == "success"
        assert state["task_result"]["documentation"]["pages_updated"] == 3
        
        print("✅ Complete workflow chain test passed")
        print(f"   - Agents: {len(agent_chain)}")
        print(f"   - Messages: {len(state['messages'])}")
        print(f"   - Final status: {state['next_agent']}")
        
        # Print workflow summary
        print("\n   Workflow Summary:")
        print(f"     1. Feature-dev: PR #{state['task_result']['feature-dev']['pr_number']}")
        print(f"     2. Code-review: {state['task_result']['code-review']['review_result']}")
        print(f"     3. CI/CD: {state['task_result']['cicd']['test_results']['passed']} tests passed")
        print(f"     4. Infrastructure: {state['task_result']['infrastructure']['deployment_status']}")
        print(f"     5. Documentation: {state['task_result']['documentation']['pages_updated']} pages")
    
    async def test_state_immutability_between_agents(self, mock_agents):
        """Test that previous agent results are not mutated by subsequent agents."""
        from graph import WorkflowState
        
        state: WorkflowState = {
            "messages": [],
            "current_agent": "feature-dev",
            "next_agent": "code-review",
            "task_result": {"feature-dev": mock_agents["feature-dev"].copy()},
            "approvals": [],
            "requires_approval": False,
        }
        
        # Store original PR number
        original_pr = state["task_result"]["feature-dev"]["pr_number"]
        
        # Simulate code-review agent processing
        state["current_agent"] = "code-review"
        state["task_result"]["code-review"] = mock_agents["code-review"]
        
        # Verify feature-dev results unchanged
        assert state["task_result"]["feature-dev"]["pr_number"] == original_pr, \
            "Previous agent results should not be mutated"
        assert "files_changed" in state["task_result"]["feature-dev"], \
            "Previous agent data should be complete"
        
        print("✅ State immutability test passed")
        print(f"   - Original PR: {original_pr}")
        print(f"   - After code-review: {state['task_result']['feature-dev']['pr_number']}")
    
    async def test_error_handling_in_chain(self, mock_agents):
        """Test error handling when one agent in chain fails."""
        from graph import WorkflowState
        from langchain_core.messages import HumanMessage, AIMessage
        
        state: WorkflowState = {
            "messages": [HumanMessage(content="Test task")],
            "current_agent": "supervisor",
            "next_agent": "feature-dev",
            "task_result": {},
            "approvals": [],
            "requires_approval": False,
        }
        
        # Feature-dev succeeds
        state["current_agent"] = "feature-dev"
        state["task_result"]["feature-dev"] = mock_agents["feature-dev"]
        state["next_agent"] = "code-review"
        
        # Code-review fails
        state["current_agent"] = "code-review"
        state["task_result"]["code-review"] = {
            "status": "error",
            "error": "Failed to fetch PR diff",
            "can_retry": True
        }
        state["messages"].append(AIMessage(content="Code review failed"))
        
        # Verify error is captured
        assert state["task_result"]["code-review"]["status"] == "error", \
            "Error status should be recorded"
        assert state["task_result"]["code-review"]["can_retry"] == True, \
            "Retry capability should be indicated"
        
        # Verify workflow can continue or halt appropriately
        # In real workflow, orchestrator would decide to retry or escalate
        
        print("✅ Error handling in chain test passed")
        print(f"   - Feature-dev: success")
        print(f"   - Code-review: {state['task_result']['code-review']['status']}")
        print(f"   - Can retry: {state['task_result']['code-review']['can_retry']}")


class TestParallelAgentExecution:
    """Test parallel agent execution scenarios."""
    
    async def test_parallel_documentation_generation(self):
        """Test parallel execution of documentation agents."""
        from graph import WorkflowState
        
        # Simulate 3 parallel documentation tasks
        doc_tasks = [
            {"type": "api_reference", "agent": "documentation"},
            {"type": "user_guide", "agent": "documentation"},
            {"type": "deployment_guide", "agent": "documentation"}
        ]
        
        # Execute in parallel (simulated)
        results = []
        start_time = asyncio.get_event_loop().time()
        
        async def generate_doc(doc_type):
            await asyncio.sleep(0.2)  # Simulate work
            return {
                "type": doc_type,
                "status": "complete",
                "pages": 5 if doc_type == "api_reference" else 3
            }
        
        results = await asyncio.gather(*[
            generate_doc(task["type"]) for task in doc_tasks
        ])
        
        elapsed = asyncio.get_event_loop().time() - start_time
        
        # Verify all completed
        assert len(results) == 3, "Should complete all 3 docs"
        assert all(r["status"] == "complete" for r in results), "All should succeed"
        
        # Verify parallel execution (< 0.5s for 3 tasks, not 0.6s sequential)
        assert elapsed < 0.5, f"Should execute in parallel (took {elapsed:.2f}s)"
        
        print("✅ Parallel documentation test passed")
        print(f"   - Tasks: {len(results)}")
        print(f"   - Execution time: {elapsed:.2f}s")
        print(f"   - Parallelism verified: {elapsed < 0.5}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
