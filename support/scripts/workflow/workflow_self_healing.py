#!/usr/bin/env python3
"""
Multi-Agent Self-Healing Infrastructure Workflow

Demonstrates autonomous infrastructure monitoring and remediation:
1. Infrastructure Agent: Detects anomaly (high CPU, disk full, service down)
2. Infrastructure Agent: Diagnoses root cause
3. Infrastructure Agent: Proposes remediation plan
4. Orchestrator: Validates plan safety
5. Infrastructure Agent: Executes remediation (with config lock)
6. Infrastructure Agent: Verifies fix
7. Documentation Agent: Records incident

Key Features:
- Config file locking (prevents concurrent changes)
- Autonomous diagnosis and remediation
- Safety validation before execution
- Incident documentation
- Rollback on failure

Usage:
    python support/scripts/workflow_self_healing.py --server web-01 --issue high_cpu
"""

import asyncio
import argparse
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

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


class SelfHealingWorkflow:
    """Orchestrates autonomous infrastructure remediation"""
    
    REMEDIATION_PLANS = {
        "high_cpu": {
            "diagnosis": "Process runaway consuming 95% CPU",
            "root_cause": "Memory leak in background worker",
            "actions": [
                "Restart background worker service",
                "Update service memory limits",
                "Enable heap profiling"
            ],
            "config_files": ["systemd/worker.service", "limits.conf"]
        },
        "disk_full": {
            "diagnosis": "Disk usage at 98% on /var/log",
            "root_cause": "Log rotation not configured",
            "actions": [
                "Clean up old log files (>30 days)",
                "Configure logrotate",
                "Set up disk usage alerts"
            ],
            "config_files": ["logrotate.d/app", "alertmanager.yml"]
        },
        "service_down": {
            "diagnosis": "Web service not responding",
            "root_cause": "Database connection pool exhausted",
            "actions": [
                "Restart web service",
                "Increase connection pool size",
                "Add connection timeout monitoring"
            ],
            "config_files": ["app.config.yaml", "prometheus.yml"]
        }
    }
    
    def __init__(self, server: str, issue_type: str):
        self.server = server
        self.issue_type = issue_type
        self.workflow_id = f"heal-{server}-{issue_type}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        # Initialize managers
        self.state_mgr = WorkflowStateManager(DB_CONN_STRING)
        self.lock_mgr = ResourceLockManager(DB_CONN_STRING)
        
        # Get remediation plan
        self.plan = self.REMEDIATION_PLANS.get(issue_type)
        if not self.plan:
            raise ValueError(f"Unknown issue type: {issue_type}")
        
        # Workflow state
        self.workflow_state = {
            "server": server,
            "issue_type": issue_type,
            "detected_at": datetime.now().isoformat(),
            "diagnosis": None,
            "remediation_plan": None,
            "plan_validated": False,
            "remediation_executed": False,
            "fix_verified": False,
            "incident_documented": False
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
    
    async def step_1_detect_anomaly(self) -> Dict[str, Any]:
        """Step 1: Detect infrastructure anomaly"""
        print("\n" + "="*70)
        print("STEP 1: Detect Anomaly")
        print("="*70)
        
        print(f"Monitoring server: {self.server}")
        
        # Simulate monitoring
        await asyncio.sleep(1)
        
        detection_result = {
            "server": self.server,
            "issue_type": self.issue_type,
            "severity": "high",
            "detected_at": datetime.now().isoformat(),
            "metrics": {
                "cpu_usage": 95.3 if self.issue_type == "high_cpu" else 45.2,
                "disk_usage": 98.1 if self.issue_type == "disk_full" else 67.4,
                "service_status": "down" if self.issue_type == "service_down" else "healthy"
            }
        }
        
        # Checkpoint
        await self.state_mgr.checkpoint(
            self.workflow_id,
            step_name="detect_anomaly",
            agent_id="infrastructure-agent",
            data={"state": self.workflow_state, "result": detection_result}
        )
        
        print(f"⚠ Anomaly detected: {self.issue_type}")
        print(f"✓ Server: {self.server}")
        print(f"✓ Severity: {detection_result['severity']}")
        print(f"✓ Metrics: {detection_result['metrics']}")
        
        return detection_result
    
    async def step_2_diagnose_root_cause(self) -> Dict[str, Any]:
        """Step 2: Diagnose root cause"""
        print("\n" + "="*70)
        print("STEP 2: Diagnose Root Cause")
        print("="*70)
        
        print(f"Analyzing {self.issue_type} on {self.server}...")
        
        # Simulate diagnosis
        await asyncio.sleep(2)
        
        diagnosis_result = {
            "diagnosis": self.plan["diagnosis"],
            "root_cause": self.plan["root_cause"],
            "confidence": 0.92,
            "evidence": [
                "Process PID 12345 consuming 95% CPU for 2 hours",
                "Memory usage grew from 2GB to 14GB over 2 hours",
                "Background worker logs show repeated OOM warnings"
            ] if self.issue_type == "high_cpu" else [
                "Disk usage increased 40% in last 24 hours",
                "No logrotate config found for application logs",
                "/var/log/app contains 50GB of uncompressed logs"
            ] if self.issue_type == "disk_full" else [
                "Web service returning 502 Bad Gateway",
                "Database connections maxed at 100/100",
                "Connection pool exhaustion errors in logs"
            ]
        }
        
        self.workflow_state["diagnosis"] = diagnosis_result
        
        # Checkpoint
        await self.state_mgr.checkpoint(
            self.workflow_id,
            step_name="diagnose_root_cause",
            agent_id="infrastructure-agent",
            data={"state": self.workflow_state, "result": diagnosis_result}
        )
        
        print(f"✓ Diagnosis: {diagnosis_result['diagnosis']}")
        print(f"✓ Root Cause: {diagnosis_result['root_cause']}")
        print(f"✓ Confidence: {diagnosis_result['confidence']*100:.0f}%")
        print(f"✓ Evidence:")
        for evidence in diagnosis_result['evidence']:
            print(f"  - {evidence}")
        
        return diagnosis_result
    
    async def step_3_propose_remediation(self) -> Dict[str, Any]:
        """Step 3: Propose remediation plan"""
        print("\n" + "="*70)
        print("STEP 3: Propose Remediation Plan")
        print("="*70)
        
        remediation_plan = {
            "actions": self.plan["actions"],
            "config_files": self.plan["config_files"],
            "estimated_duration_minutes": 5,
            "risk_level": "medium",
            "rollback_plan": "Revert config files to previous versions"
        }
        
        self.workflow_state["remediation_plan"] = remediation_plan
        
        # Checkpoint
        await self.state_mgr.checkpoint(
            self.workflow_id,
            step_name="propose_remediation",
            agent_id="infrastructure-agent",
            data={"state": self.workflow_state, "result": remediation_plan}
        )
        
        print(f"✓ Proposed Actions:")
        for i, action in enumerate(remediation_plan['actions'], 1):
            print(f"  {i}. {action}")
        print(f"✓ Config Files: {', '.join(remediation_plan['config_files'])}")
        print(f"✓ Estimated Duration: {remediation_plan['estimated_duration_minutes']} minutes")
        print(f"✓ Risk Level: {remediation_plan['risk_level']}")
        
        return remediation_plan
    
    async def step_4_validate_plan(self) -> Dict[str, Any]:
        """Step 4: Validate remediation plan safety"""
        print("\n" + "="*70)
        print("STEP 4: Validate Plan Safety")
        print("="*70)
        
        print(f"Validating remediation plan for {self.server}...")
        
        # Simulate validation
        await asyncio.sleep(1)
        
        validation_result = {
            "validated": True,
            "safety_checks": {
                "production_impact": "low",
                "data_loss_risk": "none",
                "service_interruption": "minimal (<30s)",
                "rollback_available": True
            },
            "approved_by": "orchestrator"
        }
        
        self.workflow_state["plan_validated"] = True
        
        # Checkpoint
        await self.state_mgr.checkpoint(
            self.workflow_id,
            step_name="validate_plan",
            agent_id="orchestrator",
            data={"state": self.workflow_state, "result": validation_result}
        )
        
        print(f"✓ Plan Validated: {validation_result['validated']}")
        print(f"✓ Safety Checks:")
        for check, result in validation_result['safety_checks'].items():
            print(f"  - {check}: {result}")
        
        return validation_result
    
    async def step_5_execute_remediation(self) -> Dict[str, Any]:
        """Step 5: Execute remediation with config lock"""
        print("\n" + "="*70)
        print("STEP 5: Execute Remediation (with config lock)")
        print("="*70)
        
        # Lock config files
        config_locks = [f"config:{self.server}:{cfg}" for cfg in self.plan["config_files"]]
        
        print(f"Acquiring locks on {len(config_locks)} config files...")
        
        # Acquire all locks
        locked_resources = []
        try:
            for resource in config_locks:
                async with self.lock_mgr.lock(
                    resource_id=resource,
                    agent_id="infrastructure-agent",
                    timeout_seconds=600,
                    reason=f"Executing remediation for {self.issue_type} on {self.server}"
                ):
                    locked_resources.append(resource)
                    print(f"✓ Lock acquired: {resource}")
                    
                    # Execute remediation actions
                    print(f"\nExecuting remediation actions...")
                    for i, action in enumerate(self.plan["actions"], 1):
                        print(f"  {i}. {action}...")
                        await asyncio.sleep(1)  # Simulate action execution
                        print(f"     ✓ Complete")
                    
                    execution_result = {
                        "status": "success",
                        "actions_executed": len(self.plan["actions"]),
                        "config_files_modified": self.plan["config_files"],
                        "execution_time_seconds": len(self.plan["actions"]) * 1.2,
                        "server": self.server
                    }
                    
                    self.workflow_state["remediation_executed"] = True
                    
                    # Checkpoint
                    await self.state_mgr.checkpoint(
                        self.workflow_id,
                        step_name="execute_remediation",
                        agent_id="infrastructure-agent",
                        data={"state": self.workflow_state, "result": execution_result}
                    )
                    
                    print(f"\n✓ Remediation executed successfully")
                    print(f"✓ Actions: {execution_result['actions_executed']}")
                    print(f"✓ Duration: {execution_result['execution_time_seconds']:.1f}s")
            
            # Release locks
            for resource in locked_resources:
                print(f"✓ Lock released: {resource}")
            
            return execution_result
            
        except Exception as e:
            print(f"\n❌ Remediation failed: {e}")
            print(f"Rolling back changes...")
            await asyncio.sleep(1)
            print(f"✓ Rollback complete")
            raise
    
    async def step_6_verify_fix(self) -> Dict[str, Any]:
        """Step 6: Verify remediation worked"""
        print("\n" + "="*70)
        print("STEP 6: Verify Fix")
        print("="*70)
        
        print(f"Verifying remediation on {self.server}...")
        
        # Simulate verification
        await asyncio.sleep(2)
        
        verification_result = {
            "fixed": True,
            "post_remediation_metrics": {
                "cpu_usage": 12.3 if self.issue_type == "high_cpu" else 45.2,
                "disk_usage": 65.4 if self.issue_type == "disk_full" else 67.4,
                "service_status": "healthy"
            },
            "improvement": "83% reduction in CPU usage" if self.issue_type == "high_cpu"
                          else "33% reduction in disk usage" if self.issue_type == "disk_full"
                          else "Service restored to healthy status"
        }
        
        self.workflow_state["fix_verified"] = True
        
        # Checkpoint
        await self.state_mgr.checkpoint(
            self.workflow_id,
            step_name="verify_fix",
            agent_id="infrastructure-agent",
            data={"state": self.workflow_state, "result": verification_result}
        )
        
        print(f"✓ Fix Verified: {verification_result['fixed']}")
        print(f"✓ Improvement: {verification_result['improvement']}")
        print(f"✓ Post-Remediation Metrics:")
        for metric, value in verification_result['post_remediation_metrics'].items():
            print(f"  - {metric}: {value}")
        
        return verification_result
    
    async def step_7_document_incident(self) -> Dict[str, Any]:
        """Step 7: Document incident and remediation"""
        print("\n" + "="*70)
        print("STEP 7: Document Incident")
        print("="*70)
        
        print(f"Creating incident report...")
        
        # Simulate documentation
        await asyncio.sleep(1)
        
        documentation_result = {
            "incident_id": self.workflow_id,
            "report_created": True,
            "files_updated": [
                "incidents/2025-11-19-high-cpu-web-01.md",
                "runbooks/high-cpu-remediation.md"
            ],
            "knowledge_base_updated": True
        }
        
        self.workflow_state["incident_documented"] = True
        
        # Final checkpoint
        await self.state_mgr.checkpoint(
            self.workflow_id,
            step_name="document_incident",
            agent_id="documentation-agent",
            data={"state": self.workflow_state, "result": documentation_result}
        )
        
        print(f"✓ Report Created: {documentation_result['report_created']}")
        print(f"✓ Files Updated:")
        for file in documentation_result['files_updated']:
            print(f"  - {file}")
        
        return documentation_result
    
    async def run(self) -> Dict[str, Any]:
        """Execute complete self-healing workflow"""
        print("\n" + "="*80)
        print(f" SELF-HEALING WORKFLOW: {self.server}")
        print("="*80)
        print(f"Issue: {self.issue_type}")
        print(f"Workflow ID: {self.workflow_id}")
        
        start_time = datetime.now()
        
        try:
            # Create workflow
            await self.state_mgr.create_workflow(
                workflow_id=self.workflow_id,
                workflow_type="self_healing",
                initial_state=self.workflow_state,
                participating_agents=["infrastructure", "orchestrator", "documentation"],
                metadata={
                    "server": self.server,
                    "issue_type": self.issue_type
                }
            )
            
            # Execute workflow steps
            detection = await self.step_1_detect_anomaly()
            diagnosis = await self.step_2_diagnose_root_cause()
            plan = await self.step_3_propose_remediation()
            validation = await self.step_4_validate_plan()
            
            if not validation["validated"]:
                raise Exception("Remediation plan failed safety validation")
            
            execution = await self.step_5_execute_remediation()
            verification = await self.step_6_verify_fix()
            
            if not verification["fixed"]:
                raise Exception("Verification failed - issue not resolved")
            
            documentation = await self.step_7_document_incident()
            
            # Mark workflow complete
            await self.state_mgr.complete_workflow(
                self.workflow_id,
                final_state={
                    "status": "success",
                    "server": self.server,
                    "issue_type": self.issue_type,
                    "actions_executed": len(self.plan["actions"]),
                    "fix_verified": True
                }
            )
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # Summary
            print("\n" + "="*80)
            print(" SELF-HEALING COMPLETE")
            print("="*80)
            print(f"✓ Issue: {self.issue_type}")
            print(f"✓ Root Cause: {diagnosis['root_cause']}")
            print(f"✓ Actions: {len(self.plan['actions'])} executed")
            print(f"✓ Improvement: {verification['improvement']}")
            print(f"✓ Incident: {documentation['incident_id']}")
            print(f"\nTotal Duration: {duration:.1f}s")
            
            return {
                "status": "success",
                "workflow_id": self.workflow_id,
                "duration_seconds": duration,
                "issue_resolved": True
            }
            
        except Exception as e:
            print(f"\n❌ SELF-HEALING FAILED: {e}")
            
            await self.state_mgr.update_state(
                self.workflow_id,
                updates={
                    "status": "failed",
                    "error": str(e),
                    "failed_at": datetime.now().isoformat()
                },
                agent_id="infrastructure-agent"
            )
            
            raise


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Self-Healing Infrastructure Workflow")
    parser.add_argument("--server", required=True, help="Server name (e.g., web-01)")
    parser.add_argument("--issue", required=True, 
                       choices=["high_cpu", "disk_full", "service_down"],
                       help="Issue type")
    
    args = parser.parse_args()
    
    workflow = SelfHealingWorkflow(args.server, args.issue)
    
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
