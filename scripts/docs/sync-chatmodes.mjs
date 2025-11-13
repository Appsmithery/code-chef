#!/usr/bin/env node

import { promises as fs } from "fs";
import { dirname, resolve } from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const rootDir = resolve(__dirname, "..", "..");

const agentsDir = resolve(rootDir, "agents");
const chatmodesDir = resolve(rootDir, "docs", "chatmodes");
const GENERATED_MARKER = "<!-- generated: sync-chatmodes -->";

function toTitleCase(value) {
  return value
    .split(/[-_]+/)
    .map((piece) => piece.charAt(0).toUpperCase() + piece.slice(1))
    .join(" ");
}

async function readAgentSummary(agent) {
  const readmePath = resolve(agentsDir, agent, "README.md");
  try {
    const content = await fs.readFile(readmePath, "utf8");
    const lines = content.split(/\r?\n/);
    let summary = "";
    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed) continue;
      if (trimmed.startsWith("#")) continue;
      summary = trimmed.replace(/[*`_~]/g, "");
      break;
    }
    return summary;
  } catch {
    return "";
  }
}

async function ensureChatmode(agent) {
  const summary = await readAgentSummary(agent);
  const title = `${toTitleCase(agent)} Agent Chat Mode`;
  const filePath = resolve(chatmodesDir, `${agent}.md`);
  const body =
    `${GENERATED_MARKER}\n\n# ${title}\n\n` +
    (summary ? `${summary}\n\n` : "") +
    "This file maps the agent profile to its MCP chat mode configuration.\n\n" +
    "- **Agent Folder:** `agents/" +
    agent +
    "`\n" +
    "- **Primary Endpoint:** `/health`\n" +
    "- **Automation:** Managed by `scripts/docs/sync-chatmodes.mjs`\n";

  try {
    const existing = await fs.readFile(filePath, "utf8");
    if (existing.trim() === body.trim()) {
      return { status: "unchanged", filePath };
    }
  } catch {
    // File does not exist; fall through to write
  }

  await fs.writeFile(filePath, body, "utf8");
  return { status: "updated", filePath };
}

async function removeStaleFiles(validAgents) {
  const results = [];
  let entries = [];
  try {
    entries = await fs.readdir(chatmodesDir, { withFileTypes: true });
  } catch {
    return results;
  }

  const validSet = new Set(validAgents);

  for (const entry of entries) {
    if (!entry.isFile() || !entry.name.endsWith(".md")) continue;
    const agent = entry.name.replace(/\.md$/, "");
    if (validSet.has(agent)) continue;

    const filePath = resolve(chatmodesDir, entry.name);
    try {
      const content = await fs.readFile(filePath, "utf8");
      if (content.includes(GENERATED_MARKER)) {
        await fs.unlink(filePath);
        results.push({ status: "removed", filePath });
      }
    } catch {
      // Ignore
    }
  }

  return results;
}

async function main() {
  const agentEntries = await fs.readdir(agentsDir, { withFileTypes: true });
  const agents = agentEntries
    .filter((entry) => entry.isDirectory())
    .map((entry) => entry.name)
    .filter((name) => !name.startsWith("."));

  await fs.mkdir(chatmodesDir, { recursive: true });

  const updates = [];
  for (const agent of agents) {
    const result = await ensureChatmode(agent);
    updates.push({ agent, ...result });
  }

  const removals = await removeStaleFiles(agents);

  for (const { agent, status, filePath } of updates) {
    if (status === "updated") {
      console.log(
        `📝 Synced chatmode for ${agent} -> ${filePath.replace(
          rootDir + "/",
          ""
        )}`
      );
    }
  }

  for (const { filePath } of removals) {
    console.log(
      `🗑️ Removed stale chatmode file ${filePath.replace(rootDir + "/", "")}`
    );
  }

  if (
    !updates.some((entry) => entry.status === "updated") &&
    removals.length === 0
  ) {
    console.log("✅ Chatmode files are already in sync.");
  }
}

await main();
