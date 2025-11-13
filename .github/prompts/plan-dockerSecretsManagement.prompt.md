# Enhanced Prompt

You are tasked with implementing a secure and scalable secrets management solution for a multi-agent DevOps stack. Follow the detailed architecture and implementation plan below to externalize secrets effectively. Ensure all steps are completed in sequence, and adhere to the provided best practices for local development and CI/CD integration.

---

## Objective

Implement Docker Compose secrets with bind-mounted environment files for local development, and optionally integrate GitHub repository secrets for CI/CD deployments.

---

## Implementation Plan

### Phase 1: Docker Compose Native Secrets

1. Create a `configs/env/secrets` directory (gitignored).
2. Store sensitive values in `.txt` files within this directory.
3. Update `docker-compose.yml` to mount these files as Docker secrets:

   ```yaml
   services:
     gateway-mcp:
       image: gateway-mcp:latest
       secrets:
         - linear_oauth_token
         - linear_webhook_secret
       environment:
         LINEAR_OAUTH_DEV_TOKEN_FILE: /run/secrets/linear_oauth_token
         LINEAR_WEBHOOK_SIGNING_SECRET_FILE: /run/secrets/linear_webhook_secret

   secrets:
     linear_oauth_token:
       file: ../configs/env/secrets/linear_oauth_token.txt
     linear_webhook_secret:
       file: ../configs/env/secrets/linear_webhook_secret.txt
   ```

### Phase 2: Update Application to Read Secrets

1. Modify the application to prioritize `*_FILE` environment variables:

   ```javascript
   import { readFileSync } from "fs";

   function readSecret(envVar) {
     const filePath = process.env[`${envVar}_FILE`];
     return filePath
       ? readFileSync(filePath, "utf8").trim()
       : process.env[envVar];
   }

   export const linearConfig = {
     oauth: {
       clientSecret: readSecret("LINEAR_OAUTH_CLIENT_SECRET"),
       devToken: readSecret("LINEAR_OAUTH_DEV_TOKEN"),
     },
     webhook: {
       signingSecret: readSecret("LINEAR_WEBHOOK_SIGNING_SECRET"),
     },
   };
   ```

### Phase 3: Setup Script for Local Secrets

1. Create a script (`setup_secrets.sh`) to automate local secrets setup:

   ```bash
   #!/usr/bin/env bash
   set -euo pipefail
   SECRETS_DIR="configs/env/secrets"
   mkdir -p "$SECRETS_DIR"

   if [ -f ".env" ]; then
     grep "^LINEAR_OAUTH_DEV_TOKEN=" .env | cut -d= -f2 > "$SECRETS_DIR/linear_oauth_token.txt"
     grep "^LINEAR_WEBHOOK_SIGNING_SECRET=" .env | cut -d= -f2 > "$SECRETS_DIR/linear_webhook_secret.txt"
   else
     echo "LINEAR_OAUTH_DEV_TOKEN=your_token_here" > "$SECRETS_DIR/linear_oauth_token.txt"
     echo "LINEAR_WEBHOOK_SIGNING_SECRET=your_secret_here" > "$SECRETS_DIR/linear_webhook_secret.txt"
   fi

   chmod 600 "$SECRETS_DIR"/*.txt
   ```

### Phase 4: CI/CD Integration (Optional)

1. Configure GitHub repository secrets.
2. Update the CI/CD workflow to inject secrets during deployment:
   ```yaml
   - name: Write secrets to files
     run: |
       mkdir -p configs/env/secrets
       echo "${{ secrets.LINEAR_OAUTH_DEV_TOKEN }}" > configs/env/secrets/linear_oauth_token.txt
       echo "${{ secrets.LINEAR_WEBHOOK_SIGNING_SECRET }}" > configs/env/secrets/linear_webhook_secret.txt
       chmod 600 configs/env/secrets/*.txt
   ```

### Phase 5: Documentation

1. Document the secrets management process for both local development and production deployment.

---

## Next Steps

1. Execute `./scripts/setup_secrets.sh` to migrate `.env` secrets.
2. Update `docker-compose.yml` with the secrets configuration.
3. Test the setup locally using `make rebuild && make up`.
4. Configure GitHub repository secrets for CI/CD (if applicable).
5. Remove sensitive values from `.env` after confirming functionality.

Would you like to proceed with Phase 1, or should I assist with generating the required files?
