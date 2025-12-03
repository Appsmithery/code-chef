# **12-Factor Agents** - AI DevOps Team

### **Factor 1: Natural Language to Tool Calls**

Convert deployment requests like "deploy backend to staging" into structured JSON configurations that trigger deterministic code.

### **Factor 2: Own Your Prompts**

Version-control hand-crafted system prompts for each agent role (`deploy-agent.prompt.md`, `rollback-agent.prompt.md`). Every token matters for reliability.

### **Factor 3: Own Your Context Window**

Curate deployment context carefully—summarize CI/CD state, compress logs, only include relevant history. Don't dump 50MB of CloudWatch logs into context.

### **Factor 4: Tools are Just Structured Outputs**

Define DevOps actions as strict Zod/JSON schemas validated before execution. "Tool use" is just JSON + deterministic code.

### **Factor 5: Unify Execution State and Business State**

Track both deployment progress (steps, retries) AND infrastructure state (what's deployed, health status) in one unified model.

### **Factor 6: Launch/Pause/Resume with Simple APIs**

All deployment workflows must support rollback, pause, and resume. Serialize state to DB, resume exactly where you left off.

### **Factor 7: Contact Humans with Tool Calls**

Critical prod deployments require human approval as a standardized workflow step—treat it like any other tool call.

### **Factor 8: Own Your Control Flow**

Build deterministic pipelines with LLM-powered decision gates at strategic points. Don't let the LLM run your entire deployment—YOU control the flow.

### **Factor 9: Compact Errors into Context**

Parse and compress build/deployment errors into actionable summaries. Clear resolved errors from context. No raw stack traces.

### **Factor 10: Small, Focused Agents**

Create specialized micro-agents (3-10 steps each): DeployAgent, RollbackAgent, IncidentAgent, MonitorAgent—not one giant 100-tool agent.

### **Factor 11: Trigger from Anywhere**

Support deployment triggers from Slack, GitHub PR merges, CLI, PagerDuty webhooks—meet your team where they already work.

### **Factor 12: Stateless Reducers**

All agent decisions must be reproducible from serialized deployment state. Pure functions enable testing, debugging, and audit logs.

## Core Philosophy

**"Agents are software."** Your deployment agents should be **mostly deterministic code** with LLM decision points strategically placed where flexibility adds value. As Dex says: *"Most production agents aren't that agentic at all—they're mostly just software with LLM steps sprinkled in at just the right points to make the experience truly magical."*

## Real Example: HumanLayer's Deployment Bot

Their bot is mostly deterministic CI/CD, but when a PR is merged and tests pass:

1. 🤖 Small agent decides deployment order (3-7 steps)
2. 💬 Requests human approval via Slack
3. ⏸️ Pauses and serializes state to DB
4. ▶️ Human approves, workflow resumes exactly where it left off
5. ✅ Deterministic health checks
6. 🤖 Small agent assesses metrics
7. 🔄 If needed, small rollback agent executes