#!/usr/bin/env python3
"""Test progressive MCP tool discovery"""
import sys
sys.path.insert(0, '/opt/code-chef')

from shared.lib.progressive_mcp_loader import get_progressive_loader, ToolLoadingStrategy

def test_tool_discovery():
    loader = get_progressive_loader()
    
    test_descriptions = [
        "Write Python code to sort a list",
        "Create a Docker container for a web application",
        "Set up GitHub Actions CI/CD pipeline"
    ]
    
    for desc in test_descriptions:
        print(f"\n{'='*60}")
        print(f"Task: {desc}")
        print(f"{'='*60}")
        
        # Test MINIMAL strategy
        tools = loader.get_tools_for_task(desc, strategy=ToolLoadingStrategy.MINIMAL)
        stats = loader.get_tool_usage_stats(tools)
        
        print(f"\nStrategy: MINIMAL")
        print(f"  Toolsets discovered: {len(tools)}")
        print(f"  Total tools loaded: {stats['loaded_tools']} / {stats['total_tools']}")
        print(f"  Token savings: {stats['savings_percent']}%")
        
        for toolset in tools:
            print(f"\n  Server: {toolset.server_name} ({toolset.priority})")
            print(f"    Tools: {', '.join([t.name for t in toolset.tools[:5]])}")
            if len(toolset.tools) > 5:
                print(f"    ... and {len(toolset.tools) - 5} more")
        
        # Show formatted context sample
        formatted = loader.format_tools_for_llm(tools)
        print(f"\n  Formatted context length: {len(formatted)} chars")
        print(f"\n  Sample (first 300 chars):")
        print(f"  {formatted[:300]}...")

if __name__ == "__main__":
    test_tool_discovery()
