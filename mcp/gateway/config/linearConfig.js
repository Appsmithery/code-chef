import { readFileSync } from "fs";
import path from "path";

function readSecret(envVar) {
  const filePath = process.env[`${envVar}_FILE`];
  if (filePath) {
    return readFileSync(filePath, "utf8").trim();
  }
  return process.env[envVar];
}

const {
  LINEAR_OAUTH_CLIENT_ID,
  LINEAR_OAUTH_CLIENT_SECRET,
  LINEAR_OAUTH_REDIRECT_URI,
  LINEAR_OAUTH_SCOPES,
  LINEAR_OAUTH_DEV_TOKEN,
  LINEAR_WEBHOOK_URI,
  LINEAR_WEBHOOK_SIGNING_SECRET,
  LINEAR_TOKEN_STORE_DIR,
} = process.env;

const DEFAULT_SCOPES = "read,write,app:mentionable,app:assignable";

export function getLinearScopes() {
  const raw = LINEAR_OAUTH_SCOPES || DEFAULT_SCOPES;
  return raw
    .split(",")
    .map((scope) => scope.trim())
    .filter(Boolean)
    .join(",");
}

export function getLinearOAuthConfig() {
  return {
    clientId: LINEAR_OAUTH_CLIENT_ID,
    clientSecret: readSecret("LINEAR_OAUTH_CLIENT_SECRET"),
    redirectUri: LINEAR_OAUTH_REDIRECT_URI,
    scopes: getLinearScopes(),
    developerToken: readSecret("LINEAR_OAUTH_DEV_TOKEN"),
    webhookUri: LINEAR_WEBHOOK_URI,
    webhookSigningSecret: readSecret("LINEAR_WEBHOOK_SIGNING_SECRET"),
  };
}

export function validateLinearOAuthConfig() {
  const { clientId, clientSecret, redirectUri } = getLinearOAuthConfig();
  const missing = [];
  if (!clientId) missing.push("LINEAR_OAUTH_CLIENT_ID");
  if (!clientSecret) missing.push("LINEAR_OAUTH_CLIENT_SECRET");
  if (!redirectUri) missing.push("LINEAR_OAUTH_REDIRECT_URI");
  if (missing.length) {
    throw new Error(
      `Missing Linear OAuth config: ${missing.join(
        ", "
      )}. Check your environment variables.`
    );
  }
}

export function buildLinearAuthorizeUrl(state) {
  validateLinearOAuthConfig();
  const { clientId, redirectUri, scopes } = getLinearOAuthConfig();
  const base = "https://linear.app/oauth/authorize";
  const params = new URLSearchParams({
    response_type: "code",
    client_id: clientId,
    redirect_uri: redirectUri,
    scope: scopes,
    state,
    actor: "app",
  });
  return `${base}?${params.toString()}`;
}

export function getTokenStoreDir() {
  const target = LINEAR_TOKEN_STORE_DIR || "./config";
  return path.resolve(process.cwd(), target);
}
