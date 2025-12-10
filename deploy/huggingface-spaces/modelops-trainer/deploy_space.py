#!/usr/bin/env python3
"""Deploy ModelOps Trainer to HuggingFace Space."""

import os
import sys
from pathlib import Path
from huggingface_hub import HfApi, login

def deploy_space():
    """Deploy the Space to HuggingFace."""
    # Get token from environment or MCP config
    token = os.getenv('HF_TOKEN') or os.getenv('HUGGINGFACE_TOKEN')
    
    if not token:
        # Try to read from HuggingFace CLI config
        try:
            from huggingface_hub import HfFolder
            token = HfFolder.get_token()
        except Exception:
            pass
    
    if not token:
        print("Error: No HuggingFace token found.")
        print("Please set HF_TOKEN or HUGGINGFACE_TOKEN environment variable.")
        sys.exit(1)
    
    # Login
    try:
        login(token=token)
        print("✓ Authenticated with HuggingFace")
    except Exception as e:
        print(f"Error logging in: {e}")
        sys.exit(1)
    
    # Create API client
    api = HfApi()
    
    # Space details
    space_name = "code-chef-modelops-trainer"
    username = "alextorelli"
    repo_id = f"{username}/{space_name}"
    
    # Create Space
    try:
        print(f"Creating Space: {repo_id}...")
        api.create_repo(
            repo_id=repo_id,
            repo_type="space",
            space_sdk="gradio",
            private=True,
            exist_ok=True
        )
        print(f"✓ Space created/verified: {repo_id}")
    except Exception as e:
        print(f"Error creating Space: {e}")
        sys.exit(1)
    
    # Upload files
    try:
        print("Uploading files...")
        current_dir = Path(__file__).parent
        
        api.upload_folder(
            folder_path=str(current_dir),
            repo_id=repo_id,
            repo_type="space",
            ignore_patterns=[
                ".git/*",
                ".git",
                "__pycache__/*",
                "*.pyc",
                "*.pyo",
                "*.pyd",
                ".Python",
                "deploy_space.py",  # Don't upload this script
            ]
        )
        print("✓ Files uploaded successfully")
    except Exception as e:
        print(f"Error uploading files: {e}")
        sys.exit(1)
    
    # Set secrets (HF_TOKEN)
    try:
        print("Configuring Space secrets...")
        api.add_space_secret(repo_id=repo_id, key="HF_TOKEN", value=token)
        print("✓ HF_TOKEN secret configured")
    except Exception as e:
        print(f"Warning: Could not set HF_TOKEN secret: {e}")
        print("Please set it manually in Space settings")
    
    print(f"\n✓ Deployment complete!")
    print(f"  Space URL: https://huggingface.co/spaces/{repo_id}")
    print(f"  API URL: https://alextorelli-code-chef-modelops-trainer.hf.space")
    print(f"\nNext steps:")
    print(f"  1. Wait 2-3 minutes for Space to build")
    print(f"  2. Check health: https://alextorelli-code-chef-modelops-trainer.hf.space/health")
    print(f"  3. Upgrade to t4-small GPU in Space settings for production use")

if __name__ == "__main__":
    deploy_space()
