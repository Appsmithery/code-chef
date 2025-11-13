import { existsSync, readFileSync } from 'fs';
import { resolve } from 'path';
import { discoverSchemas, mergeSchemas } from './schema-merger.js';

interface ValidationOptions {
  schemas?: string[];
  envFiles?: string[];
  format?: 'human' | 'json';
  discoverOverlays?: boolean;
}

function parseArgs(): ValidationOptions {
  const args = process.argv.slice(2);
  const options: ValidationOptions = {
    schemas: [],
    envFiles: ['.env', 'agents/.env.agent.local'],
    format: 'human',
    discoverOverlays: false,
  };

  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--schema' && args[i + 1]) {
      options.schemas!.push(args[++i]);
    } else if (args[i] === '--env-file' && args[i + 1]) {
      options.envFiles!.push(args[++i]);
    } else if (args[i] === '--json') {
      options.format = 'json';
    } else if (args[i] === '--discover-overlays') {
      options.discoverOverlays = true;
    }
  }

  return options;
}

function loadEnvVars(files: string[]): Map<string, string> {
  const vars = new Map<string, string>();

  for (const file of files) {
    const filePath = resolve(file);
    if (!existsSync(filePath)) continue;

    const content = readFileSync(filePath, 'utf-8');
    for (const line of content.split('\n')) {
      const match = line.match(/^([^#=]+)=(.*)$/);
      if (match) {
        vars.set(match[1].trim(), match[2].trim());
      }
    }
  }

  // Also check process.env
  for (const [key, value] of Object.entries(process.env)) {
    if (value !== undefined) {
      vars.set(key, value);
    }
  }

  return vars;
}

async function validateSecrets(): Promise<void> {
  const options = parseArgs();

  // Discover schemas
  const { core, overlays } = discoverSchemas({
    coreSchemaPath: 'config/secrets.core.json',
    overlaysDir: 'config/secrets.overlays',
  });

  // Add CLI-specified overlays
  for (const schemaPath of options.schemas || []) {
    if (existsSync(schemaPath)) {
      const schema = JSON.parse(readFileSync(schemaPath, 'utf-8'));
      overlays.set(schemaPath, schema);
    }
  }

  // Merge schemas
  const merged = mergeSchemas(core, overlays);

  // Load environment variables
  const envVars = loadEnvVars(options.envFiles!);

  // Validate
  const missing: Array<{ name: string; provenance: string; description: string }> = [];
  const found: Array<{ name: string; provenance: string }> = [];

  for (const secret of merged.secrets) {
    const value = envVars.get(secret.name);
    const provenance = merged.provenanceMap.get(secret.name) || 'unknown';

    if (!value && secret.required) {
      missing.push({
        name: secret.name,
        provenance,
        description: secret.description,
      });
    } else if (value) {
      found.push({ name: secret.name, provenance });
    }
  }

  // Output
  if (options.format === 'json') {
    console.log(
      JSON.stringify(
        {
          valid: missing.length === 0,
          found: found.length,
          missing: missing.length,
          total: merged.secrets.length,
          details: { found, missing },
          provenance: Object.fromEntries(merged.provenanceMap),
        },
        null,
        2
      )
    );
  } else {
    console.log('=== Secrets Validation (Merged Schema) ===\n');

    console.log('Schema Sources:');
    console.log(`  Core: config/secrets.core.json`);
    console.log(`  Overlays: ${overlays.size} discovered`);
    for (const name of overlays.keys()) {
      console.log(`    - ${name}`);
    }
    console.log();

    if (found.length > 0) {
      console.log('Found Secrets:');
      for (const { name, provenance } of found) {
        console.log(`  G�� ${name} (from ${provenance})`);
      }
      console.log();
    }

    if (missing.length > 0) {
      console.log('Missing Required Secrets:');
      for (const { name, provenance, description } of missing) {
        console.log(`  G�� ${name} (from ${provenance})`);
        console.log(`     ${description}`);
      }
      console.log();
    }

    console.log(`Summary: ${found.length}/${merged.secrets.length} found, ${missing.length} missing`);
  }

  if (missing.length > 0) {
    process.exit(1);
  }
}

validateSecrets().catch((err) => {
  console.error('Validation error:', err);
  process.exit(1);
});

