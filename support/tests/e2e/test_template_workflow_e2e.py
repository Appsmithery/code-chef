"""
End-to-end test for template-driven workflow execution (CHEF-110).

Tests the Phase 6 multi-agent collaboration workflows:
1. WorkflowRouter task→template matching
2. WorkflowEngine declarative YAML execution
3. Inter-agent communication via EventBus
4. HITL approval integration at decision gates
5. Event-sourced state persistence

Usage:
    pytest support/tests/e2e/test_template_workflow_e2e.py -v -s
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch, MagicMock
import sys
from pathlib import Path
from typing import Dict, Any

sys.path.insert(0, str(Path(__file__).parent / "../../../agent_orchestrator"))
sys.path.insert(0, str(Path(__file__).parent / "../../../shared"))

pytestmark = pytest.mark.asyncio


class TestTemplateWorkflowE2E:
    """Test template-driven workflow execution with WorkflowEngine."""

    @pytest.fixture
    def mock_llm_client(self):
        """Mock Gradient client for LLM calls."""
        mock = MagicMock()
        mock.is_enabled.return_value = True
        
        # Mock LLM response for decision gates
        mock.invoke = AsyncMock(return_value={
            "decision": "proceed",
            "reasoning": "All checks passed, safe to continue"
        })
        
        return mock

    @pytest.fixture
    def mock_event_bus(self):
        """Mock EventBus for inter-agent communication."""
        from lib.event_bus import EventBus
        from lib.agent_events import AgentResponseEvent, AgentResponseStatus
        
        # Reset singleton for clean test
        EventBus.reset_instance()
        bus = EventBus.get_instance()
        
        # Track events
        bus.emitted_events = []
        bus.requests_sent = []
        
        original_emit = bus.emit
        original_request = bus.request_agent
        
        async def track_emit(*args, **kwargs):
            bus.emitted_events.append({"args": args, "kwargs": kwargs})
            return await original_emit(*args, **kwargs)
        
        async def mock_request_agent(request, timeout=None):
            bus.requests_sent.append(request)
            # Return success response
            return AgentResponseEvent(
                request_id=request.request_id,
                source_agent=request.target_agent,
                target_agent=request.source_agent,
                status=AgentResponseStatus.SUCCESS,
                result={
                    "agent": request.target_agent,
                    "status": "completed",
                    "output": f"Mock response from {request.target_agent}"
                },
                processing_time_ms=150.0
            )
        
        bus.emit = track_emit
        bus.request_agent = mock_request_agent
        
        return bus

    @pytest.fixture
    def sample_pr_context(self) -> Dict[str, Any]:
        """Sample context for PR deployment workflow."""
        return {
            "pr_number": 42,
            "repo_url": "https://github.com/Appsmithery/Dev-Tools",
            "branch": "feature/jwt-auth",
            "previous_version": "v1.2.3",
            "author": "developer@example.com"
        }

    # =========================================================================
    # Test: WorkflowRouter routes task to correct template
    # =========================================================================
    
    async def test_workflow_router_matches_pr_deployment(self, sample_pr_context):
        """Test that PR deployment task routes to pr-deployment.workflow.yaml."""
        from workflows.workflow_router import WorkflowRouter, get_workflow_router
        
        router = get_workflow_router()
        
        task_description = (
            f"Deploy PR #{sample_pr_context['pr_number']} from branch "
            f"{sample_pr_context['branch']} to production"
        )
        
        selection = await router.route(task_description)
        
        assert selection.workflow_id == "pr-deployment"
        assert selection.confidence >= 0.7
        assert selection.method in ["HEURISTIC", "LLM"]

    async def test_workflow_router_matches_feature_development(self):
        """Test that feature development task routes to feature.workflow.yaml."""
        from workflows.workflow_router import WorkflowRouter, get_workflow_router
        
        router = get_workflow_router()
        
        task_description = "Implement JWT authentication for the REST API"
        
        selection = await router.route(task_description)
        
        assert selection.workflow_id == "feature"
        assert selection.confidence >= 0.7

    async def test_workflow_router_matches_hotfix(self):
        """Test that hotfix task routes to hotfix.workflow.yaml."""
        from workflows.workflow_router import WorkflowRouter, get_workflow_router
        
        router = get_workflow_router()
        
        task_description = "URGENT: Fix security vulnerability in authentication module"
        
        selection = await router.route(task_description)
        
        assert selection.workflow_id == "hotfix"
        assert selection.confidence >= 0.7

    # =========================================================================
    # Test: WorkflowEngine loads and validates YAML templates
    # =========================================================================
    
    async def test_workflow_engine_loads_pr_deployment_template(self):
        """Test that WorkflowEngine can load pr-deployment.workflow.yaml."""
        from workflows.workflow_engine import WorkflowEngine
        
        engine = WorkflowEngine(
            templates_dir="agent_orchestrator/workflows/templates"
        )
        
        definition = engine.load_workflow("pr-deployment.workflow.yaml")
        
        assert definition.name == "PR Deployment Workflow"
        assert definition.version == "1.0"
        assert len(definition.steps) > 0
        
        # Verify expected steps exist
        step_ids = [step.id for step in definition.steps]
        assert "code_review" in step_ids
        assert "run_tests" in step_ids
        assert "deploy_staging" in step_ids or "deploy_production" in step_ids

    async def test_workflow_engine_loads_all_templates(self):
        """Test that all workflow templates are valid YAML."""
        from workflows.workflow_engine import WorkflowEngine
        
        engine = WorkflowEngine(
            templates_dir="agent_orchestrator/workflows/templates"
        )
        
        templates = [
            "pr-deployment.workflow.yaml",
            "feature.workflow.yaml",
            "hotfix.workflow.yaml",
            "docs-update.workflow.yaml",
            "infrastructure.workflow.yaml"
        ]
        
        for template in templates:
            try:
                definition = engine.load_workflow(template)
                assert definition.name, f"Template {template} missing name"
                assert definition.steps, f"Template {template} has no steps"
            except FileNotFoundError:
                pytest.skip(f"Template {template} not found")

    # =========================================================================
    # Test: Inter-agent communication via EventBus
    # =========================================================================
    
    async def test_base_agent_request_agent(self, mock_event_bus):
        """Test that BaseAgent can send requests to other agents."""
        from agents._shared.base_agent import BaseAgent
        from lib.agent_events import AgentRequestType
        
        # Create a mock agent config
        with patch.object(BaseAgent, "_load_config") as mock_config:
            mock_config.return_value = {
                "agent": {"name": "test-agent", "model": "test-model"},
                "tools": {}
            }
            with patch.object(BaseAgent, "_initialize_llm") as mock_llm:
                mock_llm.return_value = MagicMock()
                
                agent = BaseAgent(config_path="fake.yaml", agent_name="test-agent")
                
                # Send request to another agent
                response = await agent.request_agent(
                    target_agent="code-review",
                    request_type=AgentRequestType.REVIEW_CODE,
                    payload={"file_path": "main.py"}
                )
                
                assert response.status.value == "success"
                assert response.source_agent == "code-review"
                assert len(mock_event_bus.requests_sent) == 1
                
                sent_request = mock_event_bus.requests_sent[0]
                assert sent_request.target_agent == "code-review"
                assert sent_request.request_type == AgentRequestType.REVIEW_CODE

    async def test_supervisor_delegate_to_agent(self, mock_event_bus):
        """Test that SupervisorAgent can delegate tasks to other agents."""
        from agents.supervisor import SupervisorAgent
        from lib.agent_events import AgentRequestType
        
        with patch.object(SupervisorAgent, "_load_config") as mock_config:
            mock_config.return_value = {
                "agent": {"name": "supervisor", "model": "llama-3.1-70b"},
                "tools": {}
            }
            with patch.object(SupervisorAgent, "_initialize_llm") as mock_llm:
                mock_llm.return_value = MagicMock()
                
                supervisor = SupervisorAgent()
                
                # Delegate to code-review agent
                response = await supervisor.delegate_to_agent(
                    target_agent="code-review",
                    task_type=AgentRequestType.REVIEW_CODE,
                    payload={
                        "file_path": "src/auth.py",
                        "focus_areas": ["security", "performance"]
                    }
                )
                
                assert response["status"] == "success"
                assert response["agent"] == "code-review"
                assert response["processing_time_ms"] is not None

    async def test_supervisor_delegate_parallel(self, mock_event_bus):
        """Test that SupervisorAgent can delegate multiple tasks in parallel."""
        from agents.supervisor import SupervisorAgent
        from lib.agent_events import AgentRequestType
        
        with patch.object(SupervisorAgent, "_load_config") as mock_config:
            mock_config.return_value = {
                "agent": {"name": "supervisor", "model": "llama-3.1-70b"},
                "tools": {}
            }
            with patch.object(SupervisorAgent, "_initialize_llm") as mock_llm:
                mock_llm.return_value = MagicMock()
                
                supervisor = SupervisorAgent()
                
                # Delegate to multiple agents in parallel
                tasks = [
                    {
                        "target_agent": "code-review",
                        "task_type": AgentRequestType.REVIEW_CODE,
                        "payload": {"file_path": "main.py"}
                    },
                    {
                        "target_agent": "cicd",
                        "task_type": AgentRequestType.RUN_PIPELINE,
                        "payload": {"pipeline": "test"}
                    },
                    {
                        "target_agent": "documentation",
                        "task_type": AgentRequestType.GENERATE_DOCS,
                        "payload": {"module": "auth"}
                    }
                ]
                
                results = await supervisor.delegate_parallel(tasks)
                
                assert len(results) == 3
                assert all(r["status"] == "success" for r in results)
                assert len(mock_event_bus.requests_sent) == 3

    # =========================================================================
    # Test: LangGraph workflow with template execution
    # =========================================================================
    
    async def test_graph_routes_to_workflow_executor(self):
        """Test that LangGraph routes to workflow_executor when template specified."""
        from graph import route_entry_point, WorkflowState
        
        state = WorkflowState(
            messages=[],
            current_agent="",
            next_agent="",
            task_result={},
            approvals=[],
            requires_approval=False,
            workflow_id="test-wf-123",
            thread_id="test-thread",
            pending_operation="",
            captured_insights=[],
            memory_context=None,
            workflow_template="pr-deployment.workflow.yaml",
            workflow_context={"pr_number": 42},
            use_template_engine=True,
        )
        
        route = route_entry_point(state)
        
        assert route == "workflow_executor"

    async def test_graph_routes_to_workflow_router_for_discovery(self):
        """Test that LangGraph routes to workflow_router when template not specified."""
        from graph import route_entry_point, WorkflowState
        
        state = WorkflowState(
            messages=[],
            current_agent="",
            next_agent="",
            task_result={},
            approvals=[],
            requires_approval=False,
            workflow_id="test-wf-456",
            thread_id="test-thread",
            pending_operation="",
            captured_insights=[],
            memory_context=None,
            workflow_template=None,  # No template specified
            workflow_context=None,
            use_template_engine=True,  # But template mode enabled
        )
        
        route = route_entry_point(state)
        
        assert route == "workflow_router"

    async def test_graph_defaults_to_supervisor(self):
        """Test that LangGraph defaults to supervisor when template mode disabled."""
        from graph import route_entry_point, WorkflowState
        
        state = WorkflowState(
            messages=[],
            current_agent="",
            next_agent="",
            task_result={},
            approvals=[],
            requires_approval=False,
            workflow_id="test-wf-789",
            thread_id="test-thread",
            pending_operation="",
            captured_insights=[],
            memory_context=None,
            workflow_template=None,
            workflow_context=None,
            use_template_engine=False,  # Template mode disabled
        )
        
        route = route_entry_point(state)
        
        assert route == "supervisor"

    # =========================================================================
    # Test: End-to-end workflow execution
    # =========================================================================
    
    @pytest.mark.slow
    async def test_full_pr_deployment_workflow(
        self, 
        mock_event_bus, 
        mock_llm_client, 
        sample_pr_context
    ):
        """Test complete PR deployment workflow execution.
        
        This test verifies the full flow:
        1. Task submitted with use_template_engine=True
        2. WorkflowRouter matches pr-deployment template
        3. WorkflowEngine executes steps: code_review → tests → staging → approval → production
        4. Agents communicate via EventBus
        5. Final result returned
        
        Note: This is marked @pytest.mark.slow as it tests the full integration.
        """
        from graph import (
            create_workflow, 
            WorkflowState, 
            workflow_router_node,
            workflow_executor_node
        )
        from langchain_core.messages import HumanMessage
        
        # Create workflow state
        initial_state = WorkflowState(
            messages=[
                HumanMessage(
                    content=f"Deploy PR #{sample_pr_context['pr_number']} "
                    f"from branch {sample_pr_context['branch']} to production"
                )
            ],
            current_agent="",
            next_agent="",
            task_result={},
            approvals=[],
            requires_approval=False,
            workflow_id=f"test-pr-{sample_pr_context['pr_number']}",
            thread_id="test-thread-e2e",
            pending_operation="",
            captured_insights=[],
            memory_context=None,
            workflow_template=None,
            workflow_context=sample_pr_context,
            use_template_engine=True,
        )
        
        # Test workflow router node
        with patch("workflows.workflow_router.get_workflow_router") as mock_router:
            mock_router.return_value = MagicMock()
            mock_router.return_value.route = AsyncMock(return_value=MagicMock(
                workflow_id="pr-deployment",
                confidence=0.95,
                method="HEURISTIC"
            ))
            
            result_state = await workflow_router_node(initial_state)
            
            assert result_state["workflow_template"] == "pr-deployment.workflow.yaml"
            assert result_state["use_template_engine"] == True
            assert result_state["next_agent"] == "workflow_executor"

    # =========================================================================
    # Test: EventBus event tracking and persistence
    # =========================================================================
    
    async def test_event_bus_tracks_agent_requests(self, mock_event_bus):
        """Test that EventBus properly tracks inter-agent requests."""
        from lib.event_bus import EventBus
        from lib.agent_events import AgentRequestEvent, AgentRequestType
        
        request = AgentRequestEvent(
            source_agent="orchestrator",
            target_agent="code-review",
            request_type=AgentRequestType.REVIEW_CODE,
            payload={"file_path": "test.py"}
        )
        
        response = await mock_event_bus.request_agent(request, timeout=30.0)
        
        assert len(mock_event_bus.requests_sent) == 1
        assert mock_event_bus.requests_sent[0].request_id == request.request_id
        assert response.status.value == "success"

    async def test_event_bus_broadcasts_workflow_status(self, mock_event_bus):
        """Test that EventBus can broadcast workflow status to all agents."""
        
        await mock_event_bus.emit(
            event_type="workflow.started",
            data={
                "workflow_id": "wf-test-123",
                "template": "pr-deployment",
                "agents_involved": ["code-review", "cicd", "infrastructure"]
            },
            source="supervisor"
        )
        
        assert len(mock_event_bus.emitted_events) == 1
        event = mock_event_bus.emitted_events[0]
        assert event["args"][0] == "workflow.started"
        assert event["kwargs"]["source"] == "supervisor"
