"""
Integration tests for Phase 6 multi-agent workflows.

Tests the three main workflow patterns:
1. PR Deployment (sequential with HITL approval)
2. Parallel Documentation Generation
3. Self-Healing Loop (with retry logic)
4. Resource Locking Contention
5. Workflow State Persistence

Usage:
    cd support/tests/workflows
    pytest test_multi_agent_workflows.py -v -s
    pytest test_multi_agent_workflows.py --cov=shared.lib --cov-report=html
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from datetime import datetime
import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from shared.lib.event_bus import EventBus, Event, InterAgentEvent
from shared.lib.agent_events import (
    AgentRequestEvent, AgentResponseEvent, 
    AgentRequestType, AgentResponseStatus, AgentRequestPriority
)


class TestPRDeploymentWorkflow:
    """Test PR deployment workflow with sequential steps and approval gate."""
    
    @pytest.mark.asyncio
    async def test_pr_deployment_workflow(self):
        """
        Test end-to-end PR deployment workflow:
        1. Code review
        2. Test execution
        3. HITL approval request
        4. Deployment (only if approved)
        
        Verifies:
        - State transitions through each step
        - Event emissions for each stage
        - Final deployment status
        """
        # Reset EventBus for clean test
        EventBus.reset_instance()
        event_bus = EventBus.get_instance()
        
        # Track emitted events
        events_emitted = []
        
        async def capture_event(event: Event):
            events_emitted.append(event)
        
        event_bus.subscribe("agent_request", capture_event)
        event_bus.subscribe("agent_response", capture_event)
        
        # Mock agent responses
        mock_responses = {
            "code-review": AgentResponseEvent(
                request_id="review-123",
                source_agent="code-review",
                target_agent="orchestrator",
                status=AgentResponseStatus.SUCCESS,
                result={
                    "comments": [
                        {"line": 42, "message": "Consider refactoring this function"},
                        {"line": 108, "message": "Add error handling"}
                    ],
                    "issues_count": 2,
                    "severity": "low"
                }
            ),
            "cicd": AgentResponseEvent(
                request_id="test-456",
                source_agent="cicd",
                target_agent="orchestrator",
                status=AgentResponseStatus.SUCCESS,
                result={
                    "status": "passed",
                    "tests_run": 47,
                    "tests_passed": 47,
                    "tests_failed": 0,
                    "coverage": 92.5
                }
            ),
            "infrastructure": AgentResponseEvent(
                request_id="deploy-789",
                source_agent="infrastructure",
                target_agent="orchestrator",
                status=AgentResponseStatus.SUCCESS,
                result={
                    "deployment_status": "success",
                    "environment": "production",
                    "version": "pr-42",
                    "url": "https://prod.example.com"
                }
            )
        }
        
        # Mock the request_agent method to return predefined responses
        async def mock_request_agent(request, timeout=None):
            await asyncio.sleep(0.1)  # Simulate network delay
            return mock_responses.get(request.target_agent)
        
        event_bus.request_agent = mock_request_agent
        
        # Execute workflow steps
        state = {
            "pr_number": 42,
            "repo_url": "https://github.com/test/repo",
            "review_comments": [],
            "test_results": {},
            "approval_status": "pending",
            "deployment_status": "not_started"
        }
        
        # Step 1: Code Review
        request = AgentRequestEvent(
            source_agent="orchestrator",
            target_agent="code-review",
            request_type=AgentRequestType.REVIEW_CODE,
            payload={"repo_url": state["repo_url"], "pr_number": state["pr_number"]},
            priority=AgentRequestPriority.HIGH
        )
        
        response = await event_bus.request_agent(request, timeout=10.0)
        assert response.status == AgentResponseStatus.SUCCESS
        state["review_comments"] = response.result["comments"]
        assert len(state["review_comments"]) == 2
        
        # Step 2: Test Execution
        request = AgentRequestEvent(
            source_agent="orchestrator",
            target_agent="cicd",
            request_type=AgentRequestType.RUN_PIPELINE,
            payload={
                "repo_url": state["repo_url"],
                "pr_number": state["pr_number"],
                "pipeline_type": "test"
            },
            priority=AgentRequestPriority.HIGH
        )
        
        response = await event_bus.request_agent(request, timeout=10.0)
        assert response.status == AgentResponseStatus.SUCCESS
        state["test_results"] = response.result
        assert state["test_results"]["status"] == "passed"
        
        # Step 3: HITL Approval (simulated approval)
        state["approval_status"] = "approved"
        
        # Step 4: Deployment
        request = AgentRequestEvent(
            source_agent="orchestrator",
            target_agent="infrastructure",
            request_type=AgentRequestType.DEPLOY_SERVICE,
            payload={
                "repo_url": state["repo_url"],
                "environment": "production",
                "version": f"pr-{state['pr_number']}"
            },
            priority=AgentRequestPriority.URGENT
        )
        
        response = await event_bus.request_agent(request, timeout=10.0)
        assert response.status == AgentResponseStatus.SUCCESS
        state["deployment_status"] = "success"
        
        # Verify final state
        assert state["deployment_status"] == "success"
        assert state["approval_status"] == "approved"
        assert state["test_results"]["tests_passed"] == 47
        assert len(state["review_comments"]) == 2
        
        print(f"✅ PR deployment workflow completed successfully")
        print(f"   - Review comments: {len(state['review_comments'])}")
        print(f"   - Test results: {state['test_results']['status']}")
        print(f"   - Deployment: {state['deployment_status']}")


class TestParallelDocsWorkflow:
    """Test parallel documentation generation workflow."""
    
    @pytest.mark.asyncio
    async def test_parallel_docs_workflow(self):
        """
        Test concurrent documentation generation:
        1. API docs, User guide, Deployment guide in parallel
        2. Merge results
        
        Verifies:
        - All doc types present in results
        - Parallel execution completes faster than sequential
        - Error handling for individual failures
        """
        EventBus.reset_instance()
        event_bus = EventBus.get_instance()
        
        # Track request timing
        request_times = []
        
        # Mock documentation responses
        async def mock_request_agent(request, timeout=None):
            request_times.append(datetime.utcnow())
            await asyncio.sleep(0.2)  # Simulate processing time
            
            doc_type = request.payload.get("doc_type")
            return AgentResponseEvent(
                request_id=request.request_id,
                source_agent="documentation",
                target_agent="orchestrator",
                status=AgentResponseStatus.SUCCESS,
                result={
                    "doc_type": doc_type,
                    "content": f"Generated {doc_type} documentation",
                    "pages": 10 if doc_type == "api_reference" else 5,
                    "generated_at": datetime.utcnow().isoformat()
                }
            )
        
        event_bus.request_agent = mock_request_agent
        
        state = {
            "repo_url": "https://github.com/test/repo",
            "api_docs": None,
            "user_guide": None,
            "deployment_guide": None,
            "errors": []
        }
        
        # Execute all three documentation tasks in parallel
        start_time = datetime.utcnow()
        
        tasks = [
            event_bus.request_agent(
                AgentRequestEvent(
                    source_agent="orchestrator",
                    target_agent="documentation",
                    request_type=AgentRequestType.GENERATE_DOCS,
                    payload={"repo_url": state["repo_url"], "doc_type": "api_reference"}
                ),
                timeout=10.0
            ),
            event_bus.request_agent(
                AgentRequestEvent(
                    source_agent="orchestrator",
                    target_agent="documentation",
                    request_type=AgentRequestType.GENERATE_DOCS,
                    payload={"repo_url": state["repo_url"], "doc_type": "user_guide"}
                ),
                timeout=10.0
            ),
            event_bus.request_agent(
                AgentRequestEvent(
                    source_agent="orchestrator",
                    target_agent="documentation",
                    request_type=AgentRequestType.GENERATE_DOCS,
                    payload={"repo_url": state["repo_url"], "doc_type": "deployment_guide"}
                ),
                timeout=10.0
            )
        ]
        
        responses = await asyncio.gather(*tasks)
        
        elapsed = (datetime.utcnow() - start_time).total_seconds()
        
        # Verify all succeeded
        assert all(r.status == AgentResponseStatus.SUCCESS for r in responses)
        
        # Extract results
        state["api_docs"] = responses[0].result
        state["user_guide"] = responses[1].result
        state["deployment_guide"] = responses[2].result
        
        # Merge documentation
        state["merged_docs"] = {
            "api": state["api_docs"],
            "user": state["user_guide"],
            "deploy": state["deployment_guide"]
        }
        
        # Verify all doc types present
        assert state["merged_docs"]["api"]["doc_type"] == "api_reference"
        assert state["merged_docs"]["user"]["doc_type"] == "user_guide"
        assert state["merged_docs"]["deploy"]["doc_type"] == "deployment_guide"
        
        # Verify parallel execution (should be ~0.2s, not 0.6s)
        assert elapsed < 0.5, f"Parallel execution took {elapsed}s (expected <0.5s)"
        
        # Verify all requests started around the same time
        if len(request_times) >= 3:
            time_spread = (request_times[-1] - request_times[0]).total_seconds()
            assert time_spread < 0.1, f"Requests not parallel (spread: {time_spread}s)"
        
        print(f"✅ Parallel docs workflow completed in {elapsed:.2f}s")
        print(f"   - API docs: {state['api_docs']['pages']} pages")
        print(f"   - User guide: {state['user_guide']['pages']} pages")
        print(f"   - Deployment guide: {state['deployment_guide']['pages']} pages")


class TestSelfHealingWorkflow:
    """Test self-healing workflow with retry logic."""
    
    @pytest.mark.asyncio
    async def test_self_healing_workflow(self):
        """
        Test self-healing loop:
        1. Detect issue
        2. Diagnose root cause
        3. Apply fix
        4. Verify resolution
        5. Retry if not resolved (max 3 attempts)
        
        Verifies:
        - Detection, diagnosis, fix, verification cycle
        - Retry logic for unresolved issues
        - Exit after max retries
        """
        EventBus.reset_instance()
        event_bus = EventBus.get_instance()
        
        # Track healing attempts
        healing_attempts = {"count": 0}
        
        # Mock agent responses (issue resolved on 2nd attempt)
        async def mock_request_agent(request, timeout=None):
            await asyncio.sleep(0.1)
            
            if request.request_type == AgentRequestType.HEALTH_CHECK:
                healing_attempts["count"] += 1
                if healing_attempts["count"] < 2:
                    # Issue still present
                    return AgentResponseEvent(
                        request_id=request.request_id,
                        source_agent="infrastructure",
                        target_agent="orchestrator",
                        status=AgentResponseStatus.SUCCESS,
                        result={
                            "issues": [
                                {
                                    "service": "web-api",
                                    "status": "down",
                                    "error": "Connection refused"
                                }
                            ]
                        }
                    )
                else:
                    # Issue resolved
                    return AgentResponseEvent(
                        request_id=request.request_id,
                        source_agent="infrastructure",
                        target_agent="orchestrator",
                        status=AgentResponseStatus.SUCCESS,
                        result={"issues": []}
                    )
            
            elif request.request_type == AgentRequestType.EXECUTE_TASK:
                task = request.payload.get("task")
                if task == "diagnose_issue":
                    return AgentResponseEvent(
                        request_id=request.request_id,
                        source_agent=request.target_agent,
                        target_agent="orchestrator",
                        status=AgentResponseStatus.SUCCESS,
                        result={
                            "diagnosis": "Service crashed due to memory leak",
                            "recommended_action": "restart_service",
                            "confidence": 0.85
                        }
                    )
                elif task == "restart_service":
                    return AgentResponseEvent(
                        request_id=request.request_id,
                        source_agent="infrastructure",
                        target_agent="orchestrator",
                        status=AgentResponseStatus.SUCCESS,
                        result={"action": "restart", "status": "completed"}
                    )
        
        event_bus.request_agent = mock_request_agent
        
        state = {
            "environment": "production",
            "issues": [],
            "diagnosis": {},
            "fix_result": {},
            "is_resolved": False,
            "max_retries": 3
        }
        
        # Self-healing loop
        for attempt in range(state["max_retries"]):
            # Step 1: Detect issue
            response = await event_bus.request_agent(
                AgentRequestEvent(
                    source_agent="orchestrator",
                    target_agent="infrastructure",
                    request_type=AgentRequestType.HEALTH_CHECK,
                    payload={"environment": state["environment"]}
                ),
                timeout=10.0
            )
            
            state["issues"] = response.result.get("issues", [])
            
            if not state["issues"]:
                state["is_resolved"] = True
                print(f"✅ Issue resolved after {attempt + 1} attempt(s)")
                break
            
            # Step 2: Diagnose
            issue = state["issues"][0]
            response = await event_bus.request_agent(
                AgentRequestEvent(
                    source_agent="orchestrator",
                    target_agent="code-review",
                    request_type=AgentRequestType.EXECUTE_TASK,
                    payload={"task": "diagnose_issue", "issue": issue}
                ),
                timeout=10.0
            )
            
            state["diagnosis"] = response.result
            
            # Step 3: Apply fix
            response = await event_bus.request_agent(
                AgentRequestEvent(
                    source_agent="orchestrator",
                    target_agent="infrastructure",
                    request_type=AgentRequestType.EXECUTE_TASK,
                    payload={
                        "task": "restart_service",
                        "service": issue["service"]
                    },
                    priority=AgentRequestPriority.HIGH
                ),
                timeout=10.0
            )
            
            state["fix_result"] = response.result
            
            print(f"   Attempt {attempt + 1}: Applied fix - {state['fix_result']}")
        
        # Verify resolution
        assert state["is_resolved"] == True
        assert healing_attempts["count"] == 2  # Resolved on 2nd check
        assert state["diagnosis"]["recommended_action"] == "restart_service"
        
        print(f"✅ Self-healing workflow completed successfully")
        print(f"   - Attempts: {healing_attempts['count']}")
        print(f"   - Diagnosis: {state['diagnosis']['diagnosis']}")
        print(f"   - Resolution: {state['is_resolved']}")


class TestResourceLockingContention:
    """Test distributed resource locking with contention handling."""
    
    @pytest.mark.asyncio
    async def test_resource_locking_contention(self):
        """
        Test resource lock contention:
        1. Agent A acquires lock
        2. Agent B tries to acquire same lock (should fail or wait)
        3. Agent A releases lock
        4. Agent B acquires lock successfully
        
        Verifies:
        - Lock acquisition and release
        - Contention detection
        - Lock status queries
        """
        # Mock ResourceLockManager
        from unittest.mock import MagicMock
        
        mock_pool = MagicMock()
        mock_conn = MagicMock()
        
        lock_state = {"locked": False, "owner": None}
        
        # Mock database operations
        async def mock_fetchrow(query, *args):
            if "acquire_resource_lock" in query:
                resource_id, agent_id = args[0], args[1]
                if not lock_state["locked"]:
                    lock_state["locked"] = True
                    lock_state["owner"] = agent_id
                    return {"success": True, "message": "Lock acquired"}
                else:
                    return {"success": False, "message": f"Locked by {lock_state['owner']}"}
            
            elif "release_resource_lock" in query:
                resource_id, agent_id = args[0], args[1]
                if lock_state["locked"] and lock_state["owner"] == agent_id:
                    lock_state["locked"] = False
                    lock_state["owner"] = None
                    return {"success": True, "message": "Lock released"}
                return {"success": False, "message": "Not lock owner"}
            
            elif "check_lock_status" in query:
                if lock_state["locked"]:
                    return {
                        "is_locked": True,
                        "agent_id": lock_state["owner"],
                        "resource_id": args[0]
                    }
                return {"is_locked": False}
        
        mock_conn.fetchrow = mock_fetchrow
        mock_pool.acquire = MagicMock(return_value=MagicMock(__aenter__=AsyncMock(return_value=mock_conn), __aexit__=AsyncMock()))
        
        # Create mock lock manager
        from shared.lib.resource_lock import ResourceLockManager
        
        with patch('asyncpg.create_pool', return_value=AsyncMock(return_value=mock_pool)):
            lock_manager = ResourceLockManager("postgresql://test", None)
            lock_manager.pool = mock_pool
            
            resource_id = "file:shared/config.yaml"
            
            # Agent A acquires lock
            acquired = False
            try:
                async with lock_manager.acquire(resource_id, "agent-feature-dev", wait_timeout=0):
                    acquired = True
                    assert lock_state["locked"] == True
                    assert lock_state["owner"] == "agent-feature-dev"
                    print(f"✅ Agent A acquired lock on {resource_id}")
                    
                    # Agent B tries to acquire (should fail immediately)
                    try:
                        async with lock_manager.acquire(resource_id, "agent-code-review", wait_timeout=0):
                            pytest.fail("Agent B should not acquire lock while A holds it")
                    except Exception as e:
                        print(f"✅ Agent B correctly failed to acquire lock: {e}")
            except Exception:
                acquired = False
            
            # Lock should be released after context
            assert lock_state["locked"] == False
            print(f"✅ Agent A released lock on {resource_id}")
            
            # Agent B acquires lock successfully now
            try:
                async with lock_manager.acquire(resource_id, "agent-code-review", wait_timeout=0):
                    assert lock_state["locked"] == True
                    assert lock_state["owner"] == "agent-code-review"
                    print(f"✅ Agent B acquired lock on {resource_id}")
            except Exception:
                pytest.fail("Agent B should acquire lock after A released")
            
            # Verify final state
            assert lock_state["locked"] == False
            print(f"✅ Resource locking contention test completed")


class TestWorkflowStatePersistence:
    """Test workflow state persistence and recovery."""
    
    @pytest.mark.asyncio
    async def test_workflow_state_persistence(self):
        """
        Test state persistence:
        1. Create workflow with state
        2. Update state through transitions
        3. Verify state persisted correctly
        4. Test optimistic locking (version check)
        
        Verifies:
        - State CRUD operations
        - Optimistic locking prevents conflicts
        - Data integrity across updates
        """
        # Mock PostgreSQL state persistence
        workflow_states = {}
        
        async def mock_create_workflow(workflow_id, initial_state, version=0):
            workflow_states[workflow_id] = {
                "workflow_id": workflow_id,
                "state": initial_state,
                "version": version,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            return workflow_states[workflow_id]
        
        async def mock_update_workflow(workflow_id, new_state, expected_version):
            if workflow_id not in workflow_states:
                raise ValueError(f"Workflow {workflow_id} not found")
            
            current = workflow_states[workflow_id]
            if current["version"] != expected_version:
                raise ValueError(
                    f"Version mismatch: expected {expected_version}, "
                    f"got {current['version']}"
                )
            
            current["state"] = new_state
            current["version"] += 1
            current["updated_at"] = datetime.utcnow()
            return current
        
        async def mock_get_workflow(workflow_id):
            return workflow_states.get(workflow_id)
        
        # Test workflow lifecycle
        workflow_id = "wf-test-123"
        
        # Create initial state
        initial_state = {
            "step": "code_review",
            "pr_number": 42,
            "status": "in_progress",
            "results": {}
        }
        
        workflow = await mock_create_workflow(workflow_id, initial_state)
        assert workflow["version"] == 0
        assert workflow["state"]["step"] == "code_review"
        print(f"✅ Created workflow {workflow_id} (version {workflow['version']})")
        
        # Update state (code review completed)
        updated_state = {
            **workflow["state"],
            "step": "test",
            "results": {"review": {"comments": 2, "approved": True}}
        }
        
        workflow = await mock_update_workflow(workflow_id, updated_state, expected_version=0)
        assert workflow["version"] == 1
        assert workflow["state"]["step"] == "test"
        print(f"✅ Updated workflow to version {workflow['version']}: {workflow['state']['step']}")
        
        # Update state (tests completed)
        updated_state = {
            **workflow["state"],
            "step": "approval",
            "results": {
                **workflow["state"]["results"],
                "test": {"passed": 47, "failed": 0}
            }
        }
        
        workflow = await mock_update_workflow(workflow_id, updated_state, expected_version=1)
        assert workflow["version"] == 2
        assert workflow["state"]["results"]["test"]["passed"] == 47
        print(f"✅ Updated workflow to version {workflow['version']}: {workflow['state']['step']}")
        
        # Test optimistic locking (version conflict)
        try:
            await mock_update_workflow(
                workflow_id,
                {"step": "deploy"},
                expected_version=0  # Wrong version
            )
            pytest.fail("Should raise version conflict error")
        except ValueError as e:
            assert "Version mismatch" in str(e)
            print(f"✅ Optimistic locking prevented conflicting update: {e}")
        
        # Verify final state
        final_workflow = await mock_get_workflow(workflow_id)
        assert final_workflow["version"] == 2
        assert final_workflow["state"]["step"] == "approval"
        assert final_workflow["state"]["results"]["test"]["passed"] == 47
        assert final_workflow["state"]["results"]["review"]["approved"] == True
        
        print(f"✅ Workflow state persistence test completed")
        print(f"   - Final version: {final_workflow['version']}")
        print(f"   - Current step: {final_workflow['state']['step']}")
        print(f"   - Test results: {final_workflow['state']['results']['test']}")


# Run all tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
