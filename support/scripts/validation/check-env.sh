#!/usr/bin/env bash
set -euo pipefail

echo "[ENV] Environment Configuration Status:"

required_vars=(
  "GRADIENT_MODEL_ACCESS_KEY"
  "LANGCHAIN_API_KEY"
  "LANGCHAIN_PROJECT"
  "LINEAR_OAUTH_DEV_TOKEN"
)

env_file="config/env/.env"

if [[ -f "$env_file" ]]; then
  while IFS= read -r line; do
    [[ -z "$line" || "$line" =~ ^# ]] && continue
  done < "$env_file"
  for var in "${required_vars[@]}"; do
    if grep -q "^${var}=" "$env_file"; then
      echo "  [OK] ${var}"
    else
      echo "  [MISSING] ${var}"
    fi
  done
else
  echo "  [ERROR] .env file not found at $env_file"
  for var in "${required_vars[@]}"; do
    echo "  [MISSING] ${var}"
  done
fi
