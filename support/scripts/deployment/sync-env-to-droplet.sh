#!/bin/bash
# Sync local config/env/.env to production droplet
# Ensures droplet always has latest environment configuration

set -e

DROPLET_HOST="${DROPLET_HOST:-root@45.55.173.72}"
DEPLOY_PATH="${DEPLOY_PATH:-/opt/code-chef}"
LOCAL_ENV_FILE="config/env/.env"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🔄 Syncing environment configuration to droplet"
echo "   Local: ${LOCAL_ENV_FILE}"
echo "   Remote: ${DROPLET_HOST}:${DEPLOY_PATH}/config/env/.env"
echo ""

# Check local .env exists
if [ ! -f "${LOCAL_ENV_FILE}" ]; then
    echo -e "${RED}❌ ERROR: Local .env file not found at ${LOCAL_ENV_FILE}${NC}"
    echo "   Create it from template: cp config/env/.env.template config/env/.env"
    exit 1
fi

# Validate critical variables in local .env
echo "🔍 Validating local .env configuration..."
required_vars=(
    "LLM_PROVIDER"
    "OPENROUTER_API_KEY"
    "LANGCHAIN_API_KEY"
    "QDRANT_URL"
    "QDRANT_API_KEY"
)

missing_vars=()
for var in "${required_vars[@]}"; do
    if ! grep -q "^${var}=" "${LOCAL_ENV_FILE}"; then
        missing_vars+=("$var")
    fi
done

if [ ${#missing_vars[@]} -gt 0 ]; then
    echo -e "${RED}❌ ERROR: Missing required variables in ${LOCAL_ENV_FILE}:${NC}"
    for var in "${missing_vars[@]}"; do
        echo "   - $var"
    done
    exit 1
fi

# Check LLM_PROVIDER is NOT gradient
llm_provider=$(grep "^LLM_PROVIDER=" "${LOCAL_ENV_FILE}" | cut -d'=' -f2)
if [ "$llm_provider" = "gradient" ]; then
    echo -e "${RED}❌ ERROR: LLM_PROVIDER is still set to 'gradient'${NC}"
    echo "   Update ${LOCAL_ENV_FILE} to use 'openrouter'"
    exit 1
fi

echo -e "${GREEN}✓ Local .env validated (LLM_PROVIDER=${llm_provider})${NC}"
echo ""

# Backup existing droplet .env
echo "📦 Creating backup of droplet .env..."
ssh ${DROPLET_HOST} "cd ${DEPLOY_PATH} && \
    [ -f config/env/.env ] && \
    cp config/env/.env config/env/.env.backup.\$(date +%Y%m%d_%H%M%S) || \
    echo 'No existing .env to backup'"

# Upload new .env
echo "📤 Uploading .env to droplet..."
scp "${LOCAL_ENV_FILE}" "${DROPLET_HOST}:${DEPLOY_PATH}/config/env/.env"

# Verify upload
echo "🔍 Verifying upload..."
remote_llm_provider=$(ssh ${DROPLET_HOST} "grep '^LLM_PROVIDER=' ${DEPLOY_PATH}/config/env/.env | cut -d'=' -f2")
if [ "$remote_llm_provider" = "$llm_provider" ]; then
    echo -e "${GREEN}✓ Sync successful! Remote LLM_PROVIDER=${remote_llm_provider}${NC}"
else
    echo -e "${RED}❌ ERROR: Sync verification failed${NC}"
    echo "   Local LLM_PROVIDER: $llm_provider"
    echo "   Remote LLM_PROVIDER: $remote_llm_provider"
    exit 1
fi

echo ""
echo -e "${YELLOW}⚠️  Services need restart to pick up changes${NC}"
echo "   Run: ssh ${DROPLET_HOST} 'cd ${DEPLOY_PATH}/deploy && docker compose restart'"
echo "   Or: ssh ${DROPLET_HOST} 'cd ${DEPLOY_PATH}/deploy && docker compose down && docker compose up -d'"
