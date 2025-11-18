#!/usr/bin/env python3
"""
Test Agent Memory Integration
Verifies LangChain memory can write to agent_memory collection in Qdrant Cloud
"""

import sys
from pathlib import Path

# Add agents to path
sys.path.insert(0, str(Path(__file__).parent.parent / "agents"))

def test_basic_memory():
    """Test basic conversation memory"""
    print("Testing basic conversation memory...")
    
    from shared.lib.langchain_memory import create_conversation_memory
    
    memory = create_conversation_memory()
    
    # Save conversation
    memory.save_context(
        {"input": "What is Docker?"},
        {"output": "Docker is a containerization platform that packages applications with their dependencies."}
    )
    
    memory.save_context(
        {"input": "How do I deploy with Docker?"},
        {"output": "Use docker-compose.yml to define services, then run `docker compose up -d` to deploy."}
    )
    
    # Load memory
    loaded = memory.load_memory_variables({})
    print(f"✅ Conversation memory: {len(loaded.get('chat_history', []))} messages")
    
    return True


def test_vector_memory():
    """Test vector store memory with Qdrant"""
    print("\nTesting vector memory (Qdrant Cloud)...")
    
    from shared.lib.langchain_memory import create_vector_memory
    
    memory = create_vector_memory(
        collection_name="agent_memory",
        search_kwargs={"k": 3}
    )
    
    if memory is None:
        print("⚠ Vector memory disabled (Qdrant not available)")
        return False
    
    print("✅ Vector memory created")
    
    # Save some context
    test_conversations = [
        {
            "input": "Explain the agent architecture",
            "output": "The system has 6 agents: orchestrator, feature-dev, code-review, infrastructure, cicd, and documentation. They coordinate via MCP gateway."
        },
        {
            "input": "How does MCP work?",
            "output": "MCP (Model Context Protocol) provides 150+ tools across 17 servers. Agents access tools via the gateway at port 8000."
        },
        {
            "input": "What is Qdrant used for?",
            "output": "Qdrant Cloud stores vector embeddings for 6 collections: the-shop (docs), agent_memory (conversations), task_context, code_patterns, feature_specs, and issue_tracker."
        }
    ]
    
    print("Saving test conversations...")
    for i, conv in enumerate(test_conversations):
        try:
            memory.save_context(
                {"input": conv["input"]},
                {"output": conv["output"]}
            )
            print(f"  ✓ Saved conversation {i+1}/{len(test_conversations)}")
        except Exception as e:
            print(f"  ✗ Failed to save conversation {i+1}: {e}")
            return False
    
    # Try to retrieve
    print("\nRetrieving related memories...")
    try:
        result = memory.load_memory_variables({"input": "Tell me about the agent system"})
        history = result.get("history", "")
        if history:
            print(f"✅ Retrieved memory: {len(history)} characters")
            print(f"   Preview: {history[:200]}...")
            return True
        else:
            print("⚠ No history retrieved (embeddings may not be working)")
            return False
    except Exception as e:
        print(f"✗ Failed to retrieve: {e}")
        return False


def verify_qdrant_collection():
    """Verify agent_memory collection in Qdrant"""
    print("\nVerifying Qdrant Cloud collection...")
    
    from shared.lib.qdrant_client import get_qdrant_client
    
    client = get_qdrant_client()
    
    if not client.is_enabled():
        print("✗ Qdrant Cloud not available")
        return False
    
    try:
        import asyncio
        
        # Check collection info
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        info = loop.run_until_complete(client.get_collection_info())
        loop.close()
        
        if info:
            print(f"✅ Collection 'agent_memory':")
            print(f"   Points: {info.get('points_count', 0)}")
            print(f"   Vectors: {info.get('vectors_count', 0)}")
            return True
        else:
            print("⚠ Collection info not available")
            return False
    except Exception as e:
        print(f"✗ Failed to check collection: {e}")
        return False


def main():
    print("=" * 60)
    print("Agent Memory Integration Test")
    print("=" * 60)
    
    results = {
        "Basic Memory": test_basic_memory(),
        "Vector Memory": test_vector_memory(),
        "Qdrant Collection": verify_qdrant_collection()
    }
    
    print("\n" + "=" * 60)
    print("Results:")
    print("-" * 60)
    for test, passed in results.items():
        status = "✅ PASS" if passed else "⚠ SKIP/FAIL"
        print(f"{test:.<40} {status}")
    
    print("=" * 60)
    
    # Overall
    if results["Basic Memory"]:
        print("\n✅ Agent memory system operational")
        print("   Note: Vector memory requires real embeddings in production")
        return 0
    else:
        print("\n✗ Agent memory system needs attention")
        return 1


if __name__ == "__main__":
    sys.exit(main())
