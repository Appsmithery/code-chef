import { promises as fs } from "fs";
import path from "path";
import { getTokenStoreDir } from "../config/linearConfig.js";

function getTokenFilePath() {
  const dir = getTokenStoreDir();
  return path.join(dir, "linear-token.json");
}

async function ensureDir() {
  const dir = getTokenStoreDir();
  await fs.mkdir(dir, { recursive: true });
  return dir;
}

export async function saveToken(payload) {
  await ensureDir();
  const data = JSON.stringify(payload, null, 2);
  await fs.writeFile(getTokenFilePath(), data, "utf-8");
  return payload;
}

export async function loadToken() {
  try {
    const raw = await fs.readFile(getTokenFilePath(), "utf-8");
    return JSON.parse(raw);
  } catch (error) {
    if (error.code === "ENOENT") {
      return null;
    }
    throw error;
  }
}

export async function clearToken() {
  try {
    await fs.unlink(getTokenFilePath());
  } catch (error) {
    if (error.code !== "ENOENT") {
      throw error;
    }
  }
}

export function isTokenExpired(token) {
  if (!token || !token.expiresAt) {
    return false;
  }
  return Date.now() >= token.expiresAt;
}

export function tokenSummary(token) {
  if (!token) {
    return null;
  }
  const { workspaceId, obtainedAt, expiresAt, scope, actor } = token;
  return {
    workspaceId,
    scope,
    obtainedAt,
    expiresAt,
    actor,
  };
}
