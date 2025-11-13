import { existsSync, readFileSync, readdirSync, writeFileSync } from "node:fs";
import path from "node:path";
import { discoverSchemas, mergeSchemas } from "./schema-merger.js";

interface AgentManifestProfile {
  name: string;
  directory: string;
  configPath?: string;
  toolsetPath?: string;
  mcpServers: string[];
  requiredSecrets: string[];
  secretsWithProvenance?: Array<{ name: string; provenance: string }>;
  missingFromSchema: string[];
  warnings: string[];
}

interface AgentManifestFile {
  version: string;
  generatedAt: string;
  profiles: AgentManifestProfile[];
  warnings: string[];
}

type UnknownRecord = Record<string, unknown>;

const AGENTS_ROOT = "agents";
const CONFIG_FILENAME = "config.json";
const TOOLSET_FILENAME = "toolset.jsonc";
const MANIFEST_PATH = "agents/agents-manifest.json";
const SERVER_REGISTRY_PATH = "agents/mcp-servers/active-registry.json";

function isRecord(value: unknown): value is UnknownRecord {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((entry) => typeof entry === "string");
}

function resolvePath(candidate: string): string {
  return path.isAbsolute(candidate) ? candidate : path.resolve(candidate);
}

function readJsonFile<T>(filePath: string): T | undefined {
  const resolved = resolvePath(filePath);

  if (!existsSync(resolved)) {
    return undefined;
  }

  const content = readFileSync(resolved, "utf-8");
  return JSON.parse(content) as T;
}

function stripJsonComments(content: string): string {
  return content
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/^\s*\/\/.+$/gm, "");
}

function readJsoncFile<T>(filePath: string): T | undefined {
  const resolved = resolvePath(filePath);

  if (!existsSync(resolved)) {
    return undefined;
  }

  const raw = readFileSync(resolved, "utf-8");
  const sanitized = stripJsonComments(raw);
  return JSON.parse(sanitized) as T;
}

function collectEnvVarLiterals(source: unknown, accumulator: Set<string>): void {
  if (Array.isArray(source)) {
    for (const entry of source) {
      collectEnvVarLiterals(entry, accumulator);
    }
    return;
  }

  if (isRecord(source)) {
    for (const value of Object.values(source)) {
      collectEnvVarLiterals(value, accumulator);
    }
    return;
  }

  if (typeof source === "string" && /^[A-Z0-9_]+$/.test(source)) {
    accumulator.add(source);
  }
}

function extractEnvPlaceholders(value: unknown, accumulator: Set<string>): void {
  if (typeof value === "string") {
    const regex = /\${env:([A-Z0-9_]+)(?::[^}]*)?}/g;
    let match: RegExpExecArray | null;

    while ((match = regex.exec(value)) !== null) {
      accumulator.add(match[1]);
    }

    return;
  }

  if (Array.isArray(value)) {
    for (const entry of value) {
      extractEnvPlaceholders(entry, accumulator);
    }
    return;
  }

  if (isRecord(value)) {
    for (const nested of Object.values(value)) {
      extractEnvPlaceholders(nested, accumulator);
    }
  }
}

function gatherAgentDirectories(): string[] {
  const resolvedRoot = resolvePath(AGENTS_ROOT);

  if (!existsSync(resolvedRoot)) {
    return [];
  }

  return readdirSync(resolvedRoot, { withFileTypes: true })
    .filter((dirent) => dirent.isDirectory() && dirent.name.startsWith("_"))
    .map((dirent) => dirent.name);
}

function collectMcpServers(agentConfig: UnknownRecord | undefined): string[] {
  if (!agentConfig) {
    return [];
  }

  const explicitList = agentConfig.mcp_servers;
  if (isStringArray(explicitList)) {
    return explicitList;
  }

  const dependencies = agentConfig.mcp_dependencies;
  if (isRecord(dependencies)) {
    const servers = new Set<string>();

    for (const key of ["primary", "secondary", "tertiary"]) {
      const list = dependencies[key];
      if (isStringArray(list)) {
        list.forEach((entry) => servers.add(entry));
      }
    }

    return Array.from(servers);
  }

  return [];
}

function collectSecretsFromConfig(agentConfig: UnknownRecord | undefined): Set<string> {
  const secrets = new Set<string>();

  if (!agentConfig) {
    return secrets;
  }

  const secretsManagement = agentConfig.secrets_management;
  if (isRecord(secretsManagement)) {
    const required = secretsManagement.required_variables;
    if (isStringArray(required)) {
      required.forEach((entry) => secrets.add(entry));
    }
  }

  const envCredentials = agentConfig.environment_credentials;
  if (isRecord(envCredentials)) {
    collectEnvVarLiterals(envCredentials, secrets);
  }

  extractEnvPlaceholders(agentConfig, secrets);

  return secrets;
}

function collectSecretsFromToolset(toolset: UnknownRecord | undefined): Set<string> {
  const secrets = new Set<string>();

  if (!toolset) {
    return secrets;
  }

  const requiredEnv = toolset.required_env;
  if (isStringArray(requiredEnv)) {
    requiredEnv.forEach((entry) => secrets.add(entry));
  }

  extractEnvPlaceholders(toolset, secrets);

  return secrets;
}

function collectSecretsFromServerConfig(
  serverConfig: UnknownRecord | undefined
): Set<string> {
  const secrets = new Set<string>();

  if (!serverConfig) {
    return secrets;
  }

  const envValues = serverConfig.env;
  if (isRecord(envValues)) {
    extractEnvPlaceholders(envValues, secrets);
  }

  const headers = serverConfig.headers;
  if (isRecord(headers)) {
    extractEnvPlaceholders(headers, secrets);
  }

  extractEnvPlaceholders(serverConfig, secrets);

  return secrets;
}

function sortUnique(values: Iterable<string>): string[] {
  return Array.from(new Set(values)).sort();
}

function main(): void {
  // Replace the old schema loading with merged schema
  const { core, overlays } = discoverSchemas({
    coreSchemaPath: 'config/secrets.core.json',
    overlaysDir: 'config/secrets.overlays',
  });

  const mergedSchema = mergeSchemas(core, overlays);
  const schemaSecrets = new Set(mergedSchema.secrets.map((entry) => entry.name));

  console.log(`Loaded schema with ${schemaSecrets.size} secrets from ${overlays.size + 1} sources`);

  const registry = readJsonFile<{ servers: Record<string, UnknownRecord> }>(
    SERVER_REGISTRY_PATH
  );

  const manifestWarnings: string[] = [];
  const profiles: AgentManifestProfile[] = [];

  const agentDirectories = gatherAgentDirectories();

  for (const directoryName of agentDirectories) {
    const agentRoot = path.join(AGENTS_ROOT, directoryName);
    const configPath = path.join(agentRoot, CONFIG_FILENAME);
    const toolsetPath = path.join(agentRoot, TOOLSET_FILENAME);

    const agentConfig = readJsonFile<UnknownRecord>(configPath);
    const toolset = readJsoncFile<UnknownRecord>(toolsetPath);

    const profileName = directoryName.replace(/^_/, "");
    const warnings: string[] = [];

    if (!agentConfig) {
      warnings.push(`Missing ${CONFIG_FILENAME}`);
    }

    const mcpServers = sortUnique(collectMcpServers(agentConfig));
    const requiredSecrets = new Set<string>();

    collectSecretsFromConfig(agentConfig).forEach((secret) => requiredSecrets.add(secret));
    collectSecretsFromToolset(toolset).forEach((secret) => requiredSecrets.add(secret));

    for (const serverName of mcpServers) {
      const serverConfig = registry?.servers?.[serverName];

      if (!serverConfig) {
        warnings.push(`Server '${serverName}' missing from active registry`);
        continue;
      }

      collectSecretsFromServerConfig(serverConfig).forEach((secret) =>
        requiredSecrets.add(secret)
      );
    }

    const requiredSecretsList = sortUnique(requiredSecrets);
    const missingFromSchema = requiredSecretsList.filter(
      (secret) => schemaSecrets.size > 0 && !schemaSecrets.has(secret)
    );

    // Add provenance info for required secrets
    const secretsWithProvenance = requiredSecretsList.map((name) => ({
      name,
      provenance: mergedSchema.provenanceMap.get(name) || 'undeclared',
    }));

    if (missingFromSchema.length > 0) {
      warnings.push(
        `Secrets not in merged schema: ${missingFromSchema.join(', ')}`
      );
    }

    profiles.push({
      name: profileName,
      directory: directoryName,
      configPath: existsSync(resolvePath(configPath))
        ? path.relative(process.cwd(), resolvePath(configPath))
        : undefined,
      toolsetPath: existsSync(resolvePath(toolsetPath))
        ? path.relative(process.cwd(), resolvePath(toolsetPath))
        : undefined,
      mcpServers,
      requiredSecrets: requiredSecretsList,
      secretsWithProvenance, // NEW: include provenance
      missingFromSchema,
      warnings,
    });
  }

  const manifest: AgentManifestFile = {
    version: "1.0.0",
    generatedAt: new Date().toISOString(),
    profiles: profiles.sort((a, b) => a.name.localeCompare(b.name)),
    warnings: manifestWarnings,
  };

  writeFileSync(
    resolvePath(MANIFEST_PATH),
    `${JSON.stringify(manifest, null, 2)}\n`,
    "utf-8"
  );

  console.log("=== Agent Manifest Sync ===\n");
  console.log(`Profiles processed: ${profiles.length}`);
  console.log(`Manifest written to ${path.relative(process.cwd(), MANIFEST_PATH)}`);

  const allWarnings = profiles.flatMap((profile) =>
    profile.warnings.map((warning) => `${profile.name}: ${warning}`)
  );

  if (manifestWarnings.length > 0 || allWarnings.length > 0) {
    console.warn("\nWarnings:");
    [...manifestWarnings, ...allWarnings].forEach((warning) => console.warn(`- ${warning}`));
  }
}

try {
  main();
} catch (error) {
  console.error("Manifest sync failed:", error instanceof Error ? error.message : error);
  process.exit(1);
}


