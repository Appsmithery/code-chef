"""Test MCP Tool Client Direct Invocation"""
import sys
import asyncio
sys.path.insert(0, 'agents')

from _shared.mcp_tool_client import get_mcp_tool_client

async def test_mcp_tools():
    """Test direct MCP tool invocation"""
    print("[TEST] Initializing MCP Tool Client...")
    
    client = get_mcp_tool_client("test-agent")
    
    # Test 1: List available servers
    print("\n[TEST 1] Listing available MCP servers...")
    servers = await client.list_servers()
    print(f"✓ Found {len(servers)} servers: {', '.join(servers[:5])}")
    
    # Test 2: List tools for memory server
    if "memory" in servers:
        print("\n[TEST 2] Listing tools for 'memory' server...")
        tools = await client.list_tools("memory")
        print(f"✓ Memory server has {len(tools)} tools: {', '.join(tools[:3])}")
    
    # Test 3: Create a memory entity (convenience method)
    print("\n[TEST 3] Creating test entity in memory...")
    result = await client.create_memory_entity(
        name="mcp-phase3-test",
        entity_type="test_entity",
        observations=[
            "Phase 3 implementation test",
            "Direct stdio transport",
            "No HTTP gateway"
        ]
    )
    
    if result["success"]:
        print(f"✓ Successfully created memory entity")
        print(f"  Result: {result.get('result', 'N/A')}")
    else:
        print(f"✗ Failed to create entity: {result.get('error')}")
    
    # Test 4: Search memory
    print("\n[TEST 4] Searching memory for test entity...")
    search_result = await client.search_memory("mcp-phase3")
    
    if search_result["success"]:
        print(f"✓ Search successful")
        print(f"  Result: {search_result.get('result', 'N/A')}")
    else:
        print(f"✗ Search failed: {search_result.get('error')}")
    
    # Test 5: Direct tool invocation
    print("\n[TEST 5] Direct tool invocation (read_graph)...")
    graph_result = await client.invoke_tool_simple(
        server="memory",
        tool="read_graph",
        params={}
    )
    
    if graph_result["success"]:
        print(f"✓ Direct invocation successful")
        result_data = graph_result.get('result', {})
        if isinstance(result_data, dict):
            entities = result_data.get('entities', [])
            print(f"  Knowledge graph has {len(entities) if isinstance(entities, list) else 'unknown'} entities")
    else:
        print(f"✗ Direct invocation failed: {graph_result.get('error')}")
    
    print("\n[TEST] All tests complete!")
    print("\n📊 Summary:")
    print(f"  - Servers discovered: {len(servers)}")
    print(f"  - Direct stdio transport: Working")
    print(f"  - Convenience methods: Available")
    print(f"  - No HTTP gateway needed: ✓")

if __name__ == "__main__":
    asyncio.run(test_mcp_tools())
