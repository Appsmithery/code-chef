# Docker Cleanup Guide

**Purpose:** Optimize Docker resources before deploying to DigitalOcean droplet  
**Target:** Reduce disk usage and prevent deployment issues  
**Estimated Time:** 5-10 minutes

---

## 🎯 When to Clean

### ✅ Clean Before Deployment If:

- First time deploying to droplet
- Droplet disk space low (check with `df -h`)
- Many old/unused containers/images from previous projects
- Docker taking excessive disk space (check with `docker system df`)

### ⚠️ Skip Cleanup If:

- Fresh droplet install with only Dev-Tools
- Disk space adequate (>10GB free)
- No other Docker projects on droplet
- Recent clean deployment

---

## 📊 Check Current Usage

```bash
# Overall Docker disk usage
docker system df

# Detailed breakdown
docker system df -v

# Check droplet disk space
df -h
```

**Interpretation:**

- `Images`: Built container images
- `Containers`: Running/stopped container instances
- `Local Volumes`: Persistent data (databases, configs)
- `Build Cache`: Layer cache from builds

---

## 🧹 Cleanup Options

### Option 1: Conservative Cleanup (Recommended)

**What it does:** Removes only stopped containers, dangling images, unused networks, build cache  
**What it keeps:** Running containers, named volumes (data preserved)  
**Risk:** Low - no data loss

```bash
# Stop Dev-Tools services first
cd /opt/code-chef/compose
docker-compose down

# Remove stopped containers
docker container prune -f

# Remove dangling images (untagged/unreferenced)
docker image prune -f

# Remove unused networks
docker network prune -f

# Remove build cache
docker builder prune -f
```

**Expected savings:** 1-5 GB depending on previous usage

### Option 2: Aggressive Cleanup (More Space)

**What it does:** Removes ALL unused images (not just dangling), build cache  
**What it keeps:** Named volumes (data preserved)  
**Risk:** Medium - will re-download base images on next build

```bash
# Stop Dev-Tools services
cd /opt/code-chef/compose
docker-compose down

# Remove ALL unused images (including base images)
docker image prune -a -f

# Remove build cache
docker builder prune -a -f

# Remove stopped containers
docker container prune -f

# Remove unused networks
docker network prune -f
```

**Expected savings:** 5-15 GB depending on cached images

### Option 3: Nuclear Cleanup (Maximum Space)

**What it does:** Removes EVERYTHING except named volumes  
**What it keeps:** ONLY named volumes (databases, configs)  
**Risk:** High - removes all images, containers, networks, cache

```bash
# Stop Dev-Tools services
cd /opt/code-chef/compose
docker-compose down

# Remove EVERYTHING (except volumes)
docker system prune -a -f

# Or individual commands:
docker container prune -f
docker image prune -a -f
docker network prune -f
docker builder prune -a -f
```

**Expected savings:** 10-30 GB depending on previous usage

### Option 4: FULL RESET (Includes Data)

**⚠️ DANGER:** This removes EVERYTHING including databases and persistent data!  
**Use only if:** Starting completely fresh, no data to preserve

```bash
# STOP! Are you sure? This deletes ALL data!
# Backup first: ./scripts/backup_volumes.sh

cd /opt/code-chef/compose
docker-compose down -v  # -v flag removes volumes

# Remove everything
docker system prune -a --volumes -f
```

**Expected savings:** 15-50 GB (everything deleted)

---

## 🎯 Recommended Workflow

### For First Deployment to Droplet:

```bash
# SSH to droplet
ssh do-codechef-droplet

# Check current usage
docker system df
df -h

# If disk usage > 50% or < 10GB free:
docker system prune -a -f

# Clone/update repo
cd /opt/Dev-Tools
git pull origin main

# Deploy
cd compose
docker-compose build
docker-compose up -d
```

### For Local Development Machine:

```bash
# Conservative cleanup (safe, frequent)
docker system prune -f

# Or aggressive cleanup (before major work)
docker system prune -a -f
```

---

## 💾 Volume Management

### Check Volumes

```bash
# List all volumes
docker volume ls

# Inspect specific volume
docker volume inspect <volume-name>

# Check size
docker system df -v | grep -A 20 "Local Volumes"
```

### Dev-Tools Volumes (DO NOT DELETE)

These contain critical data:

- `compose_orchestrator-data` - Task state and workflow history
- `compose_mcp-config` - MCP gateway configuration
- `compose_qdrant-data` - Vector database (RAG contexts)
- `compose_postgres-data` - Workflow state database
- `compose_prometheus-data` - Metrics history

### Backup Before Cleanup

```bash
# Backup all volumes
cd /opt/Dev-Tools
./scripts/backup_volumes.sh

# Backups saved to: ./backups/<timestamp>/
```

### Remove Unused Volumes (CAREFUL!)

```bash
# List unused volumes
docker volume ls -f dangling=true

# Remove ONLY unused volumes (not named in docker-compose.yml)
docker volume prune -f

# DO NOT run "docker volume rm <compose-volume>" unless you want to lose data!
```

---

## 🔍 Verification

After cleanup, verify:

```bash
# Check space saved
docker system df
df -h

# Ensure no running Dev-Tools containers (should be stopped for cleanup)
docker ps -a | grep compose

# Ensure volumes preserved
docker volume ls | grep compose
# Should see: orchestrator-data, mcp-config, qdrant-data, postgres-data, prometheus-data
```

---

## 🚀 Post-Cleanup Deployment

```bash
# Navigate to compose directory
cd /opt/Dev-Tools/compose

# Build fresh images (will download base images if cleaned)
docker-compose build

# Start services
docker-compose up -d

# Wait for initialization
sleep 15

# Verify health
docker-compose ps
curl http://localhost:8001/health | jq .
```

**Note:** First build after aggressive cleanup takes longer (5-10 min) due to re-downloading base images.

---

## 📋 Cleanup Checklist

Before deploying to droplet:

- [ ] Check disk space: `df -h` (need >10GB free)
- [ ] Check Docker usage: `docker system df`
- [ ] Backup volumes: `./scripts/backup_volumes.sh` (if data exists)
- [ ] Stop services: `docker-compose down`
- [ ] Run cleanup: Choose option 1, 2, or 3 above
- [ ] Verify volumes preserved: `docker volume ls | grep compose`
- [ ] Deploy: `docker-compose build && docker-compose up -d`
- [ ] Verify health: Check all `/health` endpoints

---

## 🆘 Troubleshooting

### "No space left on device" during build

```bash
# Aggressive cleanup
docker system prune -a -f

# Check space
df -h

# If still low, check logs taking space
sudo du -sh /var/lib/docker/*
sudo journalctl --vacuum-size=100M  # Clean system logs
```

### Lost data after cleanup

```bash
# Restore from backup
cd /opt/Dev-Tools
./scripts/restore_volumes.sh ./backups/<timestamp>/

# Restart services
cd compose
docker-compose up -d
```

### Build fails after cleanup

```bash
# Likely network/download issue, retry:
docker-compose build --no-cache

# Or build specific service:
docker-compose build --no-cache <service-name>
```

---

## 💡 Best Practices

1. **Regular Cleanup**: Run `docker system prune -f` weekly on development machines
2. **Pre-Deployment Cleanup**: Run option 1 or 2 before deploying to droplet
3. **Backup Before Cleanup**: Always run `./scripts/backup_volumes.sh` if data exists
4. **Monitor Disk Usage**: Check `docker system df` and `df -h` regularly
5. **Preserve Volumes**: Never run `docker-compose down -v` unless intentionally resetting
6. **Build Cache**: Keep build cache for faster rebuilds unless space constrained

---

## 📊 Expected Results

| Cleanup Option | Time    | Space Saved | Risk     | Rebuild Time     |
| -------------- | ------- | ----------- | -------- | ---------------- |
| Conservative   | 1-2 min | 1-5 GB      | Low      | Normal (2-3 min) |
| Aggressive     | 2-3 min | 5-15 GB     | Medium   | Slow (5-10 min)  |
| Nuclear        | 3-5 min | 10-30 GB    | High     | Slow (5-10 min)  |
| Full Reset     | 3-5 min | 15-50 GB    | Critical | Slow (5-10 min)  |

---

## 🎯 Recommendation

**For Droplet Deployment:**

Use **Option 1 (Conservative)** if:

- Disk space > 10GB free
- Other projects on droplet need their images

Use **Option 2 (Aggressive)** if:

- Disk space < 10GB free
- Only Dev-Tools on droplet
- Fast internet for re-downloading images

**For Local Development:**

Use **Option 1 (Conservative)** regularly (weekly)

---

**Ready to clean and deploy!** 🧹🚀
