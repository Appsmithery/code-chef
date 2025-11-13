#!/usr/bin/env node

import { promises as fs } from "fs";
import { dirname, resolve } from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const rootDir = resolve(__dirname, "..", "..");
const reportsDir = resolve(rootDir, "reports");
const outputPath = resolve(reportsDir, "reports-index.json");

async function collectReports(dir, relative = "") {
  let entries = [];
  try {
    entries = await fs.readdir(dir, { withFileTypes: true });
  } catch (error) {
    if (error.code === "ENOENT") {
      return [];
    }
    throw error;
  }

  const items = [];

  for (const entry of entries) {
    if (entry.name.startsWith(".")) continue;
    const actualPath = resolve(dir, entry.name);
    const relPath = relative ? `${relative}/${entry.name}` : entry.name;

    if (entry.isDirectory()) {
      const children = await collectReports(actualPath, relPath);
      items.push(...children);
      continue;
    }

    if (!/(\.json|\.md)$/i.test(entry.name)) continue;

    const stats = await fs.stat(actualPath);
    items.push({
      path: relPath.replace(/\\/g, "/"),
      size: stats.size,
      modified: stats.mtime.toISOString(),
    });
  }

  return items;
}

async function main() {
  const files = await collectReports(reportsDir);
  await fs.mkdir(dirname(outputPath), { recursive: true });
  const payload = {
    generated: new Date().toISOString(),
    count: files.length,
    files: files.sort((a, b) => a.path.localeCompare(b.path)),
  };

  await fs.writeFile(outputPath, JSON.stringify(payload, null, 2));
  console.log(
    `🗂️  Report index written to ${outputPath.replace(rootDir + "/", "")}`
  );
}

await main();
