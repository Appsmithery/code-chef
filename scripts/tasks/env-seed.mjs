#!/usr/bin/env node

import { promises as fs } from "fs";
import { dirname, resolve } from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const rootDir = resolve(__dirname, "..", "..");

const envPath = resolve(rootDir, ".env");
const examplePath = resolve(rootDir, ".env.example");

async function ensureEnvFile() {
  try {
    await fs.access(envPath);
    console.log("✅ .env already present — no action needed.");
    return;
  } catch {
    // File missing; continue
  }

  try {
    await fs.copyFile(examplePath, envPath);
    console.log("🆕 Created .env from .env.example");
  } catch (error) {
    if (error.code === "ENOENT") {
      console.error("❌ Cannot seed .env — missing .env.example");
    } else {
      console.error("❌ Failed to seed .env:", error.message);
    }
    process.exitCode = 1;
  }
}

await ensureEnvFile();
