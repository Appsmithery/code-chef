import { LinearClient } from "@linear/sdk";
import { getLinearOAuthConfig } from "../config/linearConfig.js";
import {
  clearToken,
  isTokenExpired,
  loadToken,
  saveToken,
  tokenSummary,
} from "../storage/tokenStore.js";

const TOKEN_ENDPOINT = "https://api.linear.app/oauth/token";
const GRAPHQL_ENDPOINT = "https://api.linear.app/graphql";

class LinearAuthError extends Error {
  constructor(message, code) {
    super(message);
    this.code = code;
  }
}

function composeTokenRecord(response, existing = {}) {
  const now = Date.now();
  const expiresIn = Number(response.expires_in ?? 0);
  const expiresAt = expiresIn > 0 ? now + expiresIn * 1000 : null;
  return {
    accessToken: response.access_token,
    refreshToken: response.refresh_token ?? existing.refreshToken ?? null,
    tokenType: response.token_type ?? existing.tokenType ?? "Bearer",
    scope: response.scope ?? existing.scope ?? null,
    obtainedAt: now,
    expiresAt,
    workspaceId: existing.workspaceId ?? null,
    viewerId: existing.viewerId ?? null,
    actor: "app",
  };
}

async function fetchViewerWorkspaceInfo(accessToken) {
  try {
    const response = await fetch(GRAPHQL_ENDPOINT, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${accessToken}`,
      },
      body: JSON.stringify({
        query: "query Viewer { viewer { id organization { id name } } }",
      }),
    });

    if (!response.ok) {
      const text = await response.text();
      throw new Error(
        `Linear viewer lookup failed: ${response.status} ${text}`
      );
    }

    const payload = await response.json();
    return {
      workspaceId: payload?.data?.viewer?.organization?.id ?? null,
      viewerId: payload?.data?.viewer?.id ?? null,
    };
  } catch (error) {
    console.warn("[linear] Failed to resolve viewer workspace:", error.message);
    return { workspaceId: null, viewerId: null };
  }
}

async function enrichTokenRecord(record) {
  if (record.workspaceId) {
    return record;
  }
  const info = await fetchViewerWorkspaceInfo(record.accessToken);
  return { ...record, ...info };
}

async function requestToken(params) {
  const body = new URLSearchParams(params);
  const response = await fetch(TOKEN_ENDPOINT, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: body.toString(),
  });
  const text = await response.text();
  if (!response.ok) {
    throw new Error(`Linear token endpoint error ${response.status}: ${text}`);
  }
  return JSON.parse(text);
}

export async function exchangeAuthorizationCode(code) {
  const { clientId, clientSecret, redirectUri } = getLinearOAuthConfig();
  const raw = await requestToken({
    grant_type: "authorization_code",
    code,
    redirect_uri: redirectUri,
    client_id: clientId,
    client_secret: clientSecret,
  });
  const record = await enrichTokenRecord(composeTokenRecord(raw));
  await saveToken(record);
  return record;
}

async function refreshToken(stored) {
  if (!stored?.refreshToken) {
    return null;
  }
  const { clientId, clientSecret } = getLinearOAuthConfig();
  const raw = await requestToken({
    grant_type: "refresh_token",
    refresh_token: stored.refreshToken,
    client_id: clientId,
    client_secret: clientSecret,
  });
  const record = await enrichTokenRecord(
    composeTokenRecord(raw, {
      workspaceId: stored.workspaceId,
      viewerId: stored.viewerId,
      scope: stored.scope,
    })
  );
  await saveToken(record);
  return record;
}

function developerTokenFallback() {
  const { developerToken } = getLinearOAuthConfig();
  if (!developerToken) {
    return null;
  }
  return {
    accessToken: developerToken,
    tokenType: "Bearer",
    scope: "developer-token",
    obtainedAt: Date.now(),
    expiresAt: null,
    workspaceId: null,
    viewerId: null,
    actor: "developer-token",
  };
}

export async function getActiveToken({ allowDeveloperFallback = true } = {}) {
  const stored = await loadToken();
  if (stored && !isTokenExpired(stored)) {
    return { token: stored, source: "stored" };
  }

  if (stored && isTokenExpired(stored)) {
    try {
      const refreshed = await refreshToken(stored);
      if (refreshed) {
        return { token: refreshed, source: "refreshed" };
      }
    } catch (error) {
      console.error("[linear] Token refresh failed, clearing stored token.");
      await clearToken();
    }
  }

  if (allowDeveloperFallback) {
    const fallback = developerTokenFallback();
    if (fallback) {
      return { token: fallback, source: "developer-token", ephemeral: true };
    }
  }

  throw new LinearAuthError(
    "No Linear OAuth token available",
    "LINEAR_TOKEN_MISSING"
  );
}

function getLinearClient(accessToken) {
  if (!accessToken) {
    throw new LinearAuthError(
      "Missing Linear access token",
      "LINEAR_TOKEN_MISSING"
    );
  }
  return new LinearClient({ accessToken });
}

export async function resolveLinearClient() {
  const { token } = await getActiveToken();
  return getLinearClient(token.accessToken);
}

export async function fetchRoadmapIssues() {
  const client = await resolveLinearClient();
  const issues = await client.issues({
    filter: {
      state: { type: { in: ["started", "unstarted", "backlog"] } },
    },
    first: 50,
  });
  return issues.nodes.map((issue) => ({
    id: issue.id,
    title: issue.title,
    state: issue.state?.name,
    priority: issue.priority,
    assignee: issue.assignee?.name,
    url: issue.url,
    createdAt: issue.createdAt,
    updatedAt: issue.updatedAt,
  }));
}

export async function fetchProjectRoadmap(projectId) {
  const client = await resolveLinearClient();
  const project = await client.project(projectId);
  const projectData = await project;
  const issues = await projectData.issues();
  return {
    project: {
      id: projectData.id,
      name: projectData.name,
      state: projectData.state,
      progress: projectData.progress,
    },
    issues: issues.nodes.map((issue) => ({
      id: issue.id,
      title: issue.title,
      state: issue.state?.name,
      priority: issue.priority,
      url: issue.url,
    })),
  };
}

export async function getTokenStatus() {
  const stored = await loadToken();
  return {
    stored: stored ? tokenSummary(stored) : null,
    developerFallback: Boolean(getLinearOAuthConfig().developerToken),
  };
}

export async function revokeStoredToken() {
  await clearToken();
}

export const LinearAuthErrors = {
  TOKEN_MISSING: "LINEAR_TOKEN_MISSING",
};
