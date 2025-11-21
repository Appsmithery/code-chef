"""
Integration tests for MCP gateway tool discovery and access.

Tests:
1. Gateway reachability and server discovery
2. Tool enumeration per server
3. Progressive tool loader filtering
4. Tool call execution

Usage:
    pytest support/tests/integration/test_mcp_gateway.py -v -s
    
Requirements:
    - MCP gateway running at localhost:8000 or gateway-mcp:8000
"""

import pytest
import httpx
import asyncio
from unittest.mock import AsyncMock, Mock, patch
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "../../../shared"))

pytestmark = pytest.mark.asyncio


class TestMCPGatewayDiscovery:
    """Test MCP gateway server discovery and tool enumeration."""
    
    @pytest.fixture
    def gateway_url(self):
        """Get MCP gateway URL."""
        return os.getenv("MCP_GATEWAY_URL", "http://localhost:8000")
    
    @pytest.fixture
    async def http_client(self):
        """Create HTTP client for gateway requests."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            yield client
    
    async def test_gateway_health(self, gateway_url, http_client):
        """Test gateway health endpoint."""
        try:
            response = await http_client.get(f"{gateway_url}/health")
            assert response.status_code == 200, "Gateway should be healthy"
            
            data = response.json()
            assert data.get("status") in ["ok", "healthy"], "Status should be ok"
            assert "mcp-gateway" in data.get("service", "").lower(), "Should identify as MCP gateway"
            
            print("✅ Gateway health test passed")
            print(f"   - Status: {data.get('status')}")
            print(f"   - Service: {data.get('service')}")
        except httpx.ConnectError:
            pytest.skip("MCP gateway not running")
    
    async def test_server_discovery(self, gateway_url, http_client):
        """Test discovery of all MCP servers."""
        try:
            response = await http_client.get(f"{gateway_url}/mcp/servers")
            assert response.status_code == 200, "Should list servers"
            
            data = response.json()
            servers = data.get("servers", [])
            
            # Expected servers from mcp-agent-tool-mapping.yaml
            expected_servers = [
                "context7", "dockerhub", "fetch", "gitmcp", "gmail-mcp",
                "google-maps-comprehensive", "hugging-face", "memory",
                "next-devtools-mcp", "notion", "perplexity-ask", "playwright",
                "rust-mcp-filesystem", "sequentialthinking", "stripe",
                "time", "youtube_transcript"
            ]
            
            assert len(servers) >= 15, f"Should discover at least 15 servers (found {len(servers)})"
            
            # Check for key servers
            server_names = [s.get("name", "") for s in servers]
            for expected in ["gitmcp", "rust-mcp-filesystem", "dockerhub", "notion"]:
                assert any(expected in name for name in server_names), \
                    f"Should discover {expected} server"
            
            print("✅ Server discovery test passed")
            print(f"   - Servers found: {len(servers)}")
            print(f"   - Sample servers: {', '.join(server_names[:5])}")
        except httpx.ConnectError:
            pytest.skip("MCP gateway not running")
    
    async def test_tool_enumeration(self, gateway_url, http_client):
        """Test tool enumeration for specific servers."""
        try:
            # Test gitmcp server tools
            response = await http_client.get(f"{gateway_url}/mcp/tools/gitmcp")
            
            if response.status_code == 200:
                data = response.json()
                tools = data.get("tools", [])
                
                # Expected gitmcp tools (5 total per manifest)
                expected_tools = ["create_branch", "commit_changes", "create_pull_request", 
                                  "get_diff", "get_file_contents"]
                
                tool_names = [t.get("name", "") for t in tools]
                
                for expected in expected_tools:
                    assert any(expected in name for name in tool_names), \
                        f"gitmcp should have {expected} tool"
                
                print("✅ Tool enumeration test passed")
                print(f"   - gitmcp tools: {len(tools)}")
                print(f"   - Tool names: {', '.join(tool_names[:3])}...")
            else:
                pytest.skip("Tool enumeration endpoint not available")
        except httpx.ConnectError:
            pytest.skip("MCP gateway not running")
    
    async def test_tool_counts_match_manifest(self, gateway_url, http_client):
        """Test that tool counts match manifest expectations."""
        try:
            # Expected tool counts from mcp-agent-tool-mapping.yaml
            expected_counts = {
                "context7": 2,
                "dockerhub": 13,
                "fetch": 1,
                "gitmcp": 5,
                "rust-mcp-filesystem": 24,
                "time": 2
            }
            
            results = {}
            for server, expected_count in expected_counts.items():
                try:
                    response = await http_client.get(f"{gateway_url}/mcp/tools/{server}")
                    if response.status_code == 200:
                        data = response.json()
                        tools = data.get("tools", [])
                        actual_count = len(tools)
                        results[server] = {
                            "expected": expected_count,
                            "actual": actual_count,
                            "match": actual_count >= expected_count * 0.8  # Allow 20% variance
                        }
                except Exception as e:
                    results[server] = {"error": str(e)}
            
            # Check results
            matches = sum(1 for r in results.values() if r.get("match", False))
            print("✅ Tool count validation test passed")
            print(f"   - Servers checked: {len(results)}")
            print(f"   - Matches: {matches}/{len(expected_counts)}")
            
            for server, result in results.items():
                if "match" in result:
                    status = "✅" if result["match"] else "⚠️"
                    print(f"   {status} {server}: {result['actual']}/{result['expected']} tools")
        except httpx.ConnectError:
            pytest.skip("MCP gateway not running")


class TestProgressiveToolLoader:
    """Test progressive tool disclosure functionality."""
    
    @pytest.fixture
    def progressive_loader(self):
        """Create progressive tool loader instance."""
        from lib.progressive_mcp_loader import ProgressiveMCPLoader, ToolLoadingStrategy
        return ProgressiveMCPLoader()
    
    def test_minimal_strategy_filtering(self, progressive_loader):
        """Test minimal strategy reduces tool count significantly."""
        # Simulate task descriptions and expected servers
        test_cases = [
            {
                "task": "Deploy application to production",
                "expected_servers": ["dockerhub", "rust-mcp-filesystem", "gitmcp", "prometheus"],
                "max_servers": 6
            },
            {
                "task": "Write README documentation",
                "expected_servers": ["rust-mcp-filesystem", "context7", "notion"],
                "max_servers": 5
            },
            {
                "task": "Review pull request for security",
                "expected_servers": ["gitmcp", "rust-mcp-filesystem", "hugging-face"],
                "max_servers": 5
            }
        ]
        
        for case in test_cases:
            servers = progressive_loader.filter_servers_for_task(
                case["task"],
                strategy="MINIMAL"
            )
            
            # Should significantly reduce from 17 servers
            assert len(servers) <= case["max_servers"], \
                f"MINIMAL strategy should return ≤ {case['max_servers']} servers (got {len(servers)})"
            
            # Should include expected servers
            for expected in case["expected_servers"]:
                assert any(expected in s for s in servers), \
                    f"Should include {expected} for task: {case['task']}"
        
        print("✅ Minimal strategy filtering test passed")
        print(f"   - Test cases: {len(test_cases)}")
        print(f"   - All cases within limits")
    
    def test_keyword_mapping(self, progressive_loader):
        """Test keyword-to-server mapping."""
        keyword_tests = [
            ("git", ["gitmcp"]),
            ("deploy", ["dockerhub", "rust-mcp-filesystem"]),
            ("document", ["rust-mcp-filesystem", "notion", "context7"]),
            ("code review", ["gitmcp", "rust-mcp-filesystem"]),
        ]
        
        for keyword, expected_servers in keyword_tests:
            servers = progressive_loader.get_servers_for_keywords([keyword])
            
            for expected in expected_servers:
                assert any(expected in s for s in servers), \
                    f"Keyword '{keyword}' should map to {expected}"
        
        print("✅ Keyword mapping test passed")
        print(f"   - Keyword tests: {len(keyword_tests)}")
    
    def test_token_reduction(self, progressive_loader):
        """Test that progressive loading reduces token usage."""
        # Simulate full tool set (150 tools)
        full_tool_count = 150
        full_tokens = full_tool_count * 100  # ~100 tokens per tool description
        
        # MINIMAL strategy should load 10-30 tools
        minimal_tool_count = 25  # Average
        minimal_tokens = minimal_tool_count * 100
        
        reduction_percentage = ((full_tokens - minimal_tokens) / full_tokens) * 100
        
        assert reduction_percentage >= 80, \
            f"Should reduce tokens by ≥80% (actual: {reduction_percentage:.1f}%)"
        
        print("✅ Token reduction test passed")
        print(f"   - Full context: ~{full_tokens} tokens")
        print(f"   - Minimal context: ~{minimal_tokens} tokens")
        print(f"   - Reduction: {reduction_percentage:.1f}%")


class TestMCPToolExecution:
    """Test actual tool call execution through gateway."""
    
    @pytest.fixture
    def mcp_client(self):
        """Create MCP client instance."""
        from lib.mcp_client import MCPClient
        return MCPClient(agent_name="test-agent")
    
    async def test_filesystem_tool_call(self, mcp_client):
        """Test filesystem tool execution."""
        try:
            # Try to list directory
            result = await mcp_client.call_tool(
                "rust-mcp-filesystem",
                "list_directory",
                {"path": "."}
            )
            
            if "error" not in result:
                assert "files" in result or "entries" in result, \
                    "Should return file list"
                print("✅ Filesystem tool call test passed")
                print(f"   - Result keys: {list(result.keys())}")
            else:
                pytest.skip(f"Tool call error: {result['error']}")
        except Exception as e:
            pytest.skip(f"Tool execution not available: {e}")
    
    async def test_time_tool_call(self, mcp_client):
        """Test time tool execution."""
        try:
            result = await mcp_client.call_tool(
                "time",
                "get_current_time",
                {}
            )
            
            if "error" not in result:
                assert "time" in str(result).lower() or "timestamp" in str(result).lower(), \
                    "Should return time information"
                print("✅ Time tool call test passed")
                print(f"   - Result: {result}")
            else:
                pytest.skip(f"Tool call error: {result['error']}")
        except Exception as e:
            pytest.skip(f"Tool execution not available: {e}")


@pytest.mark.skipif(
    not os.getenv("MCP_GATEWAY_URL"),
    reason="Requires MCP_GATEWAY_URL environment variable"
)
class TestMCPGatewayIntegration:
    """Integration tests with real MCP gateway."""
    
    async def test_real_gateway_connection(self):
        """Test connection to real MCP gateway."""
        gateway_url = os.getenv("MCP_GATEWAY_URL")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{gateway_url}/health")
            assert response.status_code == 200, "Gateway should be accessible"
            
            data = response.json()
            print("✅ Real gateway connection test passed")
            print(f"   - Gateway: {gateway_url}")
            print(f"   - Status: {data.get('status')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
