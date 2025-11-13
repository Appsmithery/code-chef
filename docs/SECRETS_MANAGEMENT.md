# Secrets Management

## Local Development

1. Run `./scripts/setup_secrets.sh` to extract secrets from `.env`
2. Secrets are stored in `configs/env/secrets/*.txt` (gitignored)
3. Docker Compose mounts these as `/run/secrets/*` inside containers

## Production Deployment

1. Store secrets in GitHub repository settings (Settings → Secrets)
2. CI/CD workflow writes secrets to `configs/env/secrets/` during deployment
3. Never commit `*.txt` files in `configs/env/secrets/`

## Adding New Secrets

1. Add secret file to `configs/env/secrets/`
2. Update `compose/docker-compose.yml` secrets section
3. Add `*_FILE` env var to service
4. Update `linearConfig.js` (or equivalent) to use `readSecret()`
