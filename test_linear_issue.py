import asyncio
import os
import sys
sys.path.insert(0, '/app')

from lib.linear_workspace_client import LinearWorkspaceClient

async def test():
    client = LinearWorkspaceClient()
    
    # First, get team info
    print("Fetching teams...")
    teams_query = '''{ teams { nodes { id key name } } }'''
    teams = await client._execute_query(teams_query)
    print('Teams:', teams)
    
    # Try to get DEV-68
    print("\nFetching DEV-68...")
    issue = await client.get_issue_by_identifier('DEV-68')
    print('DEV-68:', issue)

asyncio.run(test())
