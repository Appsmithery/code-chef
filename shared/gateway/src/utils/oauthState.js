import crypto from "crypto";

const states = new Map();
const STATE_TTL_MS = 5 * 60 * 1000;

export function createState(metadata = {}) {
  const state = crypto.randomBytes(16).toString("hex");
  const expiresAt = Date.now() + STATE_TTL_MS;
  states.set(state, { expiresAt, metadata });
  return state;
}

export function consumeState(state) {
  const record = states.get(state);
  if (!record) {
    return null;
  }
  states.delete(state);
  if (record.expiresAt < Date.now()) {
    return null;
  }
  return record.metadata || {};
}

export function pruneExpiredStates() {
  const now = Date.now();
  for (const [key, value] of states.entries()) {
    if (value.expiresAt <= now) {
      states.delete(key);
    }
  }
}

setInterval(pruneExpiredStates, STATE_TTL_MS).unref();
