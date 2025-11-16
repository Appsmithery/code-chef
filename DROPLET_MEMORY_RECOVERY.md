# Droplet Memory Crisis - Recovery Guide

## 🚨 Current Issue: Out of Memory (OOM)

Your droplet console shows multiple processes being killed:

- Node processes (total-vm: 4493MB, 4475MB)
- Snap daemon processes

**Root Cause:** The 2GB droplet is running out of memory with all services running.

---

## 🔧 Immediate Recovery Steps (In Console)

You're in recovery mode. Run these commands:

### 1. Check Current Memory Usage

```bash
free -h
df -h
```

### 2. Check Which Services Are Running

```bash
systemctl list-units --type=service --state=running
```

### 3. Stop All Docker Services Temporarily

```bash
cd /opt/Dev-Tools/compose
docker-compose down
```

This will free up memory immediately.

### 4. Add Swap Space (Critical!)

```bash
# Check if swap exists
swapon --show

# If no swap, create 4GB swap file
fallocate -l 4G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile

# Make it permanent
echo '/swapfile none swap sw 0 0' >> /etc/fstab

# Verify
free -h
```

### 5. Optimize Docker Memory Limits

Edit the docker-compose file to add memory limits:

```bash
cd /opt/Dev-Tools/compose
nano docker-compose.yml
```

Add this to each service:

```yaml
deploy:
  resources:
    limits:
      memory: 256M
    reservations:
      memory: 128M
```

### 6. Start Services Gradually

```bash
# Start infrastructure first
docker-compose up -d postgres qdrant

# Wait 30 seconds
sleep 30

# Start gateway
docker-compose up -d gateway-mcp

# Wait 30 seconds
sleep 30

# Start core agents one by one
docker-compose up -d orchestrator
sleep 15
docker-compose up -d feature-dev
sleep 15
docker-compose up -d code-review
```

---

## 💡 Memory Optimization Strategy

### Option 1: Add Swap (Done Above)

- 4GB swap gives you breathing room
- Slower than RAM but prevents crashes

### Option 2: Reduce Service Count

Only run essential services:

```bash
# Minimal stack (1.2GB total)
docker-compose up -d postgres gateway-mcp orchestrator feature-dev
```

### Option 3: Upgrade Droplet

Recommended: 4GB RAM ($24/month)

```bash
# From DigitalOcean console:
# 1. Power off droplet
# 2. Resize to 4GB plan
# 3. Power on
```

---

## 📊 Memory Budget (2GB Droplet)

**Current Services (estimated):**

- System: ~200MB
- Docker daemon: ~100MB
- PostgreSQL: ~150MB
- Qdrant: ~200MB
- Gateway (Node): ~150MB
- Orchestrator: ~200MB
- Feature-Dev: ~200MB
- Code-Review: ~150MB
- Infrastructure: ~150MB
- CI/CD: ~150MB
- Documentation: ~150MB
- RAG: ~200MB
- **Total: ~2.0GB** ⚠️ TOO MUCH!

**With Swap + Memory Limits:**

- Each agent limited to 256MB
- Swap handles overflow
- Should be stable

---

## 🔍 Check What's Using Memory

```bash
# Top memory consumers
ps aux --sort=-%mem | head -20

# Docker container stats
docker stats --no-stream

# System memory details
cat /proc/meminfo
```

---

## ⚡ Quick Commands Reference

```bash
# Emergency: Stop everything
docker-compose -f /opt/Dev-Tools/compose/docker-compose.yml down

# Add swap
fallocate -l 4G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile

# Start minimal services
cd /opt/Dev-Tools/compose
docker-compose up -d postgres gateway-mcp orchestrator

# Check memory
free -h && docker stats --no-stream

# View logs for OOM issues
dmesg | grep -i "out of memory"
journalctl -u docker --since "1 hour ago" | grep -i oom
```

---

## 🎯 Recommended Solution

1. **Add 4GB swap** (immediate relief)
2. **Update docker-compose.yml** with memory limits
3. **Start only essential services** for now
4. **Upgrade to 4GB droplet** when ready

---

## 📝 Memory-Limited docker-compose.yml

Here's a minimal configuration for 2GB droplet:

```yaml
services:
  postgres:
    # ... existing config ...
    deploy:
      resources:
        limits:
          memory: 200M
        reservations:
          memory: 100M

  gateway-mcp:
    # ... existing config ...
    deploy:
      resources:
        limits:
          memory: 150M
        reservations:
          memory: 100M

  orchestrator:
    # ... existing config ...
    deploy:
      resources:
        limits:
          memory: 256M
        reservations:
          memory: 128M

  feature-dev:
    # ... existing config ...
    deploy:
      resources:
        limits:
          memory: 256M
        reservations:
          memory: 128M
```

---

## 🚀 After Recovery: Deploy Frontend

Once services are stable:

```bash
cd /opt/Dev-Tools
git pull origin main
cd compose
docker-compose restart gateway-mcp
```

---

## 🆘 If Still Having Issues

1. **Reboot in normal mode**

   ```bash
   reboot
   ```

2. **Check logs after reboot**

   ```bash
   dmesg | tail -100
   docker-compose logs --tail=50
   ```

3. **Consider managed database**

   - Move PostgreSQL to DigitalOcean Managed Database
   - Frees up ~150MB

4. **Use Gradient Platform**
   - Offload LLM inference
   - Reduce agent memory footprint
