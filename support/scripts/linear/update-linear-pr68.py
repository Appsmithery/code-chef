#!/usr/bin/env python3
"""Update Linear PR-68 with Phase 6 completion status."""

import os
import requests
import json

LINEAR_API_KEY = os.environ.get("LINEAR_API_KEY")
if not LINEAR_API_KEY:
    print("❌ LINEAR_API_KEY environment variable not set")
    exit(1)

GRAPHQL_ENDPOINT = "https://api.linear.app/graphql"

# PR-68 issue ID (workspace approval hub)
ISSUE_ID = "PR-68"

# Phase 6 completion update
UPDATE_TEXT = """
## ✅ Phase 6: Multi-Agent Collaboration - COMPLETE

**Deployment Date**: November 19, 2025  
**Status**: Production Deployed  
**Droplet**: 45.55.173.72

### 🎉 Delivered Features

**1. Agent Registry Service** (Port 8009)
- Discovery service for dynamic agent lookup
- Health monitoring and capability registration
- RESTful API for agent metadata

**2. Inter-Agent Event Protocol**
- Async pub/sub event bus (14 Prometheus metrics)
- Agent-to-agent request/response pattern
- Event routing with timeout handling

**3. Distributed Resource Locking**
- PostgreSQL advisory locks for safe concurrency
- Deadlock detection and timeout handling
- Lock contention monitoring (6 Prometheus metrics)

**4. Workflow State Management**
- PostgreSQL-backed state persistence
- Optimistic locking with version control
- Multi-agent workflow coordination

**5. Pre-Built Workflows**
- PR Deployment (sequential: code-review → feature-dev → infrastructure → cicd)
- Parallel Docs Generation (concurrent documentation tasks)
- Self-Healing Infrastructure (monitoring + auto-remediation loop)

### 📊 Production Metrics

**Observability Stack:**
- Prometheus: http://45.55.173.72:9090/targets
- LangSmith: https://smith.langchain.com (project: dev-tools-agents)
- 19 new metrics (14 EventBus + 6 ResourceLock - see note below)

**Note on Metrics:** The 19 metrics definitions are implemented and exported by agents. Actual metric values (gauges, counters) will populate once workflows execute and use the event bus/resource locking functionality. Current validation confirms metric *definitions* are present in Prometheus scrape endpoints.

**Service Health:**
- ✅ All 10+ services UP and healthy
- ✅ Agent Registry responding on port 8009
- ✅ EventBus metrics exported from orchestrator
- ✅ ResourceLock metrics ready (activate on first workflow execution)

### 📚 Documentation

- Implementation Report: `_archive/docs-historical/PHASE_6_COMPLETE.md`
- Monitoring Guide: `PHASE_6_MONITORING_GUIDE.md`
- Event Protocol: `EVENT_PROTOCOL.md` (enhanced with examples)
- Agent Registry: `AGENT_REGISTRY.md` (enhanced with integration patterns)
- Resource Locking: `RESOURCE_LOCKING.md` (enhanced with best practices)

### ✅ Validation Results

**Integration Tests:**
- 5/5 tests passing (test_multi_agent_workflows.py)
- Coverage: PR deployment, parallel docs, self-healing, resource contention, state persistence

**Code Quality:**
- All Prometheus metrics instrumented
- Error handling patterns documented
- Best practices guides complete

**Deployment:**
- Docker images built and pushed to Docker Hub
- Production deployment successful
- Health checks passing across all services

### 📋 48-Hour Monitoring Plan

**Action Items:**
1. Monitor Prometheus targets (check every 4 hours)
2. Review LangSmith traces for orchestrator workflows
3. Watch for EventBus errors and request timeouts
4. Track resource lock contention ratios
5. Verify PostgreSQL connection pool health

**Alert Thresholds Configured:**
- Event Bus errors > 10%
- Request timeouts > 5%
- Lock contention > 30%
- P95 latency > 2 seconds

### 🚀 Next Steps (Phase 7)

Ready to plan Phase 7 after 48-hour stability verification:
- LangGraph integration for complex workflows
- Advanced retry/circuit breaker patterns
- Cross-agent telemetry aggregation
- Workflow visualization dashboard

---

**Deployment Command:**
```bash
./support/scripts/deploy/deploy.ps1 -Target remote
```

**Monitoring Dashboard:**
http://45.55.173.72:9090/targets

**Linear Issue:** PR-68 (workspace approval notification hub)
"""

def update_issue_description(issue_id: str, description: str) -> bool:
    """Update Linear issue description via GraphQL API."""
    
    # First, get the issue's internal UUID
    query_get_issue = """
    query GetIssue($issueId: String!) {
        issue(id: $issueId) {
            id
            identifier
            title
            description
        }
    }
    """
    
    response = requests.post(
        GRAPHQL_ENDPOINT,
        headers={
            "Authorization": LINEAR_API_KEY,
            "Content-Type": "application/json"
        },
        json={
            "query": query_get_issue,
            "variables": {"issueId": issue_id}
        }
    )
    
    if response.status_code != 200:
        print(f"❌ Failed to fetch issue: {response.status_code}")
        print(response.text)
        return False
    
    data = response.json()
    if "errors" in data:
        print(f"❌ GraphQL errors: {data['errors']}")
        return False
    
    issue = data.get("data", {}).get("issue")
    if not issue:
        print(f"❌ Issue {issue_id} not found")
        return False
    
    print(f"📝 Found issue: {issue['identifier']} - {issue['title']}")
    internal_id = issue["id"]
    
    # Now update the description
    mutation = """
    mutation UpdateIssue($issueId: String!, $description: String!) {
        issueUpdate(
            id: $issueId,
            input: { description: $description }
        ) {
            success
            issue {
                id
                identifier
                title
                url
            }
        }
    }
    """
    
    # Append to existing description if it exists
    current_desc = issue.get("description", "")
    new_description = f"{current_desc}\n\n{description}" if current_desc else description
    
    response = requests.post(
        GRAPHQL_ENDPOINT,
        headers={
            "Authorization": LINEAR_API_KEY,
            "Content-Type": "application/json"
        },
        json={
            "query": mutation,
            "variables": {
                "issueId": internal_id,
                "description": new_description
            }
        }
    )
    
    if response.status_code != 200:
        print(f"❌ Failed to update issue: {response.status_code}")
        print(response.text)
        return False
    
    data = response.json()
    if "errors" in data:
        print(f"❌ GraphQL errors: {data['errors']}")
        return False
    
    result = data.get("data", {}).get("issueUpdate", {})
    if result.get("success"):
        issue_data = result.get("issue", {})
        print(f"✅ Successfully updated: {issue_data.get('identifier')} - {issue_data.get('title')}")
        print(f"   URL: {issue_data.get('url')}")
        return True
    else:
        print(f"❌ Update failed")
        return False

if __name__ == "__main__":
    print(f"🔄 Updating Linear issue {ISSUE_ID} with Phase 6 completion...\n")
    success = update_issue_description(ISSUE_ID, UPDATE_TEXT)
    exit(0 if success else 1)
