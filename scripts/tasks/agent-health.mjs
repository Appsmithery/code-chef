#!/usr/bin/env node

import { dirname, resolve } from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const rootDir = resolve(__dirname, "..", "..");

const agentConfig = {
  gateway: { port: 8000, path: "/health" },
  "mcp-gateway": { port: 8000, path: "/health" },
  orchestrator: { port: 8001, path: "/health" },
  "feature-dev": { port: 8002, path: "/health" },
  "code-review": { port: 8003, path: "/health" },
  documentation: { port: 8004, path: "/health" },
  infrastructure: { port: 8006, path: "/health" },
  cicd: { port: 8005, path: "/health" },
  rag: { port: 8007, path: "/health" },
  state: { port: 8008, path: "/health" },
};

const rawAgents = process.argv.slice(2);
if (!rawAgents.length) {
  console.error(
    "❌ No agents specified. Usage: node scripts/tasks/agent-health.mjs orchestrator,feature-dev"
  );
  process.exit(1);
}

const agents = rawAgents
  .join(" ")
  .split(",")
  .map((agent) => agent.trim())
  .filter(Boolean);

const host = process.env.AGENT_HOST ?? "http://localhost";
const timeoutMs = Number(process.env.AGENT_HEALTH_TIMEOUT ?? 5000);

async function fetchWithTimeout(url, options = {}) {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
    });
    return response;
  } finally {
    clearTimeout(id);
  }
}

async function checkAgent(agent) {
  const config = agentConfig[agent] ?? agentConfig[agent.replace(/-/g, "_")];
  if (!config) {
    console.warn(`⚠️  Unknown agent "${agent}" — skipping.`);
    return true;
  }

  const url = `${host.replace(/\/$/, "")}:${config.port}${config.path}`;

  try {
    const response = await fetchWithTimeout(url);
    if (!response.ok) {
      console.error(`❌ ${agent}: HTTP ${response.status}`);
      return false;
    }
    const payload = await response.json().catch(() => ({}));
    const status = payload.status ?? "unknown";
    console.log(`✅ ${agent} — status: ${status}`);
    return true;
  } catch (error) {
    console.error(`❌ ${agent}: ${error.message}`);
    return false;
  }
}

async function main() {
  const results = await Promise.all(agents.map(checkAgent));
  if (results.every(Boolean)) {
    console.log("\nAll requested agents are healthy.");
  } else {
    console.error("\nOne or more agents failed health checks.");
    process.exitCode = 1;
  }
}

await main();
