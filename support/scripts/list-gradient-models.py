#!/usr/bin/env python3
"""
List Available DigitalOcean Gradient AI Models

Queries the Gradient API to list all available models for serverless inference.
"""

import os
import sys
from gradient import Gradient

def list_models():
    """List all available Gradient AI models."""
    
    # Get API key from environment
    api_key = os.getenv("GRADIENT_MODEL_ACCESS_KEY") or os.getenv("DO_SERVERLESS_INFERENCE_KEY")
    
    if not api_key:
        print("❌ Error: GRADIENT_MODEL_ACCESS_KEY or DO_SERVERLESS_INFERENCE_KEY not set")
        sys.exit(1)
    
    print("🔍 Fetching available Gradient AI models...\n")
    
    try:
        # Initialize client
        client = Gradient(access_token=api_key)
        
        # List models filtered for serverless inference
        response = client.agents.evaluation_metrics.models.list(
            usecases=["MODEL_USECASE_SERVERLESS"],
            public_only=True
        )
        
        if not response.models:
            print("⚠️  No models found")
            return
        
        print(f"✅ Found {len(response.models)} serverless inference models:\n")
        print(f"{'Model ID':<40} {'Name':<50} {'Foundational'}")
        print("=" * 100)
        
        for model in response.models:
            model_id = model.id or "N/A"
            name = model.name or "N/A"
            is_foundational = "✓" if model.is_foundational else ""
            print(f"{model_id:<40} {name:<50} {is_foundational}")
        
        # Show pagination info if available
        if response.meta:
            print(f"\n📄 Page {response.meta.page} of {response.meta.pages} (Total: {response.meta.total})")
        
        # Print recommended models for our use case
        print("\n🎯 Recommended models for orchestrator:")
        print("  - llama3.3-70b-instruct (Best for complex reasoning)")
        print("  - llama3.1-70b-instruct (Good balance)")
        print("  - llama3.1-8b-instruct (Fast, cost-effective)")
        
    except Exception as e:
        print(f"❌ Error listing models: {e}")
        sys.exit(1)

if __name__ == "__main__":
    list_models()
