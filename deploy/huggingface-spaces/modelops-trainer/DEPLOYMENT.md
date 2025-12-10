# HuggingFace Space Deployment Instructions

## 1. Create Space on HuggingFace

1. Go to https://huggingface.co/new-space
2. Fill in details:
   - **Owner**: `appsmithery` (or your organization)
   - **Space name**: `code-chef-modelops-trainer`
   - **License**: `apache-2.0`
   - **SDK**: `Gradio`
   - **Hardware**: `t4-small` (upgrade to `a10g-large` for 3-7B models)
   - **Visibility**: `Private` (recommended) or `Public`

## 2. Configure Secrets

In Space Settings > Variables and secrets:

1. Add secret: `HF_TOKEN`
   - Value: Your HuggingFace write access token from https://huggingface.co/settings/tokens
   - Required permissions: `write` (for pushing trained models)

## 3. Upload Files

Upload these files to the Space repository:

```
code-chef-modelops-trainer/
├── app.py                  # Main application
├── requirements.txt        # Python dependencies
└── README.md              # Space documentation
```

**Option A: Via Web UI**

- Drag and drop files to Space Files tab

**Option B: Via Git**

```bash
# Clone the Space repo
git clone https://huggingface.co/spaces/appsmithery/code-chef-modelops-trainer
cd code-chef-modelops-trainer

# Copy files
cp deploy/huggingface-spaces/modelops-trainer/* .

# Commit and push
git add .
git commit -m "Initial ModelOps trainer deployment"
git push
```

## 4. Verify Deployment

1. Wait for Space to build (2-3 minutes)
2. Check logs for errors
3. Test health endpoint:
   ```bash
   curl https://appsmithery-code-chef-modelops-trainer.hf.space/health
   ```

Expected response:

```json
{
  "status": "healthy",
  "service": "code-chef-modelops-trainer",
  "autotrain_available": true,
  "hf_token_configured": true
}
```

## 5. Update code-chef Configuration

Add Space URL to `config/env/.env`:

```bash
# ModelOps - HuggingFace Space
MODELOPS_SPACE_URL=https://appsmithery-code-chef-modelops-trainer.hf.space
MODELOPS_SPACE_TOKEN=your_hf_token_here
```

## 6. Test from code-chef

Use the client example:

```python
from deploy.huggingface_spaces.modelops_trainer.client_example import ModelOpsTrainerClient

client = ModelOpsTrainerClient(
    space_url=os.environ["MODELOPS_SPACE_URL"],
    hf_token=os.environ["MODELOPS_SPACE_TOKEN"]
)

# Health check
health = client.health_check()
print(health)

# Submit demo job
result = client.submit_training_job(
    agent_name="feature_dev",
    base_model="Qwen/Qwen2.5-Coder-7B",
    dataset_csv_path="/tmp/demo.csv",
    demo_mode=True
)

print(f"Job ID: {result['job_id']}")
```

## 7. Hardware Upgrades

For larger models (3-7B), upgrade hardware:

1. Go to Space Settings
2. Change Hardware to `a10g-large`
3. Note: Cost increases from ~$0.75/hr to ~$2.20/hr

## 8. Monitoring

- **Logs**: Check Space logs for errors
- **TensorBoard**: Each job provides a TensorBoard URL
- **LangSmith**: Client example includes `@traceable` for observability

## 9. Production Considerations

- **Persistence**: Jobs stored in `/tmp` - lost on restart. Use persistent storage or external DB for production
- **Queuing**: Current version runs jobs sequentially. Add job queue (Celery/Redis) for concurrent training
- **Authentication**: Add API key auth for production use
- **Rate Limiting**: Add rate limits to prevent abuse
- **Monitoring**: Set up alerts for failed jobs

## 10. Cost Optimization

- **Auto-scaling**: Set Space to sleep after inactivity
- **Demo mode**: Always test with demo mode first ($0.50 vs $15)
- **Batch jobs**: Train multiple agents in sequence to maximize GPU utilization
- **Local development**: Test locally before deploying to Space

## Troubleshooting

**Space won't build**:

- Check requirements.txt versions
- Verify Python version compatibility (3.9+ recommended)
- Check Space logs for build errors

**Training fails**:

- Verify HF_TOKEN has write permissions
- Check dataset format (must have `text` and `response` columns)
- Ensure model repo exists on HuggingFace Hub

**Out of memory**:

- Enable demo mode to test with smaller dataset
- Use quantization: `int4` or `int8`
- Upgrade to larger GPU (`a10g-large`)
- Reduce `max_seq_length` in config

**Connection timeout**:

- Space may be sleeping - first request wakes it (30s delay)
- Increase client timeout to 60s for first request
