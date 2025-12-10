# Manual HuggingFace Space Deployment

Since automated deployment requires HuggingFace CLI authentication, please deploy manually:

## Option 1: Web UI (Fastest - 5 minutes)

1. Go to https://huggingface.co/new-space
2. Configure:
   - **Owner**: Alextorelli
   - **Space name**: `code-chef-modelops-trainer`
   - **License**: MIT
   - **Select the SDK**: Gradio
   - **Hardware**: CPU basic (free) - upgrade to t4-small later
   - **Visibility**: Private
3. Click **Create Space**
4. Upload these 7 files from `deploy/huggingface-spaces/modelops-trainer/`:
   - `app.py`
   - `requirements.txt`
   - `README.md`
   - `DEPLOYMENT.md`
   - `QUICKSTART.md`
   - `client_example.py`
   - `.spaceignore`
5. Go to **Settings → Variables and secrets**
6. Add secret:
   - **Name**: `HF_TOKEN`
   - **Value**: Your HuggingFace token from https://huggingface.co/settings/tokens
7. Wait 2-3 minutes for build
8. Test: Visit https://alextorelli-code-chef-modelops-trainer.hf.space/health

## Option 2: CLI (After `huggingface-cli login`)

```powershell
# Login first
huggingface-cli login

# Then run deployment script
cd D:\APPS\code-chef
python deploy\huggingface-spaces\modelops-trainer\deploy_space.py
```

## After Deployment

Update `config/env/.env` (create if needed):
```env
MODELOPS_SPACE_URL=https://alextorelli-code-chef-modelops-trainer.hf.space
HUGGINGFACE_TOKEN=your_token_here
```

## Space URL

Once deployed, your Space will be at:
- **Web UI**: https://huggingface.co/spaces/Alextorelli/code-chef-modelops-trainer
- **API Endpoint**: https://alextorelli-code-chef-modelops-trainer.hf.space
- **Health Check**: https://alextorelli-code-chef-modelops-trainer.hf.space/health

---

**Proceeding with Phase 1 implementation in parallel...**
