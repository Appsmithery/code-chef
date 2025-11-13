#!/usr/bin/env node

import { promises as fs } from "fs";
import { dirname, resolve } from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const rootDir = resolve(__dirname, "..", "..");

const cleanupTargets = [
  ["reports", "temp"],
  ["reports", "context", "tmp"],
  ["reports", "context", "cache"],
];

async function removePath(parts) {
  const targetPath = resolve(rootDir, ...parts);
  let exists = false;
  try {
    await fs.access(targetPath);
    exists = true;
  } catch {
    exists = false;
  }

  if (!exists) {
    console.log(
      `ℹ️  Skipping missing ${targetPath.replace(rootDir + "/", "")}`
    );
    return;
  }

  try {
    await fs.rm(targetPath, { recursive: true, force: true });
    console.log(`🧹 Removed ${targetPath.replace(rootDir + "/", "")}`);
  } catch (error) {
    console.error(`⚠️  Unable to remove ${targetPath}:`, error.message);
    process.exitCode = 1;
  }
}

async function main() {
  await Promise.all(cleanupTargets.map(removePath));
  console.log("✨ Reports cleanup complete.");
}

await main();
