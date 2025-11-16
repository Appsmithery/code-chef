#!/usr/bin/env python3
"""
Direct test of DigitalOcean Gradient AI endpoint

Based on: https://docs.digitalocean.com/products/gradientai-platform/how-to/use-serverless-inference/#use
"""

import os
import asyncio
from dotenv import load_dotenv
from pathlib import Path
from openai import AsyncOpenAI

# Load environment
repo_root = Path(__file__).parent.parent
env_file = repo_root / "config" / "env" / ".env"
load_dotenv(env_file)

async def test_gradient_direct():
    """Test DigitalOcean Gradient AI using OpenAI SDK directly"""
    
    # For DO Gradient AI, we need the DigitalOcean PAT, not GRADIENT_MODEL_ACCESS_KEY
    api_key = os.getenv("DIGITAL_OCEAN_PAT")
    gradient_key = os.getenv("GRADIENT_MODEL_ACCESS_KEY") or os.getenv("GRADIENT_API_KEY")
    
    if not api_key:
        print("❌ No DIGITAL_OCEAN_PAT found")
        print("   DigitalOcean Gradient AI requires a Personal Access Token")
        return False
    
    print(f"Using DIGITAL_OCEAN_PAT (first 10 chars): {api_key[:10]}...")
    if gradient_key:
        print(f"Also found GRADIENT_MODEL_ACCESS_KEY: {gradient_key[:10]}...")
    
    # According to DO docs: https://docs.digitalocean.com/products/gradientai-platform/how-to/use-serverless-inference/#use
    # The endpoint should be OpenAI-compatible with DO PAT as auth
    
    base_url = "https://api.digitalocean.com/v2/ai"
    
    print(f"\n{'='*60}")
    print(f"Testing Gradient AI Serverless Inference")
    print(f"Base URL: {base_url}")
    print(f"Model: llama-3.1-8b-instruct")
    print(f"Auth: Bearer <DIGITAL_OCEAN_PAT>")
    print(f"{'='*60}")
    
    try:
        client = AsyncOpenAI(
            base_url=base_url,
            api_key=api_key
        )
        
        print("\nSending request...")
        response = await client.chat.completions.create(
            model="llama-3.1-8b-instruct",
            messages=[{"role": "user", "content": "What is 2+2? Answer briefly."}],
            max_tokens=50,
            temperature=0.7
        )
        
        print(f"\n✅ SUCCESS!")
        print(f"Model: {response.model}")
        print(f"Response: {response.choices[0].message.content}")
        print(f"Tokens used: {response.usage.total_tokens}")
        return True
        
    except Exception as e:
        print(f"\n❌ FAILED: {type(e).__name__}")
        print(f"Error: {e}")
        
        # Try to get more details
        if hasattr(e, 'response'):
            print(f"\nResponse status: {e.response.status_code if hasattr(e.response, 'status_code') else 'N/A'}")
            print(f"Response headers: {dict(e.response.headers) if hasattr(e.response, 'headers') else 'N/A'}")
        
        return False

if __name__ == "__main__":
    asyncio.run(test_gradient_direct())
