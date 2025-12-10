#!/usr/bin/env python3
"""Simple test for ModelOps Space health check without full orchestrator imports."""

import httpx

def test_space_health():
    """Test Space health endpoint."""
    space_url = "https://alextorelli-code-chef-modelops-trainer.hf.space"
    
    print(f"Testing {space_url}/health...")
    
    try:
        response = httpx.get(f"{space_url}/health", timeout=30.0)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Space is healthy!")
            print(f"  Service: {data.get('service')}")
            print(f"  Status: {data.get('status')}")
            print(f"  AutoTrain: {data.get('autotrain_available')}")
            print(f"  HF Token: {data.get('hf_token_configured')}")
            return True
        else:
            print(f"✗ Health check failed: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return False
    
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

if __name__ == "__main__":
    import sys
    success = test_space_health()
    sys.exit(0 if success else 1)
