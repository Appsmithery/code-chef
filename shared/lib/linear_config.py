"""Linear configuration loader with .env override support.

This module provides a multi-layer configuration strategy:
1. Structural config from YAML (UUIDs, field IDs, endpoints)
2. Secrets from .env (OAuth tokens, API keys)
3. Environment variable overrides for both layers

Usage:
    from lib.linear_config import get_linear_config

    config = get_linear_config()
    template_uuid = config.get_template_uuid("orchestrator", scope="workspace")
    api_key = config.api_key
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional, List
import yaml
from pydantic import BaseModel, Field


class CustomFieldOption(BaseModel):
    """Custom field option configuration."""

    value: str
    default: bool = False


class CustomField(BaseModel):
    """Custom field configuration."""

    id: str
    type: str
    options: List[str | CustomFieldOption] = Field(default_factory=list)


class TemplateConfig(BaseModel):
    """Linear template configuration."""

    uuid: str
    url: Optional[str] = None
    name: str
    scope: str  # 'workspace' or 'project'


class WorkspaceConfig(BaseModel):
    """Workspace configuration."""

    slug: str
    team_id: str


class ApprovalHubConfig(BaseModel):
    """Approval hub configuration."""

    issue_id: str


class LabelsConfig(BaseModel):
    """Labels configuration."""

    hitl: str
    orchestrator: str


class DefaultAssigneeConfig(BaseModel):
    """Default assignee configuration."""

    id: str
    email: str


class WebhookConfig(BaseModel):
    """Webhook configuration."""

    signing_secret_env: str
    uri: str


class OAuthConfig(BaseModel):
    """OAuth configuration."""

    redirect_uri: str
    scopes: str


class ApprovalPolicyConfig(BaseModel):
    """Approval policy for risk level."""

    required_actions: List[str]
    priority: int


class LinearConfig(BaseModel):
    """Linear integration configuration."""

    # Workspace info
    workspace: WorkspaceConfig
    approval_hub: ApprovalHubConfig

    # Templates
    templates: Dict[str, TemplateConfig]

    # Custom fields
    custom_fields: Dict[str, CustomField]

    # Labels
    labels: LabelsConfig

    # Default assignee
    default_assignee: DefaultAssigneeConfig

    # Webhooks
    webhooks: Dict[str, WebhookConfig]

    # OAuth
    oauth: OAuthConfig

    # Approval policies
    approval_policies: Dict[str, ApprovalPolicyConfig]

    # Secrets (loaded from .env)
    api_key: str
    oauth_client_id: Optional[str] = None
    oauth_client_secret: Optional[str] = None
    oauth_dev_token: Optional[str] = None
    webhook_signing_secret: Optional[str] = None

    @classmethod
    def load(
        cls, config_path: str = "config/linear/linear-config.yaml"
    ) -> "LinearConfig":
        """Load Linear configuration from YAML + .env secrets.

        Args:
            config_path: Path to YAML configuration file

        Returns:
            LinearConfig instance with merged YAML + environment configuration

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If required secrets are missing
        """

        # Load structural config from YAML
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Linear config not found: {config_path}")

        with open(config_file) as f:
            config_data = yaml.safe_load(f)

        # Parse nested structures
        workspace = WorkspaceConfig(**config_data["workspace"])
        approval_hub = ApprovalHubConfig(**config_data["approval_hub"])

        templates = {
            name: TemplateConfig(**template_data)
            for name, template_data in config_data["templates"].items()
        }

        custom_fields = {
            name: CustomField(**field_data)
            for name, field_data in config_data["custom_fields"].items()
        }

        labels = LabelsConfig(**config_data["labels"])
        default_assignee = DefaultAssigneeConfig(**config_data["default_assignee"])

        webhooks = {
            name: WebhookConfig(**webhook_data)
            for name, webhook_data in config_data["webhooks"].items()
        }

        oauth = OAuthConfig(**config_data["oauth"])

        approval_policies = {
            level: ApprovalPolicyConfig(**policy_data)
            for level, policy_data in config_data["approval_policies"].items()
        }

        # Load secrets from .env
        api_key = os.getenv("LINEAR_API_KEY", "")
        if not api_key:
            raise ValueError("LINEAR_API_KEY environment variable is required")

        return cls(
            workspace=workspace,
            approval_hub=approval_hub,
            templates=templates,
            custom_fields=custom_fields,
            labels=labels,
            default_assignee=default_assignee,
            webhooks=webhooks,
            oauth=oauth,
            approval_policies=approval_policies,
            # Secrets from .env
            api_key=api_key,
            oauth_client_id=os.getenv("LINEAR_OAUTH_CLIENT_ID"),
            oauth_client_secret=os.getenv("LINEAR_OAUTH_CLIENT_SECRET"),
            oauth_dev_token=os.getenv("LINEAR_OAUTH_DEV_TOKEN"),
            webhook_signing_secret=os.getenv("LINEAR_ORCHESTRATOR_WEBHOOK_SECRET"),
        )

    def get_template_uuid(self, agent: str, scope: str = "workspace") -> str:
        """Get template UUID with fallback logic.

        Args:
            agent: Agent name (e.g., 'orchestrator', 'feature-dev')
            scope: Template scope ('workspace' or 'project')

        Returns:
            Template UUID string
        """
        # Try agent-specific template from environment
        env_var = f"HITL_{agent.upper().replace('-', '_')}_TEMPLATE_UUID"
        if agent_uuid := os.getenv(env_var):
            return agent_uuid

        # Fallback to orchestrator template
        if scope == "workspace":
            return self.templates["hitl_orchestrator"].uuid
        return self.templates["task_orchestrator"].uuid

    def get_approval_policy(self, risk_level: str) -> ApprovalPolicyConfig:
        """Get approval policy for risk level.

        Args:
            risk_level: Risk level ('low', 'medium', 'high', 'critical')

        Returns:
            ApprovalPolicyConfig for the risk level

        Raises:
            ValueError: If risk level is invalid
        """
        if risk_level not in self.approval_policies:
            raise ValueError(
                f"Invalid risk level: {risk_level}. Must be one of: {list(self.approval_policies.keys())}"
            )

        return self.approval_policies[risk_level]

    def get_custom_field_id(self, field_name: str) -> str:
        """Get custom field ID by name.

        Args:
            field_name: Field name ('required_action' or 'request_status')

        Returns:
            Custom field ID

        Raises:
            ValueError: If field name is invalid
        """
        if field_name not in self.custom_fields:
            raise ValueError(
                f"Invalid field name: {field_name}. Must be one of: {list(self.custom_fields.keys())}"
            )

        return self.custom_fields[field_name].id


# Global config instance (lazy-loaded)
_config: Optional[LinearConfig] = None


def get_linear_config(reload: bool = False) -> LinearConfig:
    """Get Linear configuration singleton.

    Args:
        reload: Force reload configuration from disk

    Returns:
        LinearConfig instance
    """
    global _config
    if _config is None or reload:
        _config = LinearConfig.load()
    return _config
