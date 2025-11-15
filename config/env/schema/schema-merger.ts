import { existsSync, readFileSync, readdirSync } from 'fs';
import { join, resolve } from 'path';

export interface SecretSchemaEntry {
  name: string;
  required: boolean;
  description: string;
  sources: string[];
  provenance?: string; // 'core' | overlay filename
}

export interface SecretsSchema {
  version: string;
  secrets: SecretSchemaEntry[];
}

export interface MergedSchema extends SecretsSchema {
  provenanceMap: Map<string, string>; // secret name -> source file
}

/**
 * Discovers and loads all schema files (core + overlays)
 */
export function discoverSchemas(options: {
  coreSchemaPath?: string;
  overlaysDir?: string;
  submoduleParent?: string;
}): { core: SecretsSchema | null; overlays: Map<string, SecretsSchema> } {
  const {
    coreSchemaPath = 'config/env/schema/secrets.core.json',
    overlaysDir = 'config/env/schema/overlays',
    submoduleParent = '..',
  } = options;

  // Load core schema
  let core: SecretsSchema | null = null;
  const coreResolved = resolve(coreSchemaPath);
  if (existsSync(coreResolved)) {
    core = JSON.parse(readFileSync(coreResolved, 'utf-8'));
  }

  // Load local overlays
  const overlays = new Map<string, SecretsSchema>();
  const overlaysDirResolved = resolve(overlaysDir);

  if (existsSync(overlaysDirResolved)) {
    const files = readdirSync(overlaysDirResolved).filter(f => f.endsWith('.json'));
    for (const file of files) {
      const filePath = join(overlaysDirResolved, file);
      const schema: SecretsSchema = JSON.parse(readFileSync(filePath, 'utf-8'));
      overlays.set(file, schema);
    }
  }

  // Discover submodule overlays (when Dev-Tools is embedded)
  const _submoduleSearch = resolve(submoduleParent, '*/config/dev-tools.secrets.schema.json');
  // Note: This is a simplified search; production should use glob or recursive scan
  // For now, check if we're in a submodule context
  const parentConfigPath = resolve(submoduleParent, 'config/dev-tools.secrets.schema.json');
  if (existsSync(parentConfigPath)) {
    const schema: SecretsSchema = JSON.parse(readFileSync(parentConfigPath, 'utf-8'));
    overlays.set('parent-project', schema);
  }

  return { core, overlays };
}

/**
 * Merges core schema with overlays, tracking provenance
 */
export function mergeSchemas(
  core: SecretsSchema | null,
  overlays: Map<string, SecretsSchema>
): MergedSchema {
  const secretsMap = new Map<string, SecretSchemaEntry>();
  const provenanceMap = new Map<string, string>();

  // Add core secrets
  if (core) {
    for (const secret of core.secrets) {
      secretsMap.set(secret.name, { ...secret, provenance: 'core' });
      provenanceMap.set(secret.name, 'secrets.core.json');
    }
  }

  // Merge overlays (later overlays can override/extend)
  for (const [overlayName, overlaySchema] of overlays) {
    for (const secret of overlaySchema.secrets) {
      const existing = secretsMap.get(secret.name);

      if (existing) {
        // Merge sources, upgrade to required if any overlay requires it
        secretsMap.set(secret.name, {
          ...existing,
          required: existing.required || secret.required,
          sources: Array.from(new Set([...existing.sources, ...secret.sources])),
          description: secret.description || existing.description,
          provenance: `${existing.provenance}, ${overlayName}`,
        });
      } else {
        secretsMap.set(secret.name, { ...secret, provenance: overlayName });
      }

      provenanceMap.set(secret.name, overlayName);
    }
  }

  return {
    version: core?.version || '1.0.0',
    secrets: Array.from(secretsMap.values()).sort((a, b) => a.name.localeCompare(b.name)),
    provenanceMap,
  };
}

/**
 * Exports the merged schema for other tooling
 */
export function exportMergedSchema(merged: MergedSchema): SecretsSchema {
  return {
    version: merged.version,
    secrets: merged.secrets.map(({ provenance: _provenance, ...rest }) => rest),
  };
}

