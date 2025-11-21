#!/usr/bin/env python3
"""
Multi-Agent PR Deployment Workflow

Demonstrates coordinated multi-agent workflow for:
1. Code Review Agent: Reviews PR changes
2. CI/CD Agent: Runs tests
3. Infrastructure Agent: Provisions resources (if needed)
4. CI/CD Agent: Deploys to staging (with resource lock)
5. Orchestrator: Approval gate (HITL)
6. CI/CD Agent: Deploys to production (with resource lock)
7. Documentation Agent: Updates deployment docs

Key Features:
- Resource locking for deployment environments (prevents concurrent deploys)
- Workflow state checkpointing (resume after failures)
- Inter-agent communication via event protocol
- Conditional routing based on test results
- Human-in-the-loop approval gate

Usage:
    python support/scripts/workflow_pr_deploy.py --pr-id PR-123 --branch feature/new-feature
"""

import asyncio
import argparse
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

# Add repo root to path
repo_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(repo_root))

from shared.lib.workflow_state import WorkflowStateManager
from shared.lib.resource_lock_manager import ResourceLockManager

# Database connection
DB_CONN_STRING = os.getenv(
    "DATABASE_URL",
    "postgresql://devtools:changeme@localhost:5432/devtools"
)

# LangGraph orchestrator endpoint (all agent nodes accessible through orchestrator)
ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "http://localhost:8001")

# Note: Individual agent URLs removed - all agents now internal LangGraph nodes
# Use orchestrator's /orchestrate/langgraph endpoint for all agent interactions


class PRDeploymentWorkflow:
    """Orchestrates multi-agent PR deployment workflow"""
    
    def __init__(self, pr_id: str, branch: str, target_env: str = "production"):
        self.pr_id = pr_id
        self.branch = branch
        self.target_env = target_env
        self.workflow_id = f"pr-deploy-{pr_id}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        # Initialize managers
        self.state_mgr = WorkflowStateManager(DB_CONN_STRING)
        self.lock_mgr = ResourceLockManager(DB_CONN_STRING)
        
        # Workflow state
        self.workflow_state = {
            "pr_id": pr_id,
            "branch": branch,
            "target_env": target_env,
            "review_status": None,
            "test_results": None,
            "staging_deployed": False,
            "approval_received": False,
            "production_deployed": False,
            "docs_updated": False
        }
    
    async def initialize(self):
        """Initialize connections"""
        await self.state_mgr.connect()
        await self.lock_mgr.connect()
        print(f"✓ Initialized workflow: {self.workflow_id}")
    
    async def close(self):
        """Cleanup connections"""
        await self.state_mgr.close()
        await self.lock_mgr.close()
    
    async def step_1_code_review(self) -> Dict[str, Any]:
        """Step 1: Code Review Agent reviews PR"""
        print("\n" + "="*70)
        print("STEP 1: Code Review")
        print("="*70)
        
        # Simulate code review request
        review_request = {
            "pr_id": self.pr_id,
            "branch": self.branch,
            "checks": ["security", "quality", "best-practices"]
        }
        
        print(f"Requesting code review for PR-{self.pr_id} on branch '{self.branch}'...")
        
        # Simulate review (in real implementation, would call CODE_REVIEW_URL)
        await asyncio.sleep(1)  # Simulate review time
        
        review_result = {
            "status": "approved",
            "score": 85,
            "issues": ["Consider adding more unit tests"],
            "security_scan": "passed",
            "quality_gate": "passed"
        }
        
        self.workflow_state["review_status"] = review_result["status"]
        
        # Checkpoint workflow state
        await self.state_mgr.checkpoint(
            self.workflow_id,
            step_name="code_review",
            agent_id="code-review-agent",
            data={"state": self.workflow_state, "result": review_result}
        )
        
        print(f"✓ Review Status: {review_result['status']}")
        print(f"✓ Score: {review_result['score']}/100")
        print(f"✓ Security: {review_result['security_scan']}")
        
        return review_result
    
    async def step_2_run_tests(self) -> Dict[str, Any]:
        """Step 2: CI/CD Agent runs test suite"""
        print("\n" + "="*70)
        print("STEP 2: Run Tests")
        print("="*70)
        
        test_request = {
            "branch": self.branch,
            "test_suites": ["unit", "integration", "e2e"]
        }
        
        print(f"Running test suites: {test_request['test_suites']}")
        
        # Simulate test execution
        await asyncio.sleep(2)
        
        test_result = {
            "status": "passed",
            "total_tests": 247,
            "passed": 245,
            "failed": 2,
            "skipped": 0,
            "duration_seconds": 45.3,
            "coverage": 87.5
        }
        
        self.workflow_state["test_results"] = test_result
        
        # Checkpoint
        await self.state_mgr.checkpoint(
            self.workflow_id,
            step_name="run_tests",
            agent_id="cicd-agent",
            data={"state": self.workflow_state, "result": test_result}
        )
        
        print(f"✓ Tests: {test_result['passed']}/{test_result['total_tests']} passed")
        print(f"✓ Coverage: {test_result['coverage']}%")
        print(f"✓ Duration: {test_result['duration_seconds']}s")
        
        if test_result["failed"] > 0:
            print(f"⚠ Warning: {test_result['failed']} tests failed")
        
        return test_result
    
    async def step_3_deploy_staging(self) -> Dict[str, Any]:
        """Step 3: Deploy to staging with resource lock"""
        print("\n" + "="*70)
        print("STEP 3: Deploy to Staging (with resource lock)")
        print("="*70)
        
        staging_resource = "deployment:staging"
        
        # Acquire lock on staging environment
        print(f"Acquiring lock on {staging_resource}...")
        
        async with self.lock_mgr.lock(
            resource_id=staging_resource,
            agent_id="cicd-agent",
            timeout_seconds=300,
            reason=f"Deploying PR-{self.pr_id} to staging"
        ):
            print(f"✓ Lock acquired on {staging_resource}")
            
            # Simulate deployment
            print(f"Deploying branch '{self.branch}' to staging...")
            await asyncio.sleep(3)
            
            deploy_result = {
                "status": "success",
                "environment": "staging",
                "deployment_id": f"staging-deploy-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "url": f"https://staging.example.com/pr-{self.pr_id}",
                "duration_seconds": 3.2
            }
            
            self.workflow_state["staging_deployed"] = True
            
            # Checkpoint
            await self.state_mgr.checkpoint(
                self.workflow_id,
                step_name="deploy_staging",
                agent_id="cicd-agent",
                data={"state": self.workflow_state, "result": deploy_result}
            )
            
            print(f"✓ Deployed to staging: {deploy_result['url']}")
            print(f"✓ Deployment ID: {deploy_result['deployment_id']}")
        
        print(f"✓ Lock released on {staging_resource}")
        
        return deploy_result
    
    async def step_4_approval_gate(self) -> Dict[str, Any]:
        """Step 4: Human-in-the-loop approval gate"""
        print("\n" + "="*70)
        print("STEP 4: Approval Gate (HITL)")
        print("="*70)
        
        print(f"Waiting for approval to deploy PR-{self.pr_id} to production...")
        print(f"Review staging deployment: https://staging.example.com/pr-{self.pr_id}")
        
        # In real implementation, would wait for Linear approval notification
        # For demo, simulate approval after 2 seconds
        await asyncio.sleep(2)
        
        approval_result = {
            "approved": True,
            "approver": "tech-lead",
            "timestamp": datetime.now().isoformat(),
            "comment": "Looks good, proceed with production deployment"
        }
        
        self.workflow_state["approval_received"] = True
        
        # Checkpoint
        await self.state_mgr.checkpoint(
            self.workflow_id,
            step_name="approval_gate",
            agent_id="orchestrator",
            data={"state": self.workflow_state, "result": approval_result}
        )
        
        print(f"✓ Approval received from {approval_result['approver']}")
        print(f"✓ Comment: {approval_result['comment']}")
        
        return approval_result
    
    async def step_5_deploy_production(self) -> Dict[str, Any]:
        """Step 5: Deploy to production with resource lock"""
        print("\n" + "="*70)
        print("STEP 5: Deploy to Production (with resource lock)")
        print("="*70)
        
        prod_resource = f"deployment:{self.target_env}"
        
        # Acquire lock on production environment
        print(f"Acquiring lock on {prod_resource}...")
        
        async with self.lock_mgr.lock(
            resource_id=prod_resource,
            agent_id="cicd-agent",
            timeout_seconds=600,
            reason=f"Deploying PR-{self.pr_id} to {self.target_env}",
            metadata={"pr_id": self.pr_id, "branch": self.branch}
        ):
            print(f"✓ Lock acquired on {prod_resource}")
            
            # Simulate production deployment
            print(f"Deploying branch '{self.branch}' to {self.target_env}...")
            await asyncio.sleep(5)
            
            deploy_result = {
                "status": "success",
                "environment": self.target_env,
                "deployment_id": f"prod-deploy-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "url": f"https://{self.target_env}.example.com",
                "duration_seconds": 5.7,
                "health_check": "passed"
            }
            
            self.workflow_state["production_deployed"] = True
            
            # Checkpoint
            await self.state_mgr.checkpoint(
                self.workflow_id,
                step_name="deploy_production",
                agent_id="cicd-agent",
                data={"state": self.workflow_state, "result": deploy_result}
            )
            
            print(f"✓ Deployed to {self.target_env}: {deploy_result['url']}")
            print(f"✓ Deployment ID: {deploy_result['deployment_id']}")
            print(f"✓ Health check: {deploy_result['health_check']}")
        
        print(f"✓ Lock released on {prod_resource}")
        
        return deploy_result
    
    async def step_6_update_docs(self) -> Dict[str, Any]:
        """Step 6: Update deployment documentation"""
        print("\n" + "="*70)
        print("STEP 6: Update Documentation")
        print("="*70)
        
        docs_request = {
            "pr_id": self.pr_id,
            "deployment_id": f"prod-deploy-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "environment": self.target_env
        }
        
        print(f"Updating deployment documentation...")
        
        # Simulate doc update
        await asyncio.sleep(1)
        
        docs_result = {
            "status": "updated",
            "files_updated": ["CHANGELOG.md", "DEPLOYMENT.md"],
            "changelog_entry": f"PR-{self.pr_id}: Deployed to {self.target_env}"
        }
        
        self.workflow_state["docs_updated"] = True
        
        # Final checkpoint
        await self.state_mgr.checkpoint(
            self.workflow_id,
            step_name="update_docs",
            agent_id="documentation-agent",
            data={"state": self.workflow_state, "result": docs_result}
        )
        
        print(f"✓ Updated files: {', '.join(docs_result['files_updated'])}")
        
        return docs_result
    
    async def run(self) -> Dict[str, Any]:
        """Execute complete workflow"""
        print("\n" + "="*80)
        print(f" PR DEPLOYMENT WORKFLOW: {self.pr_id}")
        print("="*80)
        print(f"Branch: {self.branch}")
        print(f"Target: {self.target_env}")
        print(f"Workflow ID: {self.workflow_id}")
        
        start_time = datetime.now()
        
        try:
            # Create workflow
            await self.state_mgr.create_workflow(
                workflow_id=self.workflow_id,
                workflow_type="pr_deployment",
                initial_state=self.workflow_state,
                participating_agents=["orchestrator", "code-review", "cicd", "infrastructure", "documentation"],
                metadata={
                    "pr_id": self.pr_id,
                    "branch": self.branch,
                    "target_env": self.target_env
                }
            )
            
            # Execute workflow steps
            review_result = await self.step_1_code_review()
            
            if review_result["status"] != "approved":
                raise Exception(f"Code review failed: {review_result['status']}")
            
            test_result = await self.step_2_run_tests()
            
            if test_result["status"] != "passed":
                raise Exception(f"Tests failed: {test_result['failed']} failures")
            
            staging_result = await self.step_3_deploy_staging()
            approval_result = await self.step_4_approval_gate()
            
            if not approval_result["approved"]:
                raise Exception("Deployment approval denied")
            
            prod_result = await self.step_5_deploy_production()
            docs_result = await self.step_6_update_docs()
            
            # Mark workflow complete
            await self.state_mgr.complete_workflow(
                self.workflow_id,
                final_state={
                    "status": "success",
                    "review_score": review_result["score"],
                    "tests_passed": test_result["passed"],
                    "staging_url": staging_result["url"],
                    "production_url": prod_result["url"]
                }
            )
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # Summary
            print("\n" + "="*80)
            print(" WORKFLOW COMPLETE")
            print("="*80)
            print(f"✓ Code Review: {review_result['status']} ({review_result['score']}/100)")
            print(f"✓ Tests: {test_result['passed']}/{test_result['total_tests']} passed")
            print(f"✓ Staging: {staging_result['url']}")
            print(f"✓ Production: {prod_result['url']}")
            print(f"✓ Documentation: {', '.join(docs_result['files_updated'])}")
            print(f"\nTotal Duration: {duration:.1f}s")
            print(f"Workflow ID: {self.workflow_id}")
            
            return {
                "status": "success",
                "workflow_id": self.workflow_id,
                "duration_seconds": duration,
                "results": {
                    "review": review_result,
                    "tests": test_result,
                    "staging": staging_result,
                    "production": prod_result,
                    "docs": docs_result
                }
            }
            
        except Exception as e:
            print(f"\n❌ WORKFLOW FAILED: {e}")
            
            # Mark workflow failed
            await self.state_mgr.update_state(
                self.workflow_id,
                updates={
                    "status": "failed",
                    "error": str(e),
                    "failed_at": datetime.now().isoformat()
                },
                agent_id="orchestrator"
            )
            
            raise


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Multi-Agent PR Deployment Workflow")
    parser.add_argument("--pr-id", required=True, help="PR ID (e.g., PR-123)")
    parser.add_argument("--branch", required=True, help="Git branch name")
    parser.add_argument("--env", default="production", help="Target environment")
    
    args = parser.parse_args()
    
    workflow = PRDeploymentWorkflow(args.pr_id, args.branch, args.env)
    
    try:
        await workflow.initialize()
        result = await workflow.run()
        return 0
    except Exception as e:
        print(f"\nError: {e}")
        return 1
    finally:
        await workflow.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
