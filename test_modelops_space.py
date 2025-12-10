#!/usr/bin/env python3
"""Test ModelOps Space deployment with demo training job"""

from agent_orchestrator.agents.infrastructure.modelops.training import (
    ModelOpsTrainerClient,
)

# Initialize client
client = ModelOpsTrainerClient()

# Prepare demo dataset
csv_data = """text,response
Write a hello world function,def hello():\n    print("Hello World")
Write a function to add two numbers,def add(a, b):\n    return a + b
Write a loop from 1 to 10,for i in range(1, 11):\n    print(i)
"""

# Submit demo training job
print("Submitting demo training job...")
job = client.submit_training_job(
    csv_data=csv_data,
    base_model="microsoft/Phi-3-mini-4k-instruct",
    project_name="test-demo",
    is_demo=True,
)

print(f"\n✓ Job submitted successfully!")
print(f"  Job ID: {job['job_id']}")
print(f"  Status: {job['status']}")
print(f"\n  Check status with:")
print(f"    client.get_job_status('{job['job_id']}')")
print(f"\n  Space URL: https://alextorelli-code-chef-modelops-trainer.hf.space")
