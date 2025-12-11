"""
LangSmith dataset creation for E2E evaluation.

Seeds datasets from IB-Agent Platform implementation scenarios.
Used for automated evaluation of code-chef agent routing and quality.

Usage:
    python support/tests/e2e/langsmith_datasets.py [--recreate]

Linear Issue: DEV-195
Test Project: https://github.com/Appsmithery/IB-Agent
"""

import argparse
import logging
import os
from typing import Any, Dict, List

from langsmith import Client

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Load .env if available
try:
    from dotenv import load_dotenv

    load_dotenv("config/env/.env")
except ImportError:
    pass

# Initialize LangSmith client with workspace ID for org-scoped API keys
# Workspace ID from: https://smith.langchain.com/o/5029c640-3f73-480c-82f3-58e402ed4207
LANGSMITH_WORKSPACE_ID = os.getenv(
    "LANGSMITH_WORKSPACE_ID", "5029c640-3f73-480c-82f3-58e402ed4207"
)

# Set headers for org-scoped API keys
os.environ.setdefault("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")

client = Client(
    api_key=os.getenv("LANGCHAIN_API_KEY"),
    # Workspace ID header required for org-scoped API keys
)

# =============================================================================
# IB-AGENT PLATFORM SCENARIOS
# Mapped to code-chef agent nodes for routing validation
# =============================================================================

IB_AGENT_SCENARIOS: List[Dict[str, Any]] = [
    # =========================================================================
    # Phase 1: Data Layer Foundation (MCP Servers)
    # =========================================================================
    {
        "task": "Build EDGAR MCP server with search_filings tool that queries SEC EDGAR API for 10-K, 10-Q, and 8-K filings by ticker",
        "expected_agents": ["feature_dev", "code_review"],
        "risk_level": "high",
        "ib_agent_step": "1.3",
        "expected_steps": ["feature_dev_node", "code_review_node", "test_generate"],
        "description": "Create fastmcp server with rate limiting, caching, and proper SEC User-Agent header",
    },
    {
        "task": "Configure Qdrant collection 'ib-agent-filings' with 1536-dimension vectors for SEC filing embeddings using HNSW indexing",
        "expected_agents": ["infrastructure"],
        "risk_level": "medium",
        "ib_agent_step": "1.4",
        "expected_steps": ["infrastructure_check", "docker_validate"],
        "description": "Setup vector DB with payload indexes for ticker, form_type, and fiscal_year",
    },
    {
        "task": "Clone Nasdaq Data Link MCP server repository and integrate into docker-compose.yml with proper network configuration",
        "expected_agents": ["infrastructure", "cicd"],
        "risk_level": "medium",
        "ib_agent_step": "1.2",
        "expected_steps": ["infrastructure_check", "docker_validate", "mcp_health"],
        "description": "Add pre-built MCP server for World Bank, Equities 360, and RTAT datasets",
    },
    {
        "task": "Write docker-compose.yml for IB Agent stack with backend, qdrant, postgres, traefik, and mcp-servers services",
        "expected_agents": ["infrastructure"],
        "risk_level": "medium",
        "ib_agent_step": "1.1",
        "expected_steps": ["infrastructure_check", "docker_validate"],
        "description": "Configure internal bridge network, volume mounts, and health checks",
    },
    # =========================================================================
    # Phase 2: Core Agent Development
    # =========================================================================
    {
        "task": "Implement CompsAgent with LangGraph StateGraph workflow: get_fundamentals -> screen_peers -> enrich_data -> calculate_multiples -> rank_results",
        "expected_agents": ["feature_dev", "code_review"],
        "risk_level": "high",
        "ib_agent_step": "2.2",
        "expected_steps": ["feature_dev_node", "code_review_node", "test_generate"],
        "description": "Build comparable company analysis agent with MCP tool integration",
    },
    {
        "task": "Build RAG ingestion pipeline for 10-K filings with semantic chunking by SEC Item headers (Item 1, 1A, 7, etc.)",
        "expected_agents": ["feature_dev"],
        "risk_level": "medium",
        "ib_agent_step": "2.3",
        "expected_steps": ["feature_dev_node", "test_generate"],
        "description": "Create ingest_filings.py with OpenAI embeddings and Qdrant upsert",
    },
    {
        "task": "Create POST /api/v1/research/comps FastAPI endpoint with async BackgroundTask execution and task polling",
        "expected_agents": ["feature_dev", "code_review"],
        "risk_level": "medium",
        "ib_agent_step": "2.1",
        "expected_steps": ["feature_dev_node", "code_review_node", "test_generate"],
        "description": "Implement headless analyst API with task store for workflow tracking",
    },
    {
        "task": "Add TaskStore class for async workflow tracking with status, progress updates, and result storage",
        "expected_agents": ["feature_dev"],
        "risk_level": "low",
        "ib_agent_step": "2.1",
        "expected_steps": ["feature_dev_node"],
        "description": "In-memory store with optional Redis backend for production",
    },
    # =========================================================================
    # Phase 3: UI Integration
    # =========================================================================
    {
        "task": "Update Chainlit UI on_message handler to call /api/v1/research/comps and display results as interactive table",
        "expected_agents": ["feature_dev"],
        "risk_level": "low",
        "ib_agent_step": "3.1",
        "expected_steps": ["feature_dev_node"],
        "description": "Add intent detection for comps, macro, and filing queries",
    },
    {
        "task": "Implement Excel export service with openpyxl for downloadable comps analysis results",
        "expected_agents": ["feature_dev", "code_review"],
        "risk_level": "medium",
        "ib_agent_step": "3.2",
        "expected_steps": ["feature_dev_node", "code_review_node"],
        "description": "Create /api/v1/export/excel/{task_id} endpoint",
    },
    # =========================================================================
    # Phase 4: Excel Add-in ("The Sidecar")
    # =========================================================================
    {
        "task": "Create Office.js manifest.xml for Excel Add-in with ReadWriteDocument permissions and Traefik HTTPS hosting",
        "expected_agents": ["feature_dev"],
        "risk_level": "high",
        "ib_agent_step": "4.1",
        "expected_steps": ["feature_dev_node", "code_review_node", "security_scan"],
        "description": "Configure task pane add-in for Excel 2016+, Windows/Mac, and Excel Online",
    },
    {
        "task": "Build React task pane with Excel.run() API for reading selected ticker and writing comps table to workbook",
        "expected_agents": ["feature_dev", "code_review"],
        "risk_level": "high",
        "ib_agent_step": "4.2",
        "expected_steps": ["feature_dev_node", "code_review_node", "security_scan"],
        "description": "Implement bidirectional Excel integration with WebSocket progress streaming",
    },
    # =========================================================================
    # ModelOps Extension: Model Training and Deployment
    # =========================================================================
    {
        "task": "Train a fine-tuned CodeLlama model using AutoTrain with demo mode for feature_dev agent",
        "expected_agents": ["infrastructure"],
        "risk_level": "medium",
        "ib_agent_step": "modelops.1",
        "expected_steps": ["infrastructure_check", "modelops_train"],
        "description": "Initiate model training with cost estimation, progress tracking, and HuggingFace Space integration",
    },
    {
        "task": "Evaluate the newly trained model against the current feature_dev model using LangSmith comparison",
        "expected_agents": ["infrastructure"],
        "risk_level": "low",
        "ib_agent_step": "modelops.2",
        "expected_steps": ["infrastructure_check", "modelops_evaluate"],
        "description": "Run evaluation suite with weighted scoring: accuracy, completeness, efficiency, latency, integration",
    },
    {
        "task": "Deploy the evaluated model to production with automatic config update and rollback capability",
        "expected_agents": ["infrastructure"],
        "risk_level": "high",
        "ib_agent_step": "modelops.3",
        "expected_steps": ["infrastructure_check", "modelops_deploy", "config_backup"],
        "description": "Update models.yaml, create version backup, ensure thread-safe registry operations",
    },
    {
        "task": "View model deployment history and rollback to previous version due to performance regression",
        "expected_agents": ["infrastructure"],
        "risk_level": "medium",
        "ib_agent_step": "modelops.4",
        "expected_steps": ["infrastructure_check", "modelops_rollback"],
        "description": "Access model registry, identify previous version, execute rollback with validation",
    },
    {
        "task": "Convert deployed model to GGUF format for local development and testing",
        "expected_agents": ["infrastructure"],
        "risk_level": "low",
        "ib_agent_step": "modelops.5",
        "expected_steps": ["infrastructure_check", "modelops_convert"],
        "description": "Generate GGUF quantized model with download management for local usage",
    },
    # =========================================================================
    # Cross-Cutting Concerns
    # =========================================================================
    {
        "task": "Review MCP client implementation for OWASP Top 10 vulnerabilities including injection and broken auth",
        "expected_agents": ["code_review"],
        "risk_level": "high",
        "ib_agent_step": "cross",
        "expected_steps": ["code_review_node", "security_scan"],
        "description": "Security audit of mcp_clients.py for API key handling and input validation",
    },
    {
        "task": "Write OpenAPI documentation for IB Agent research endpoints with request/response schemas",
        "expected_agents": ["documentation"],
        "risk_level": "low",
        "ib_agent_step": "cross",
        "expected_steps": ["documentation_node"],
        "description": "Generate Swagger docs for /api/v1/research/* endpoints",
    },
    {
        "task": "Configure GitHub Actions workflow for IB Agent with Docker build, pytest, and DigitalOcean deployment",
        "expected_agents": ["cicd"],
        "risk_level": "medium",
        "ib_agent_step": "cross",
        "expected_steps": ["cicd_node", "infrastructure_check"],
        "description": "Create CI/CD pipeline with health check validation",
    },
]


def create_evaluation_dataset(
    dataset_name: str = "ib-agent-scenarios-v1", recreate: bool = False
) -> str:
    """
    Create or update the evaluation dataset with IB-Agent scenarios.

    Args:
        dataset_name: Name of the LangSmith dataset
        recreate: If True, delete existing dataset and recreate

    Returns:
        Dataset ID
    """
    # Check if dataset exists
    existing_datasets = list(client.list_datasets(dataset_name=dataset_name))

    if existing_datasets:
        if recreate:
            logger.info(f"Deleting existing dataset: {dataset_name}")
            client.delete_dataset(dataset_id=existing_datasets[0].id)
        else:
            logger.info(
                f"Dataset already exists: {dataset_name} (use --recreate to overwrite)"
            )
            return existing_datasets[0].id

    # Create new dataset
    logger.info(f"Creating dataset: {dataset_name}")
    dataset = client.create_dataset(
        dataset_name=dataset_name,
        description="IB-Agent Platform development scenarios for code-chef evaluation. "
        "Maps to implementation phases 1-4 from action_plan.md. "
        "See: https://github.com/Appsmithery/IB-Agent",
    )

    # Add examples
    for i, scenario in enumerate(IB_AGENT_SCENARIOS, 1):
        logger.info(
            f"Adding scenario {i}/{len(IB_AGENT_SCENARIOS)}: {scenario['ib_agent_step']}"
        )
        client.create_example(
            dataset_id=dataset.id,
            inputs={
                "task": scenario["task"],
                "description": scenario.get("description", ""),
            },
            outputs={
                "expected_agents": scenario["expected_agents"],
                "risk_level": scenario["risk_level"],
                "ib_agent_step": scenario["ib_agent_step"],
                "expected_steps": scenario.get("expected_steps", []),
            },
        )

    logger.info(
        f"Created dataset with {len(IB_AGENT_SCENARIOS)} examples: {dataset.id}"
    )
    return dataset.id


def list_datasets() -> None:
    """List all available datasets in the workspace."""
    datasets = list(client.list_datasets())
    print(f"\n{'Name':<40} {'Examples':<10} {'Created':<25}")
    print("-" * 75)
    for ds in datasets:
        print(f"{ds.name:<40} {ds.example_count or 0:<10} {str(ds.created_at)[:25]}")


def get_dataset_examples(dataset_name: str) -> None:
    """Print all examples in a dataset."""
    datasets = list(client.list_datasets(dataset_name=dataset_name))
    if not datasets:
        print(f"Dataset not found: {dataset_name}")
        return

    examples = list(client.list_examples(dataset_id=datasets[0].id))
    print(f"\n{dataset_name}: {len(examples)} examples\n")

    for i, ex in enumerate(examples, 1):
        step = ex.outputs.get("ib_agent_step", "N/A") if ex.outputs else "N/A"
        agents = ex.outputs.get("expected_agents", []) if ex.outputs else []
        risk = ex.outputs.get("risk_level", "N/A") if ex.outputs else "N/A"
        task = ex.inputs.get("task", "")[:80] if ex.inputs else ""

        print(f"{i:2}. [{step}] {task}...")
        print(f"    Agents: {', '.join(agents)} | Risk: {risk}")
        print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Manage LangSmith evaluation datasets")
    parser.add_argument(
        "--recreate", action="store_true", help="Delete and recreate dataset"
    )
    parser.add_argument("--list", action="store_true", help="List all datasets")
    parser.add_argument("--show", type=str, help="Show examples for a dataset")
    parser.add_argument(
        "--name", type=str, default="ib-agent-scenarios-v1", help="Dataset name"
    )

    args = parser.parse_args()

    if args.list:
        list_datasets()
    elif args.show:
        get_dataset_examples(args.show)
    else:
        dataset_id = create_evaluation_dataset(args.name, args.recreate)
        print(f"\nDataset ready: {dataset_id}")
        print(f"View at: https://smith.langchain.com/datasets/{dataset_id}")
