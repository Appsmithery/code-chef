# Infrastructure Agent

The Infrastructure Agent is responsible for Infrastructure as Code (IaC), containerization, Terraform deployments, and the ModelOps extension.

## Core Capabilities

### Infrastructure as Code

- Terraform configuration and deployment
- Docker Compose orchestration
- Kubernetes manifests
- Cloud resource provisioning

### Container Management

- Docker image building and deployment
- Container health monitoring
- Network configuration
- Volume management

### ModelOps Extension

**Complete model training and deployment lifecycle for fine-tuning agent models.**

#### Training

- **HuggingFace AutoTrain Advanced** integration via Space API
- **Demo mode**: $0.50, 5 minutes (100 examples)
- **Production mode**: $3.50-$15, 90 minutes (full dataset)
- Automatic GPU selection, LoRA configuration, progress monitoring
- Real-time training status with cost tracking

#### Evaluation

- **LangSmith-based comparison** using existing evaluators
- **Weighted scoring**: 30% accuracy, 25% completeness, 20% efficiency, 15% latency, 10% integration
- **Automatic recommendations**: deploy, deploy_canary, needs_review, reject
- Side-by-side model comparison reports

#### Deployment

- **Immediate deployment** (100%) with rollback support
- **Automatic config updates** to `config/agents/models.yaml`
- **Version backups** with <60 second rollback capability
- **Thread-safe registry** operations

#### Registry

- **Version tracking** in `config/models/registry.json`
- **Pydantic validation** for schema consistency
- **GGUF conversion** support for local deployment
- **Rollback history** with deployment metadata

## ModelOps Architecture

```
InfrastructureAgent
└─> handle_modelops_request() [Intelligent parsing]
    └─> ModelOpsCoordinator
        ├─> ModelOpsTrainer (training.py)
        ├─> ModelEvaluator (evaluation.py)
        ├─> ModelOpsDeployment (deployment.py)
        └─> ModelRegistry (registry.json)
```

## VS Code Integration

The ModelOps extension provides 5 VS Code commands:

1. **Train Model** (`codechef.modelops.trainModel`)

   - Training wizard with cost estimation
   - Real-time progress monitoring
   - AutoTrain job management

2. **Evaluate Models** (`codechef.modelops.evaluateModels`)

   - Model comparison interface
   - Evaluation results visualization
   - Deployment recommendations

3. **Deploy Model** (`codechef.modelops.deployModel`)

   - One-click deployment
   - Config backup and rollback
   - Version management

4. **View Model History** (`codechef.modelops.viewModelHistory`)

   - Version timeline
   - Performance metrics
   - Rollback interface

5. **Convert to GGUF** (`codechef.modelops.convertToGGUF`)
   - Local deployment preparation
   - Quantization options
   - Download management

## Configuration

### Model Registry (`config/models/registry.json`)

```json
{
  "models": [
    {
      "agent": "feature_dev",
      "model_id": "gradient/codellama-13b",
      "version": "v1.2.0",
      "deployed_at": "2024-01-15T10:30:00Z",
      "evaluation_score": 0.85,
      "training_job_id": "train_abc123"
    }
  ]
}
```

### Training Defaults (`config/modelops/training_defaults.yaml`)

```yaml
demo_mode:
  num_samples: 100
  cost: 0.50
  duration_minutes: 5

production_mode:
  num_samples: 1000
  cost: 3.50
  duration_minutes: 90

lora_config:
  r: 16
  alpha: 32
  dropout: 0.1
```

## Tool Integration

The Infrastructure Agent uses progressive tool loading:

- **Terraform** tools for IaC deployment
- **Docker** tools for container management
- **ModelOps** tools for training/evaluation/deployment
- **Linear** tools for issue tracking (production requirement)

## Error Handling

All ModelOps operations include:

- **Structured error responses** with specific error codes
- **Automatic rollback** on deployment failures
- **Cost protection** with pre-flight validation
- **Thread-safe operations** preventing race conditions

## Files Structure

```
agents/infrastructure/
├── __init__.py              # Main agent with ModelOps routing
├── system.prompt.md         # Agent instructions
├── tools.yaml              # Tool configuration
└── modelops/
    ├── coordinator.py       # Request routing and JSON responses
    ├── training.py          # AutoTrain integration
    ├── evaluation.py        # LangSmith comparison
    ├── deployment.py        # Config management
    └── registry.py          # Version tracking
```
