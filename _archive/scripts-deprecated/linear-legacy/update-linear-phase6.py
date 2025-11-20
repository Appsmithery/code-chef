#!/usr/bin/env python3
"""Update Linear AI DevOps Agent Platform project with Phase 6 completion.

This script updates the PROJECT roadmap, NOT PR-68 (which is for approval requests only).

Project: AI DevOps Agent Platform
Project ID: 78b3b839d36b
URL: https://linear.app/project-roadmaps/project/ai-devops-agent-platform-78b3b839d36b
"""

import os
import requests
import json

LINEAR_API_KEY = os.environ.get("LINEAR_API_KEY")
if not LINEAR_API_KEY:
    print("❌ LINEAR_API_KEY environment variable not set")
    exit(1)

GRAPHQL_ENDPOINT = "https://api.linear.app/graphql"

# Project information
PROJECT_ID = "b21cbaa1-9f09-40f4-b62a-73e0f86dd501"  # AI DevOps Agent Platform (full UUID)
SLUG_ID = "78b3b839d36b"  # Short slug ID for URLs
TEAM_ID = "f5b610be-ac34-4983-918b-2c9d00aa9b7a"  # Project Roadmaps (PR)

# Phase 6 issue identifier (you'll need to find this in Linear)
# We'll search for it by title if not provided
PHASE_6_TITLE = "Phase 6: Multi-Agent Collaboration"

def search_phase_6_issue():
    """Search for Phase 6 issue in the project."""
    query = """
    query SearchIssue($projectId: String!) {
        project(id: $projectId) {
            id
            name
            issues {
                nodes {
                    id
                    identifier
                    title
                    description
                    state {
                        name
                        type
                    }
                }
            }
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
            "query": query,
            "variables": {"projectId": PROJECT_ID}
        }
    )
    
    if response.status_code != 200:
        print(f"❌ Failed to search project: {response.status_code}")
        print(response.text)
        return None
    
    data = response.json()
    if "errors" in data:
        print(f"❌ GraphQL errors: {data['errors']}")
        return None
    
    project = data.get("data", {}).get("project")
    if not project:
        print(f"❌ Project {PROJECT_ID} not found")
        return None
    
    print(f"📁 Found project: {project['name']}")
    
    # Search for Phase 6 issue
    issues = project.get("issues", {}).get("nodes", [])
    for issue in issues:
        if PHASE_6_TITLE in issue.get("title", ""):
            print(f"✅ Found Phase 6 issue: {issue['identifier']} - {issue['title']}")
            return issue
    
    print(f"⚠️  Phase 6 issue not found in project. Creating new issue...")
    return None

def create_phase_6_issue():
    """Create a new Phase 6 issue in the project."""
    mutation = """
    mutation CreateIssue($teamId: String!, $projectId: String!, $title: String!, $description: String!) {
        issueCreate(
            input: {
                teamId: $teamId
                projectId: $projectId
                title: $title
                description: $description
                priority: 1
            }
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
    
    description = "Multi-agent coordination layer with event bus, resource locking, and workflow orchestration."
    
    response = requests.post(
        GRAPHQL_ENDPOINT,
        headers={
            "Authorization": LINEAR_API_KEY,
            "Content-Type": "application/json"
        },
        json={
            "query": mutation,
            "variables": {
                "teamId": TEAM_ID,
                "projectId": PROJECT_ID,
                "title": PHASE_6_TITLE,
                "description": description
            }
        }
    )
    
    if response.status_code != 200:
        print(f"❌ Failed to create issue: {response.status_code}")
        print(response.text)
        return None
    
    data = response.json()
    if "errors" in data:
        print(f"❌ GraphQL errors: {data['errors']}")
        return None
    
    result = data.get("data", {}).get("issueCreate", {})
    if result.get("success"):
        issue_data = result.get("issue", {})
        print(f"✅ Created issue: {issue_data.get('identifier')} - {issue_data.get('title')}")
        print(f"   URL: {issue_data.get('url')}")
        return issue_data
    
    return None

def update_phase_6_completion(issue_id: str):
    """Update Phase 6 issue with completion details."""
    
    completion_text = """
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
- Async pub/sub event bus with 8 Prometheus metrics
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
- 19 metrics across EventBus and ResourceLockManager

**Service Health:**
- ✅ All 10+ services UP and healthy
- ✅ Agent Registry responding on port 8009
- ✅ EventBus metrics exported from orchestrator
- ✅ ResourceLock metrics ready (activate on workflow execution)

### 📚 Documentation

- Implementation Report: `support/docs/PHASE_6_COMPLETE.md`
- Monitoring Guide: `support/docs/PHASE_6_MONITORING_GUIDE.md`
- Event Protocol: `support/docs/EVENT_PROTOCOL.md`
- Agent Registry: `support/docs/AGENT_REGISTRY.md`
- Resource Locking: `support/docs/RESOURCE_LOCKING.md`

### ✅ Validation Results

**Integration Tests:**
- 5/5 tests passing (test_multi_agent_workflows.py)
- Coverage: PR deployment, parallel docs, self-healing, resource contention, state persistence

**Deployment:**
- Docker images built and pushed to Docker Hub
- Production deployment successful
- Health checks passing across all services

### 📋 48-Hour Monitoring Plan

**Monitoring Dashboard**: http://45.55.173.72:9090/targets

**Key Metrics:**
- Event bus throughput and latency
- Resource lock contention ratios
- Agent request timeouts
- LangSmith trace analysis

### 🚀 Next Steps (Phase 7)

Ready for Phase 7 planning after 48-hour stability verification:
- LangGraph integration for complex workflows
- Advanced retry/circuit breaker patterns
- Cross-agent telemetry aggregation
- Workflow visualization dashboard

---

**GitHub Repository**: https://github.com/Appsmithery/Dev-Tools  
**Linear Project**: https://linear.app/project-roadmaps/project/ai-devops-agent-platform-78b3b839d36b
"""
    
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
    
    response = requests.post(
        GRAPHQL_ENDPOINT,
        headers={
            "Authorization": LINEAR_API_KEY,
            "Content-Type": "application/json"
        },
        json={
            "query": mutation,
            "variables": {
                "issueId": issue_id,
                "description": completion_text
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
    
    return False

if __name__ == "__main__":
    print(f"🔄 Updating AI DevOps Agent Platform project with Phase 6 completion...\n")
    print(f"📁 Project UUID: {PROJECT_ID}")
    print(f"🔗 URL: https://linear.app/project-roadmaps/project/ai-devops-agent-platform-{SLUG_ID}\n")
    
    # Search for existing Phase 6 issue
    issue = search_phase_6_issue()
    
    if not issue:
        # Create new issue if not found
        issue = create_phase_6_issue()
        if not issue:
            print("❌ Failed to create Phase 6 issue")
            exit(1)
    
    # Update issue with completion details
    success = update_phase_6_completion(issue["id"])
    
    if success:
        print("\n✨ Phase 6 completion successfully recorded in Linear project!")
        exit(0)
    else:
        print("\n❌ Failed to update Phase 6 issue")
        exit(1)
