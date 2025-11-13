#!/usr/bin/env bash
# Hydrate local agent environment variables and validate required secrets.

set -euo pipefail

ENV_FILE="agents/.env.agent.local"
MANIFEST_FILE="agents/agents-manifest.json"

log() {
  printf '%s\n' "$1"
}

heading() {
  printf '\n=== %s ===\n\n' "$1"
}

ensure_env_file() {
  if [[ -f "$ENV_FILE" ]]; then
    log "G£Ù Local agent env file found: $ENV_FILE"
    return
  fi

  log "Creating $ENV_FILE..."
  mkdir -p "$(dirname "$ENV_FILE")"
  cat <<EOF >"$ENV_FILE"
# Agent Environment Variables
# Hydrated: $(date --iso-8601=seconds)

NODE_ENV=development

# Highlight.io Observability
# HIGHLIGHT_PROJECT_ID=

# Supabase
# SUPABASE_ANON_KEY=

# GitHub (auto-injected in Codespaces)
# GITHUB_TOKEN=
EOF
  log "G£Ù Created placeholder: $ENV_FILE"
}

ensure_manifest() {
  if [[ -f "$MANIFEST_FILE" ]]; then
    log "G£Ù Agent manifest located: $MANIFEST_FILE"
    return
  fi

  log "Agent manifest missing - generating via npm run agents:manifest"
  if ! npm run --silent agents:manifest; then
    log "G•Ó Failed to generate agents manifest"
    exit 1
  fi
}

check_codespaces_secrets() {
  if [[ -z "${CODESPACES:-}" ]]; then
    log "Running outside Codespaces - ensure .env files contain required values."
    return
  fi

  if ! command -v jq >/dev/null 2>&1; then
    log "G‹· jq not found - skipping Codespaces secret verification"
    return
  fi

  log "Detected GitHub Codespaces environment - verifying injected secrets"

  # Get validation results with provenance from validator
  validation_json=$(npm run --silent secrets:validate -- --json 2>/dev/null || echo "")
  if [[ -z "$validation_json" ]]; then
    log "G‹· Could not get validation details - running basic check"
    return
  fi

  # Extract all secrets from provenance (both found and missing)
  mapfile -t all_secrets < <(echo "$validation_json" | jq -r '.provenance | keys[]' 2>/dev/null || echo "")

  for secret in "${all_secrets[@]}"; do
    if [[ -n "${!secret:-}" ]]; then
      log "G£Ù Codespaces secret available: $secret"
    else
      log "G‹· Codespaces secret missing: $secret"
    fi
  done
}

run_validation() {
  log "Running secret validation with provenance tracking..."

  # Run validation and check result
  if npm run --silent secrets:validate -- --json >/dev/null 2>&1; then
    # Validation passed - get provenance info
    npm run --silent secrets:validate -- --json 2>/dev/null | jq -r '.provenance | to_entries[] | "G£Ù Schema source: \(.key) (\(.value) secrets)"' 2>/dev/null || true
    log "G£Ù Secret validation passed"
  else
    # Validation failed - show details
    log "Validation failed, showing missing secrets:"
    npm run --silent secrets:validate -- --json 2>/dev/null | jq -r '.details.missing[] | "G•Ó Missing: \(.name) (from \(.provenance)): \(.description)"' 2>/dev/null || log "Could not parse validation output"
    log "G•Ó Secret validation failed"
    exit 1
  fi
}

heading "Environment Hydration"
ensure_env_file
ensure_manifest
check_codespaces_secrets
run_validation

printf '\nG£Ù Hydration complete\n'