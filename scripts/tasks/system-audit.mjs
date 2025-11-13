#!/usr/bin/env node

import { promises as fs } from "fs";
import { dirname, resolve } from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const rootDir = resolve(__dirname, "..", "..");

const targets = [
  { path: "compose/docker-compose.yml", label: "Docker Compose stack" },
  {
    path: "configs/routing/task-router.rules.yaml",
    label: "Task router rules",
  },
  { path: "configs/rag/indexing.yaml", label: "RAG indexing config" },
  { path: "configs/rag/vectordb.config.yaml", label: "Vector DB config" },
  { path: "configs/state/schema.sql", label: "State schema" },
  { path: "configs/env/.env.example", label: "Environment template" },
  { path: "agents/agents-manifest.json", label: "Agents manifest" },
  { path: "docs/AGENT_ENDPOINTS.md", label: "Agent endpoints documentation" },
];

async function checkPath({ path, label }) {
  const absolute = resolve(rootDir, path);
  try {
    const stats = await fs.stat(absolute);
    console.log(`✅ ${label.padEnd(30)} → ${path} (${stats.size} bytes)`);
    return true;
  } catch (error) {
    console.error(`❌ ${label.padEnd(30)} → missing (${path})`);
    return false;
  }
}

async function main() {
  const results = await Promise.all(targets.map(checkPath));
  if (results.every(Boolean)) {
    console.log("\nSystem audit completed successfully.");
  } else {
    console.error("\nSystem audit detected missing assets.");
    process.exitCode = 1;
  }
}

await main();
