#!/usr/bin/env node

import { promises as fs } from "fs";
import { dirname, resolve } from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const rootDir = resolve(__dirname, "..", "..");
const outputPath = resolve(
  rootDir,
  "context",
  "agents",
  "store",
  "shared",
  "_repo-GPS",
  "repo-folder-tree.txt"
);

const ignore = new Set([
  ".git",
  ".github",
  ".idea",
  ".vscode",
  ".venv",
  "node_modules",
  "dist",
  "build",
  "coverage",
  "__pycache__",
]);

async function listDirectory(dir) {
  const entries = await fs.readdir(dir, { withFileTypes: true });
  return entries
    .filter(
      (entry) => !entry.name.startsWith(".") || entry.name === ".env.example"
    )
    .filter((entry) => !ignore.has(entry.name))
    .sort((a, b) => {
      if (a.isDirectory() && !b.isDirectory()) return -1;
      if (!a.isDirectory() && b.isDirectory()) return 1;
      return a.name.localeCompare(b.name);
    });
}

async function buildTree(dir, prefix = "") {
  const entries = await listDirectory(dir);
  const lines = [];

  for (let index = 0; index < entries.length; index += 1) {
    const entry = entries[index];
    const connector = index === entries.length - 1 ? "└── " : "├── ";
    const childPrefix = index === entries.length - 1 ? "    " : "│   ";
    lines.push(`${prefix}${connector}${entry.name}`);

    if (entry.isDirectory()) {
      const childLines = await buildTree(
        resolve(dir, entry.name),
        prefix + childPrefix
      );
      lines.push(...childLines);
    }
  }

  return lines;
}

async function ensureDirectory(pathname) {
  const parent = dirname(pathname);
  await fs.mkdir(parent, { recursive: true });
}

async function main() {
  const treeLines = await buildTree(rootDir);
  const banner = [
    `Repository: ${rootDir}`,
    `Generated: ${new Date().toISOString()}`,
    "",
  ];
  const output = banner.concat(treeLines).join("\n");
  await ensureDirectory(outputPath);
  await fs.writeFile(outputPath, output, "utf8");
  console.log(
    `🌲 Folder tree written to ${outputPath.replace(rootDir + "/", "")}`
  );
}

await main();
