# Docker Compose Migration - Qdrant Cloud

**Date**: 2025-01-28  
**Goal**: Remove local Qdrant container, use Qdrant Cloud exclusively

## Changes to Make

### 1. Remove Qdrant Service from docker-compose.yml

**Current (lines 219-230)**:

```yaml
# Qdrant Vector Database
qdrant:
  image: qdrant/qdrant:latest
  ports:
    - "6333:6333"
    - "6334:6334"
  environment:
    - QDRANT__SERVICE__GRPC_PORT=6334
  networks:
    - devtools-network
  volumes:
    - qdrant-data:/qdrant/storage
```

**Action**: Comment out or delete this entire service block

### 2. Remove Qdrant Volume

**Current (volumes section at bottom)**:

```yaml
volumes:
  orchestrator-data:
  mcp-config:
  qdrant-data: # <-- Remove this line
  postgres-data:
```

**Action**: Remove `qdrant-data:` line

### 3. Update RAG Service Dependencies

**Current rag-context service**:

```yaml
rag-context:
  # ... build config ...
  depends_on:
    - qdrant # <-- Remove this dependency
    - postgres
```

**Action**: Remove `- qdrant` from depends_on list

### 4. Update RAG Environment Variables

**Current**:

```yaml
rag-context:
  environment:
    - QDRANT_HOST=qdrant # <-- Change to cloud URL
    - QDRANT_PORT=6333 # <-- Remove (cloud uses HTTPS)
```

**New**:

```yaml
rag-context:
  environment:
    - QDRANT_URL=${QDRANT_URL}
    - QDRANT_API_KEY=${QDRANT_API_KEY}
    - QDRANT_COLLECTION=${QDRANT_COLLECTION:-the-shop}
```

## Implementation Steps

### Local Testing First

1. **Verify Qdrant Cloud credentials in .env**:

   ```bash
   grep QDRANT config/env/.env
   # Should see: QDRANT_URL, QDRANT_API_KEY, QDRANT_COLLECTION
   ```

2. **Test Qdrant Cloud connection**:

   ```python
   from agents._shared.qdrant_client import get_qdrant_client

   client = get_qdrant_client()
   if client.is_enabled():
       info = await client.get_collection_info()
       print(f"Connected: {info}")
   ```

3. **Update local docker-compose.yml**:

   - Comment out qdrant service (use `# ` prefix)
   - Keep volume for now (for rollback)
   - Update rag-context environment

4. **Rebuild affected services**:

   ```powershell
   cd compose
   docker-compose build rag-context orchestrator
   ```

5. **Test locally**:

   ```powershell
   docker-compose down
   docker-compose up -d postgres gateway-mcp orchestrator rag-context

   # Check health
   curl http://localhost:8001/health
   curl http://localhost:8007/health

   # Check Qdrant Cloud connection in logs
   docker-compose logs rag-context | grep -i qdrant
   ```

### Droplet Deployment

6. **Commit changes locally**:

   ```powershell
   git add compose/docker-compose.yml agents/orchestrator/requirements.txt
   git commit -m "feat: migrate to Qdrant Cloud, add LangGraph infrastructure"
   git push origin main
   ```

7. **Deploy to droplet** (after reboot):

   ```bash
   ssh alex@45.55.173.72
   cd /opt/Dev-Tools

   # Pull latest changes
   git pull origin main

   # Rebuild services
   cd compose
   docker-compose build rag-context orchestrator

   # Selective startup (see DROPLET_REBOOT_PROCEDURE.md)
   docker-compose up -d postgres gateway-mcp
   docker-compose up -d orchestrator
   docker-compose up -d rag-context
   ```

8. **Verify cloud connection**:

   ```bash
   # Check orchestrator health
   curl http://localhost:8001/health

   # Check RAG health
   curl http://localhost:8007/health

   # Check logs for Qdrant Cloud connection
   docker-compose logs orchestrator | grep -i qdrant
   docker-compose logs rag-context | grep -i qdrant
   ```

## Rollback Plan

If Qdrant Cloud connection fails:

1. **Restore local Qdrant**:

   - Uncomment qdrant service in docker-compose.yml
   - Add back qdrant-data volume
   - Revert rag-context environment variables

2. **Rebuild and restart**:
   ```bash
   docker-compose down
   docker-compose build rag-context
   docker-compose up -d postgres qdrant gateway-mcp rag-context
   ```

## Memory Savings

**Before**:

- qdrant container: ~350MB RAM
- Total with local Qdrant: ~2.5GB

**After**:

- qdrant container: REMOVED
- Total without local Qdrant: ~2.15GB
- **Savings: 350MB (14% reduction)**

## Next Migration Phase

After Qdrant Cloud is stable:

- Implement unified workflow consolidation
- Target 3 containers: unified-workflow, postgres, gateway
- Expected total: ~850MB RAM
- **Total savings: ~1.65GB (66% reduction)**

## Validation Checklist

- [ ] Qdrant Cloud credentials in .env
- [ ] Test connection with qdrant_client.py
- [ ] docker-compose.yml updated (qdrant service commented/removed)
- [ ] rag-context environment variables updated
- [ ] Local testing passes
- [ ] Changes committed to git
- [ ] Deployed to droplet
- [ ] Health checks pass on droplet
- [ ] Logs show "Qdrant Cloud client initialized"
- [ ] No errors in rag-context logs
- [ ] Vector search working (test with /api/rag/search endpoint)

## Timeline

1. **Now**: Local changes and testing
2. **After droplet reboot**: Deploy to production
3. **Monitor**: 24 hours for stability
4. **Phase 2**: Remove qdrant-data volume permanently
5. **Phase 3**: Unified workflow consolidation
