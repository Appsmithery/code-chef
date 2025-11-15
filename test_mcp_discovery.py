"""Test MCP Discovery functionality"""
import sys
import json
sys.path.insert(0, 'agents')

from _shared.mcp_discovery import get_mcp_discovery

if __name__ == "__main__":
    print("[TEST] Testing MCP Discovery...")
    
    discovery = get_mcp_discovery()
    
    print("\n[TEST] Discovering servers...")
    servers = discovery.discover_servers()
    
    print(json.dumps(servers, indent=2))
    
    print(f"\n[TEST] Summary:")
    print(f"  Total Servers: {servers.get('total_servers', 0)}")
    print(f"  Total Tools: {servers.get('total_tools', 0)}")
    
    if servers.get('servers'):
        print(f"\n[TEST] First 3 servers:")
        for server in servers['servers'][:3]:
            print(f"  - {server['name']}: {server['tool_count']} tools")
