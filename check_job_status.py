#!/usr/bin/env python3
"""Check status of ModelOps training job"""

import sys

from agent_orchestrator.agents.infrastructure.modelops.training import (
    ModelOpsTrainerClient,
)

if len(sys.argv) < 2:
    print("Usage: python check_job_status.py <job_id>")
    sys.exit(1)

job_id = sys.argv[1]
client = ModelOpsTrainerClient()

print(f"Checking status for job: {job_id}")
status = client.get_job_status(job_id)

print(f"\n  Job ID: {status['job_id']}")
print(f"  Status: {status['status']}")
if status.get("hub_repo"):
    print(f"  Model: {status['hub_repo']}")
if status.get("tensorboard_url"):
    print(f"  TensorBoard: {status['tensorboard_url']}")
if status.get("error"):
    print(f"  Error: {status['error']}")
