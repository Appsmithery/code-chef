# Frontend Integration Guide

**Frontend URL**: https://theshop.appsmithery.co/  
**Backend Services**: Dev-Tools Agents on DigitalOcean (45.55.173.72)  
**Integration Method**: MCP Central Gateway + Direct REST API

---

## 🏗️ Architecture Overview

```
Frontend (theshop.appsmithery.co)
    ↓
MCP Central Gateway (Port 8000)
    ↓
DevTools Orchestrator (Port 8001)
    ↓
┌─────────────┬──────────────┬──────────────┐
│ Feature-Dev │ Code-Review  │ Infrastructure│
│   :8002     │    :8003     │     :8004    │
└─────────────┴──────────────┴──────────────┘
```

---

## 🔌 Integration Methods

### Method 1: Direct REST API (Recommended for MVP)

**Pros**: Simple, no additional infrastructure, works immediately  
**Cons**: Requires CORS configuration, no centralized auth

#### Frontend API Client

```typescript
// src/services/devtools-api.ts
const DEVTOOLS_BASE_URL = "http://45.55.173.72:8001";

export class DevToolsAPI {
  private baseURL: string;

  constructor(baseURL: string = DEVTOOLS_BASE_URL) {
    this.baseURL = baseURL;
  }

  /**
   * Create a new development task
   */
  async createTask(
    description: string,
    priority: "low" | "medium" | "high" = "medium"
  ) {
    const response = await fetch(`${this.baseURL}/orchestrate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ description, priority }),
    });

    if (!response.ok) {
      throw new Error(`Failed to create task: ${response.statusText}`);
    }

    return response.json(); // Returns { task_id, assigned_agents, status }
  }

  /**
   * Execute a task workflow
   */
  async executeTask(taskId: string) {
    const response = await fetch(`${this.baseURL}/execute/${taskId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    });

    if (!response.ok) {
      throw new Error(`Failed to execute task: ${response.statusText}`);
    }

    return response.json(); // Returns { status, execution_results }
  }

  /**
   * Get task status
   */
  async getTaskStatus(taskId: string) {
    const response = await fetch(`${this.baseURL}/tasks/${taskId}`);

    if (!response.ok) {
      throw new Error(`Failed to get task status: ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * Direct agent call (bypass orchestrator)
   */
  async callAgent(agentPort: number, endpoint: string, data: any) {
    const response = await fetch(
      `http://45.55.173.72:${agentPort}/${endpoint}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      }
    );

    if (!response.ok) {
      throw new Error(`Agent call failed: ${response.statusText}`);
    }

    return response.json();
  }
}

// Export singleton instance
export const devToolsAPI = new DevToolsAPI();
```

#### React Component Example

```tsx
// src/components/DevToolsPanel.tsx
import React, { useState } from "react";
import { devToolsAPI } from "../services/devtools-api";

export const DevToolsPanel: React.FC = () => {
  const [taskDescription, setTaskDescription] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);

  const handleSubmit = async () => {
    setLoading(true);
    try {
      // Step 1: Create task
      const task = await devToolsAPI.createTask(taskDescription, "high");
      console.log("Task created:", task.task_id);

      // Step 2: Execute workflow
      const execution = await devToolsAPI.executeTask(task.task_id);
      setResult(execution);
    } catch (error) {
      console.error("DevTools error:", error);
      alert("Failed to execute task");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="devtools-panel">
      <h2>🤖 AI Development Assistant</h2>

      <textarea
        value={taskDescription}
        onChange={(e) => setTaskDescription(e.target.value)}
        placeholder="Describe what you want to build..."
        rows={4}
      />

      <button onClick={handleSubmit} disabled={loading}>
        {loading ? "Processing..." : "Generate Code"}
      </button>

      {result && (
        <div className="results">
          <h3>Status: {result.status}</h3>
          {result.execution_results?.map((r: any, i: number) => (
            <div key={i} className="agent-result">
              <strong>{r.agent}:</strong> {r.status}
              {r.result && <pre>{JSON.stringify(r.result, null, 2)}</pre>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
```

---

### Method 2: Via MCP Central Gateway (Production Ready)

**Pros**: Centralized auth, rate limiting, observability, type-safe APIs  
**Cons**: Requires MCP Gateway deployment and configuration

#### Update MCP Gateway Configuration

Add Dev-Tools agents as MCP servers in your gateway:

```typescript
// central-mcp-gateway/app/src/config/servers.ts
export const MCP_SERVERS = [
  // ... existing servers ...
  {
    name: "devtools-orchestrator",
    url: "http://45.55.173.72:8001",
    type: "rest",
    tools: [
      { name: "orchestrate", endpoint: "/orchestrate", method: "POST" },
      { name: "execute", endpoint: "/execute/:taskId", method: "POST" },
      { name: "get_task", endpoint: "/tasks/:taskId", method: "GET" },
    ],
  },
  {
    name: "devtools-feature-dev",
    url: "http://45.55.173.72:8002",
    type: "rest",
    tools: [{ name: "implement", endpoint: "/implement", method: "POST" }],
  },
  {
    name: "devtools-code-review",
    url: "http://45.55.173.72:8003",
    type: "rest",
    tools: [{ name: "review", endpoint: "/review", method: "POST" }],
  },
];
```

#### Frontend Integration via Gateway

```typescript
// src/services/mcp-gateway-api.ts
const GATEWAY_URL = "https://your-mcp-gateway.com";

export class MCPGatewayAPI {
  private token: string | null = null;

  async authenticate(githubToken: string) {
    const response = await fetch(`${GATEWAY_URL}/oauth/github/authorize`, {
      headers: { Authorization: `Bearer ${githubToken}` },
    });
    const data = await response.json();
    this.token = data.token;
  }

  async invokeDevTools(toolName: string, params: any) {
    const response = await fetch(
      `${GATEWAY_URL}/mcp/servers/devtools-orchestrator/${toolName}`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${this.token}`,
        },
        body: JSON.stringify(params),
      }
    );

    return response.json();
  }
}
```

---

## 🔒 CORS Configuration

Enable CORS on your DigitalOcean droplet to allow frontend access:

### Update Orchestrator CORS

```python
# /opt/Dev-Tools/agents/orchestrator/main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://theshop.appsmithery.co",
        "http://localhost:3000",  # Development
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Apply to All Agents

Run this command on the droplet to update all agents:

```bash
ssh root@45.55.173.72 << 'EOF'
cd /opt/Dev-Tools

# Add CORS to all agent main.py files
for agent in agents/*/main.py; do
  if ! grep -q "CORSMiddleware" "$agent"; then
    sed -i '/from fastapi import/a from fastapi.middleware.cors import CORSMiddleware' "$agent"
    sed -i '/app = FastAPI(/a \\napp.add_middleware(\n    CORSMiddleware,\n    allow_origins=["https://theshop.appsmithery.co", "http://localhost:3000"],\n    allow_credentials=True,\n    allow_methods=["*"],\n    allow_headers=["*"],\n)' "$agent"
  fi
done

# Restart services
cd compose
docker compose restart

echo "✅ CORS enabled for all agents"
EOF
```

---

## 🚀 Quick Start Integration

### 1. Test Backend Connectivity

```bash
curl http://45.55.173.72:8001/health
# Should return: {"status":"ok","service":"orchestrator"}
```

### 2. Add API Client to Frontend

```bash
cd /path/to/theshop.appsmithery.co
mkdir -p src/services
# Copy the devtools-api.ts code above
```

### 3. Install in Your App

```tsx
// src/App.tsx or wherever you want the integration
import { DevToolsPanel } from "./components/DevToolsPanel";

function App() {
  return (
    <div>
      {/* Your existing app */}
      <DevToolsPanel />
    </div>
  );
}
```

### 4. Test End-to-End

```typescript
// Test in browser console
const api = new DevToolsAPI("http://45.55.173.72:8001");
const task = await api.createTask(
  "Create a login page with email and password"
);
console.log("Task ID:", task.task_id);

const result = await api.executeTask(task.task_id);
console.log("Result:", result);
```

---

## 📊 Available Endpoints

### Orchestrator (Port 8001)

- `POST /orchestrate` - Create task
- `POST /execute/:taskId` - Execute workflow
- `GET /tasks/:taskId` - Get task status
- `GET /health` - Health check

### Feature-Dev (Port 8002)

- `POST /implement` - Generate code
- `GET /health` - Health check

### Code-Review (Port 8003)

- `POST /review` - Review code
- `GET /health` - Health check

### Infrastructure (Port 8004)

- `POST /generate` - Generate IaC
- `GET /health` - Health check

### CI/CD (Port 8005)

- `POST /configure` - Configure pipeline
- `GET /health` - Health check

### Documentation (Port 8006)

- `POST /generate-docs` - Generate docs
- `GET /health` - Health check

### RAG Context (Port 8007)

- `POST /search` - Semantic code search
- `GET /health` - Health check

### State Persistence (Port 8008)

- `GET /tasks` - List all tasks
- `POST /init` - Initialize database
- `GET /health` - Health check

---

## 🔐 Security Considerations

### For Production:

1. **Enable HTTPS**: Use Caddy or nginx to add SSL termination
2. **Add API Keys**: Require `X-API-Key` header for authentication
3. **Rate Limiting**: Already built-in (1000 req/min per agent)
4. **IP Whitelist**: Restrict access to your frontend IP only

```bash
# On droplet, update firewall to whitelist only your frontend IP
ssh root@45.55.173.72
ufw delete allow 8000:8008/tcp
ufw allow from YOUR_FRONTEND_IP to any port 8000:8008 proto tcp
ufw reload
```

---

## 🐛 Troubleshooting

### CORS Errors

- Check browser console for specific CORS error
- Verify `allow_origins` includes your frontend URL
- Restart agents after CORS changes

### Connection Timeout

- Verify firewall allows traffic: `ufw status`
- Check service status: `docker compose ps`
- Test from curl first: `curl http://45.55.173.72:8001/health`

### Task Execution Fails

- Check agent logs: `docker compose logs orchestrator`
- Verify all agents are running: `docker compose ps`
- Test individual agents directly

---

## 📝 Next Steps

1. **Test Direct API Integration** (Quickest path to working integration)
2. **Add CORS** to agents
3. **Implement Frontend UI** using the React component example
4. **Add MCP Gateway** for production (optional but recommended)
5. **Enable HTTPS** with Caddy/nginx
6. **Add Authentication** and API keys

---

## 🎯 Example Full Workflow

```typescript
// Complete workflow example
async function buildFeature() {
  const api = new DevToolsAPI();

  // 1. Create task
  const task = await api.createTask(
    "Build a user profile page with avatar upload and bio editing",
    "high"
  );

  // 2. Execute workflow (orchestrator → feature-dev → code-review)
  const execution = await api.executeTask(task.task_id);

  // 3. Get generated code
  const featureResult = execution.execution_results.find(
    (r) => r.agent === "feature-dev"
  );

  console.log("Generated Code:", featureResult.result);

  // 4. Get code review
  const reviewResult = execution.execution_results.find(
    (r) => r.agent === "code-review"
  );

  console.log("Code Review:", reviewResult.result);

  return { code: featureResult.result, review: reviewResult.result };
}
```

---

**Your Dev-Tools platform is live and ready for integration!** 🚀
