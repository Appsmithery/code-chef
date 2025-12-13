#!/usr/bin/env python3
"""
End-to-End Workflow Testing Script

Tests all 5 workflow templates with real execution:
1. pr-deployment - Full PR review and deployment
2. hotfix - Emergency hotfix workflow
3. feature - Feature development lifecycle
4. docs-update - Documentation-only changes
5. infrastructure - IaC deployment with plan/apply

Usage:
    python support/scripts/workflow/test-workflows.py [workflow_name]

    If no workflow_name provided, tests all workflows
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import httpx

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))


class WorkflowTester:
    """Test harness for workflow execution."""

    def __init__(self, orchestrator_url: str = "http://localhost:8001"):
        self.orchestrator_url = orchestrator_url
        self.test_results: List[Dict[str, Any]] = []

    async def test_pr_deployment(self) -> Dict[str, Any]:
        """Test PR deployment workflow."""
        print("\n" + "=" * 80)
        print("Testing PR Deployment Workflow")
        print("=" * 80)

        context = {
            "pr_number": 123,
            "repo_url": "https://github.com/Appsmithery/Dev-Tools",
            "branch": "feature/test-workflow",
            "base_branch": "main",
            "author": "test-user",
            "title": "Test PR Deployment Workflow",
        }

        return await self._execute_and_validate(
            "pr-deployment.workflow.yaml",
            context,
            expected_steps=[
                "code_review",
                "run_tests",
                "deploy_staging",
                "approval_gate",
                # After approval: deploy_production, update_docs
            ],
            requires_approval=True,
        )

    async def test_hotfix(self) -> Dict[str, Any]:
        """Test hotfix workflow."""
        print("\n" + "=" * 80)
        print("Testing Hotfix Workflow")
        print("=" * 80)

        context = {
            "pr_number": 456,
            "repo_url": "https://github.com/Appsmithery/Dev-Tools",
            "branch": "hotfix/critical-fix",
            "base_branch": "main",
            "author": "devops-user",
            "title": "Critical Production Fix",
            "severity": "critical",
        }

        return await self._execute_and_validate(
            "hotfix.workflow.yaml",
            context,
            expected_steps=[
                "validate_hotfix",
                "emergency_review",
                "deploy_production",
                "post_deploy_verification",
            ],
            requires_approval=False,  # Hotfix may auto-approve
        )

    async def test_feature(self) -> Dict[str, Any]:
        """Test feature development workflow."""
        print("\n" + "=" * 80)
        print("Testing Feature Development Workflow")
        print("=" * 80)

        context = {
            "task_description": "Add test feature for workflow validation",
            "project_path": "/opt/Dev-Tools/agent_orchestrator",
            "language": "python",
            "framework": "FastAPI",
            "requires_infrastructure": False,
            "requires_cicd": False,
        }

        return await self._execute_and_validate(
            "feature.workflow.yaml",
            context,
            expected_steps=[
                "analyze_requirements",
                "implement_feature",
                "code_review",
                "run_tests",
                "update_documentation",
                "approval_gate",
            ],
            requires_approval=True,
        )

    async def test_docs_update(self) -> Dict[str, Any]:
        """Test documentation update workflow."""
        print("\n" + "=" * 80)
        print("Testing Documentation Update Workflow")
        print("=" * 80)

        context = {
            "files_changed": [
                "README.md",
                "support/docs/getting-started/QUICK_START.md",
            ],
            "pr_number": 789,
            "change_type": "typo_fix",
            "author": "contributor",
        }

        return await self._execute_and_validate(
            "docs-update.workflow.yaml",
            context,
            expected_steps=[
                "validate_docs_only",
                "review_documentation",
                "check_approval_needed",
                "merge_documentation",
            ],
            requires_approval=False,  # Low-risk may auto-approve
        )

    async def test_infrastructure(self) -> Dict[str, Any]:
        """Test infrastructure deployment workflow."""
        print("\n" + "=" * 80)
        print("Testing Infrastructure Deployment Workflow")
        print("=" * 80)

        context = {
            "changes_description": "Add test PostgreSQL resource",
            "cloud_provider": "digitalocean",
            "environment": "staging",
            "iac_tool": "terraform",
            "resources": ["droplet", "managed_database"],
        }

        return await self._execute_and_validate(
            "infrastructure.workflow.yaml",
            context,
            expected_steps=[
                "analyze_changes",
                "generate_plan",
                "approval_gate",
                "apply_changes",
                "update_documentation",
            ],
            requires_approval=True,
        )

    async def _execute_and_validate(
        self,
        template_name: str,
        context: Dict[str, Any],
        expected_steps: List[str],
        requires_approval: bool,
    ) -> Dict[str, Any]:
        """Execute workflow and validate results."""

        result = {
            "workflow": template_name,
            "status": "pending",
            "errors": [],
            "warnings": [],
            "start_time": datetime.utcnow().isoformat(),
        }

        try:
            # Step 1: Execute workflow
            print(f"\n1. Executing workflow: {template_name}")
            print(f"   Context: {json.dumps(context, indent=2)}")

            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(
                    f"{self.orchestrator_url}/workflow/execute",
                    json={"template_name": template_name, "context": context},
                )

                if response.status_code != 200:
                    result["status"] = "failed"
                    result["errors"].append(
                        f"Execution failed: {response.status_code} - {response.text}"
                    )
                    return result

                execution_data = response.json()
                workflow_id = execution_data["workflow_id"]
                result["workflow_id"] = workflow_id

                print(f"   ✓ Workflow started: {workflow_id}")

            # Step 2: Poll status until paused or completed
            print(f"\n2. Monitoring workflow execution...")

            state = await self._poll_workflow(workflow_id, max_wait=120)
            result["final_status"] = state["status"]
            result["step_statuses"] = state.get("step_statuses", {})

            # Step 3: Validate steps executed
            print(f"\n3. Validating executed steps...")

            executed_steps = [
                step_id
                for step_id, status in state.get("step_statuses", {}).items()
                if status in ["completed", "running"]
            ]

            missing_steps = [
                step
                for step in expected_steps
                if step not in executed_steps
                and not self._step_conditional(step, context)
            ]

            if missing_steps:
                result["warnings"].append(
                    f"Expected steps not executed: {missing_steps}"
                )
                print(f"   ⚠ Missing steps: {missing_steps}")
            else:
                print(f"   ✓ All expected steps executed")

            # Step 4: Handle approval if needed
            if state["status"] == "paused" and requires_approval:
                print(f"\n4. Workflow paused for approval...")
                print(f"   Linear issue: Check Linear for approval request")
                print(
                    f"   Resume: POST {self.orchestrator_url}/workflow/resume/{workflow_id}"
                )

                # Auto-approve for testing
                print(f"   Auto-approving for test...")

                async with httpx.AsyncClient(timeout=60.0) as client:
                    resume_response = await client.post(
                        f"{self.orchestrator_url}/workflow/resume/{workflow_id}",
                        json={"approval_decision": "approved"},
                    )

                    if resume_response.status_code == 200:
                        print(f"   ✓ Workflow resumed")

                        # Poll again until completion
                        final_state = await self._poll_workflow(
                            workflow_id, max_wait=120
                        )
                        result["final_status"] = final_state["status"]
                        result["step_statuses"] = final_state.get("step_statuses", {})
                    else:
                        result["warnings"].append(
                            f"Resume failed: {resume_response.text}"
                        )

            # Step 5: Final validation
            print(f"\n5. Final validation...")

            if result["final_status"] == "completed":
                print(f"   ✓ Workflow completed successfully")
                result["status"] = "passed"
            elif result["final_status"] == "failed":
                print(f"   ✗ Workflow failed")
                result["status"] = "failed"
                result["errors"].append(
                    f"Workflow failed: {state.get('error_message')}"
                )
            else:
                print(f"   ⚠ Workflow in unexpected state: {result['final_status']}")
                result["status"] = "incomplete"

            result["end_time"] = datetime.utcnow().isoformat()

        except Exception as e:
            result["status"] = "error"
            result["errors"].append(f"Test error: {str(e)}")
            print(f"   ✗ Test error: {e}")

        return result

    async def _poll_workflow(
        self,
        workflow_id: str,
        max_wait: int = 120,
        poll_interval: int = 5,
    ) -> Dict[str, Any]:
        """Poll workflow status until completed or paused."""

        start_time = datetime.utcnow()

        async with httpx.AsyncClient(timeout=30.0) as client:
            while True:
                elapsed = (datetime.utcnow() - start_time).total_seconds()
                if elapsed > max_wait:
                    raise TimeoutError(
                        f"Workflow {workflow_id} did not complete within {max_wait}s"
                    )

                response = await client.get(
                    f"{self.orchestrator_url}/workflow/status/{workflow_id}"
                )

                if response.status_code != 200:
                    raise RuntimeError(f"Failed to get status: {response.status_code}")

                state = response.json()
                status = state["status"]
                current_step = state.get("current_step", "unknown")

                print(f"   Status: {status} | Step: {current_step}")

                if status in ["completed", "failed", "paused"]:
                    return state

                await asyncio.sleep(poll_interval)

    def _step_conditional(self, step_id: str, context: Dict[str, Any]) -> bool:
        """Check if step is conditional and may be skipped."""

        # Infrastructure and CI/CD steps may be skipped based on context
        conditional_steps = {
            "update_infrastructure": not context.get("requires_infrastructure", False),
            "update_cicd": not context.get("requires_cicd", False),
        }

        return conditional_steps.get(step_id, False)

    async def run_all_tests(self):
        """Run all workflow tests."""

        tests = [
            ("pr-deployment", self.test_pr_deployment),
            ("hotfix", self.test_hotfix),
            ("feature", self.test_feature),
            ("docs-update", self.test_docs_update),
            ("infrastructure", self.test_infrastructure),
        ]

        print("\n" + "=" * 80)
        print("WORKFLOW TESTING SUITE")
        print("=" * 80)
        print(f"Orchestrator: {self.orchestrator_url}")
        print(f"Start time: {datetime.utcnow().isoformat()}")

        for name, test_func in tests:
            try:
                result = await test_func()
                self.test_results.append(result)
            except Exception as e:
                print(f"\n✗ Test {name} crashed: {e}")
                self.test_results.append(
                    {
                        "workflow": name,
                        "status": "crashed",
                        "errors": [str(e)],
                    }
                )

        # Print summary
        self._print_summary()

    def _print_summary(self):
        """Print test results summary."""

        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)

        passed = sum(1 for r in self.test_results if r["status"] == "passed")
        failed = sum(1 for r in self.test_results if r["status"] == "failed")
        errors = sum(1 for r in self.test_results if r["status"] == "error")

        print(
            f"\nTotal: {len(self.test_results)} | Passed: {passed} | Failed: {failed} | Errors: {errors}"
        )

        for result in self.test_results:
            status_icon = {
                "passed": "✓",
                "failed": "✗",
                "error": "✗",
                "incomplete": "⚠",
            }.get(result["status"], "?")

            print(f"\n{status_icon} {result['workflow']} - {result['status'].upper()}")

            if result.get("errors"):
                for error in result["errors"]:
                    print(f"  Error: {error}")

            if result.get("warnings"):
                for warning in result["warnings"]:
                    print(f"  Warning: {warning}")

        # Save results to file
        results_file = (
            project_root
            / "support"
            / "reports"
            / f"workflow-test-results-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.json"
        )
        results_file.parent.mkdir(parents=True, exist_ok=True)

        with open(results_file, "w") as f:
            json.dump(self.test_results, f, indent=2)

        print(f"\nResults saved to: {results_file}")


async def main():
    """Main entry point."""

    orchestrator_url = os.getenv("ORCHESTRATOR_URL", "http://localhost:8001")

    tester = WorkflowTester(orchestrator_url)

    if len(sys.argv) > 1:
        # Test specific workflow
        workflow_name = sys.argv[1]

        test_map = {
            "pr-deployment": tester.test_pr_deployment,
            "hotfix": tester.test_hotfix,
            "feature": tester.test_feature,
            "docs-update": tester.test_docs_update,
            "infrastructure": tester.test_infrastructure,
        }

        if workflow_name not in test_map:
            print(f"Unknown workflow: {workflow_name}")
            print(f"Available: {', '.join(test_map.keys())}")
            sys.exit(1)

        result = await test_map[workflow_name]()
        tester.test_results.append(result)
        tester._print_summary()
    else:
        # Run all tests
        await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
