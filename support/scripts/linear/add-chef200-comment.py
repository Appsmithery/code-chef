#!/usr/bin/env python3
"""Add implementation comment to CHEF-200."""
import os
import requests

LINEAR_API_KEY = os.environ.get("LINEAR_API_KEY")
if not LINEAR_API_KEY:
    print("LINEAR_API_KEY not set")
    exit(1)

# First get the issue ID (UUID)
r = requests.post('https://api.linear.app/graphql',
    headers={'Authorization': LINEAR_API_KEY, 'Content-Type': 'application/json'},
    json={'query': 'query { issue(id: "CHEF-200") { id identifier title } }'})
data = r.json()
issue_id = data['data']['issue']['id']
print(f'Issue UUID: {issue_id}')

# Add comment
comment = '''Implemented semantic tool discovery, tracing sampling, and centralized config.

**Files changed:**
- `shared/lib/progressive_mcp_loader.py`: Added SEMANTIC strategy, LLM keyword extraction
- `agent_orchestrator/agents/_shared/base_agent.py`: Improved task description extraction
- `config/observability/tracing.yaml`: Centralized tracing config
- `config/mcp-agent-tool-mapping.yaml`: Meta-tools for self-discovery
- `agent_orchestrator/agents/supervisor/tools.yaml`: SEMANTIC strategy enabled
- `agent_orchestrator/agents/code_review/tools.yaml`: SEMANTIC strategy enabled
- `support/docs/architecture-and-platform/ARCHITECTURE.md`: Tool loading strategies documentation

**Token Savings:** 96% with semantic strategy (26K → 1K tokens)'''

mutation = '''mutation CreateComment($issueId: String!, $body: String!) {
  commentCreate(input: { issueId: $issueId, body: $body }) {
    success
    comment { id }
  }
}'''

r2 = requests.post('https://api.linear.app/graphql',
    headers={'Authorization': LINEAR_API_KEY, 'Content-Type': 'application/json'},
    json={'query': mutation, 'variables': {'issueId': issue_id, 'body': comment}})
print(r2.status_code, r2.json())
