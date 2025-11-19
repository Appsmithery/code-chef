"""
Test script for Phase 5 chat endpoint

Tests intent recognition, session management, and task creation.
"""

import asyncio
import httpx
import json


async def test_chat_endpoint():
    """Test the /chat endpoint with various scenarios."""
    
    base_url = "http://localhost:8001"
    
    print("=" * 60)
    print("Phase 5 Chat Endpoint Test")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        
        # Test 1: Health check
        print("\n[Test 1] Health check...")
        response = await client.get(f"{base_url}/health")
        health = response.json()
        print(f"✓ Service: {health['service']}")
        print(f"✓ Chat enabled: {health.get('chat', {}).get('enabled', False)}")
        
        # Test 2: Simple task submission
        print("\n[Test 2] Task submission - 'Add error handling to login endpoint'")
        response = await client.post(
            f"{base_url}/chat",
            json={
                "message": "Add error handling to the login endpoint",
                "user_id": "test-user"
            }
        )
        chat1 = response.json()
        session_id = chat1["session_id"]
        print(f"✓ Intent: {chat1['intent']}")
        print(f"✓ Confidence: {chat1['confidence']:.2f}")
        print(f"✓ Session: {session_id}")
        print(f"✓ Response: {chat1['message'][:100]}...")
        
        if chat1.get("task_id"):
            print(f"✓ Task created: {chat1['task_id']}")
        else:
            print("⚠ Clarification needed (expected for ambiguous tasks)")
        
        # Test 3: Clarification (continue conversation)
        if not chat1.get("task_id"):
            print("\n[Test 3] Clarification - 'feature-dev'")
            response = await client.post(
                f"{base_url}/chat",
                json={
                    "message": "feature-dev",
                    "session_id": session_id,
                    "user_id": "test-user"
                }
            )
            chat2 = response.json()
            print(f"✓ Intent: {chat2['intent']}")
            print(f"✓ Response: {chat2['message'][:100]}...")
            if chat2.get("task_id"):
                print(f"✓ Task created: {chat2['task_id']}")
        
        # Test 4: Status query
        print("\n[Test 4] Status query - 'What's the status of task-123?'")
        response = await client.post(
            f"{base_url}/chat",
            json={
                "message": "What's the status of task-123?",
                "user_id": "test-user"
            }
        )
        chat3 = response.json()
        print(f"✓ Intent: {chat3['intent']}")
        print(f"✓ Response: {chat3['message'][:100]}...")
        
        # Test 5: General query
        print("\n[Test 5] General query - 'What can you do?'")
        response = await client.post(
            f"{base_url}/chat",
            json={
                "message": "What can you do?",
                "user_id": "test-user"
            }
        )
        chat4 = response.json()
        print(f"✓ Intent: {chat4['intent']}")
        print(f"✓ Suggestions: {chat4.get('suggestions', [])}")
        print(f"✓ Response: {chat4['message'][:100]}...")
        
        print("\n" + "=" * 60)
        print("✅ All tests completed!")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_chat_endpoint())
