#!/usr/bin/env bash
set -euo pipefail

SECRETS_DIR="configs/env/secrets"
mkdir -p "$SECRETS_DIR"

echo "Setting up local secrets (gitignored)..."

# Prompt or copy from .env
if [ -f ".env" ]; then
  grep "^LINEAR_OAUTH_DEV_TOKEN=" .env | cut -d= -f2 > "$SECRETS_DIR/linear_oauth_token.txt"
  grep "^LINEAR_WEBHOOK_SIGNING_SECRET=" .env | cut -d= -f2 > "$SECRETS_DIR/linear_webhook_secret.txt"
  echo "✓ Secrets extracted from .env"
else
  echo "LINEAR_OAUTH_DEV_TOKEN=your_token_here" > "$SECRETS_DIR/linear_oauth_token.txt"
  echo "LINEAR_WEBHOOK_SIGNING_SECRET=your_secret_here" > "$SECRETS_DIR/linear_webhook_secret.txt"
  echo "⚠ Created placeholder secrets. Edit files in $SECRETS_DIR"
fi

chmod 600 "$SECRETS_DIR"/*.txt
echo "✓ Secrets secured (600 permissions)"