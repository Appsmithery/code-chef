# GitHub Secrets Setup Guide

## Quick Setup (Copy-Paste Ready)

Go to: **https://github.com/Appsmithery/Dev-Tools/settings/secrets/actions/new**

### 1. Docker Hub Authentication

**Name:** `DOCKER_USERNAME`  
**Value:**

```
alextorelli28
```

**Name:** `DOCKER_HUB_TOKEN`  
**Value:**

```
dckr_pat_b2YnSaHZWoz3GqBnM245NsHBr7g
```

### 2. Langfuse (LLM Observability)

**Name:** `LANGFUSE_SECRET_KEY`  
**Value:**

```
sk-lf-51d46621-1aff-4867-be1f-66450c44ef8c
```

**Name:** `LANGFUSE_PUBLIC_KEY`  
**Value:**

```
pk-lf-7029904c-4cc7-44c4-a470-aa73f1e6a745
```

### 3. DigitalOcean Gradient AI

**Name:** `GRADIENT_API_KEY`  
**Value:**

```
dop_v1_21565d5f63b515138cae71c2815df3ca6dd95cec7587dca513fab11c7e5589ee
```

### 4. Linear Integration (Optional)

**Name:** `LINEAR_OAUTH_DEV_TOKEN`  
**Value:**

```
lin_oauth_8f8990917b7e520efcd51f8ebe84055a251f53f8738bb526c8f2fac8ff0a1571
```

### 5. Qdrant Vector DB (Optional)

**Name:** `QDRANT_API_KEY`  
**Value:**

```
627d4d41-8ab9-4426-80a9-981ae49d1238|dxU9Sds4KrMZ3a-lalClB3sxK60jjQtywi3RFmJs9gxWvw1eCuCILQ
```

**Name:** `QDRANT_URL`  
**Value:**

```
https://83b61795-7dbd-4477-890e-edce352a00e2.us-east4-0.gcp.cloud.qdrant.io
```

### 6. Database

**Name:** `DB_PASSWORD`  
**Value:**

```
changeme
```

_(⚠️ Change this in production!)_

### 7. Droplet SSH Key

**Name:** `DROPLET_SSH_KEY`  
**Value:**

```
-----BEGIN OPENSSH PRIVATE KEY-----
[Your private SSH key content here]
-----END OPENSSH PRIVATE KEY-----
```

**To get your SSH key:**

```powershell
# Windows
Get-Content $env:USERPROFILE\.ssh\id_rsa
# or
Get-Content $env:USERPROFILE\.ssh\id_ed25519
```

---

## Verification Checklist

After adding all secrets, verify at: https://github.com/Appsmithery/Dev-Tools/settings/secrets/actions

You should see:

- ✅ DOCKER_USERNAME
- ✅ DOCKER_HUB_TOKEN
- ✅ LANGFUSE_SECRET_KEY
- ✅ LANGFUSE_PUBLIC_KEY
- ✅ GRADIENT_API_KEY
- ✅ LINEAR_OAUTH_DEV_TOKEN
- ✅ QDRANT_API_KEY
- ✅ QDRANT_URL
- ✅ DB_PASSWORD
- ✅ DROPLET_SSH_KEY

**Total: 10 secrets**

---

## Test the Pipeline

Once all secrets are configured:

```bash
# Commit and push to trigger workflow
git add .
git commit -m "feat: complete v2.0 Docker Hub migration"
git push origin main
```

Monitor at: https://github.com/Appsmithery/Dev-Tools/actions

Expected workflow:

1. **build-and-push** job: ~10-15 minutes
   - Checkout code
   - Login to Docker Hub
   - Build all services
   - Push to alextorelli28/appsmithery
2. **deploy** job: ~3-5 minutes
   - SSH to droplet
   - Pull images from Docker Hub
   - Restart services
   - Validate health

---

## SSH Key Setup for Droplet

If you don't have SSH access set up yet:

### Generate SSH Key (if needed)

```powershell
ssh-keygen -t ed25519 -C "github-actions@dev-tools"
```

### Add to Droplet

```bash
# Copy public key
Get-Content $env:USERPROFILE\.ssh\id_ed25519.pub | Set-Clipboard

# SSH to droplet
ssh root@45.55.173.72

# Add to authorized_keys
echo "paste-your-public-key-here" >> ~/.ssh/authorized_keys
```

### Add Private Key to GitHub Secret

```powershell
# Copy private key (entire content including BEGIN/END lines)
Get-Content $env:USERPROFILE\.ssh\id_ed25519
```

Paste into GitHub Secret: `DROPLET_SSH_KEY`

---

## Troubleshooting

### Secret Not Working

- Ensure no extra spaces or newlines
- For multi-line secrets (SSH key), include BEGIN/END markers
- Secret names are case-sensitive

### Workflow Fails on SSH

- Verify SSH key has access: `ssh -i ~/.ssh/id_ed25519 root@45.55.173.72`
- Check known_hosts: `ssh-keyscan -H 45.55.173.72`
- Ensure key format is OpenSSH (not PEM)

### Docker Hub Push Fails

- Verify token has Read, Write, Delete permissions
- Check token hasn't expired: https://hub.docker.com/settings/security
- Test locally: `echo $TOKEN | docker login -u alextorelli28 --password-stdin`
