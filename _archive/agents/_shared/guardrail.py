"""Guardrail orchestration utilities shared across Dev-Tools agents."""

from __future__ import annotations

import os
import uuid
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import httpx
import yaml
from pydantic import BaseModel, Field, ConfigDict


class GuardrailSeverity(str, Enum):
    """Severity of a single guardrail check."""

    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"


class GuardrailStatus(str, Enum):
    """Overall guardrail execution status."""

    PASSED = "passed"
    WARNINGS = "warnings"
    FAILED = "failed"


class GuardrailCheckResult(BaseModel):
    """Outcome of an individual guardrail check."""

    model_config = ConfigDict(use_enum_values=True)

    id: str
    name: str
    severity: GuardrailSeverity
    message: str
    remediation: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class GuardrailReport(BaseModel):
    """Aggregate report for a guardrail run."""

    model_config = ConfigDict(use_enum_values=True, json_encoders={datetime: lambda dt: dt.isoformat()})

    report_id: str
    agent: str
    status: GuardrailStatus
    started_at: datetime
    completed_at: datetime
    summary: Dict[str, int] = Field(default_factory=dict)
    checks: List[GuardrailCheckResult] = Field(default_factory=list)
    task_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class GuardrailOrchestrator:
    """Executes guardrail checks and persists results."""

    _DEFAULT_CRITICAL_KEYS: Set[str] = {
        "DB_PASSWORD",
        "LANGFUSE_SECRET_KEY",
        "LANGFUSE_PUBLIC_KEY",
        "GRADIENT_API_KEY",
        "GRADIENT_MODEL_ACCESS_KEY",
        "QDRANT_API_KEY",
        "DIGITALOCEAN_TOKEN",
        "DIGITAL_OCEAN_PAT",
        "SUPABASE_SERVICE_ROLE_KEY",
    }

    _REQUIRED_MCP_SERVERS: Dict[str, Set[str]] = {
        "infrastructure": {"dockerhub", "prometheus", "rust-mcp-filesystem"},
        "cicd": {"gitmcp", "rust-mcp-filesystem"},
    }

    _HIGH_RISK_SERVERS: Set[str] = {"gmail-mcp", "stripe"}

    def __init__(self) -> None:
        self.env_template_path = Path(os.getenv("GUARDRAIL_ENV_TEMPLATE", "config/env/.env.template"))
        self.env_file_path = Path(os.getenv("GUARDRAIL_ENV_FILE", "config/env/.env"))
        self.mcp_mapping_path = Path(os.getenv("GUARDRAIL_MCP_MAPPING", "config/mcp-agent-tool-mapping.yaml"))
        self.prometheus_config_path = Path(os.getenv("GUARDRAIL_PROMETHEUS_CONFIG", "config/prometheus/prometheus.yml"))
        self.state_service_url = os.getenv("STATE_SERVICE_URL", "http://state-persistence:8008")
        self.enforcement_mode = os.getenv("GUARDRAIL_ENFORCEMENT", "observe").strip().lower()
        self.http_timeout = float(os.getenv("GUARDRAIL_HTTP_TIMEOUT", "4.0"))

        user_defined_keys = {
            key.strip()
            for key in os.getenv("GUARDRAIL_CRITICAL_KEYS", "").split(",")
            if key.strip()
        }
        self.critical_secret_keys = self._DEFAULT_CRITICAL_KEYS.union(user_defined_keys)

    @property
    def should_block_failures(self) -> bool:
        """Whether failures should block the calling workflow."""

        return self.enforcement_mode in {"enforce", "strict", "block"}

    async def run(
        self,
        agent_name: str,
        *,
        task_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> GuardrailReport:
        """Execute guardrail checks and optionally persist the report."""

        started_at = datetime.utcnow()
        checks: List[GuardrailCheckResult] = []

        checks.append(self._check_env_alignment())
        checks.append(self._check_mcp_policy(agent_name))
        checks.append(self._check_prometheus_security())

        severity_counts = {
            GuardrailSeverity.PASS.value: sum(1 for c in checks if c.severity == GuardrailSeverity.PASS),
            GuardrailSeverity.WARN.value: sum(1 for c in checks if c.severity == GuardrailSeverity.WARN),
            GuardrailSeverity.FAIL.value: sum(1 for c in checks if c.severity == GuardrailSeverity.FAIL),
        }

        if severity_counts[GuardrailSeverity.FAIL.value] > 0:
            status = GuardrailStatus.FAILED
        elif severity_counts[GuardrailSeverity.WARN.value] > 0:
            status = GuardrailStatus.WARNINGS
        else:
            status = GuardrailStatus.PASSED

        report = GuardrailReport(
            report_id=str(uuid.uuid4()),
            agent=agent_name,
            task_id=task_id,
            status=status,
            started_at=started_at,
            completed_at=datetime.utcnow(),
            summary=severity_counts,
            checks=checks,
            metadata={"context_keys": sorted((context or {}).keys())},
        )

        await self._persist_report(report)

        return report

    def _check_env_alignment(self) -> GuardrailCheckResult:
        """Validate production environment variables and secrets."""

        if not self.env_template_path.exists():
            return GuardrailCheckResult(
                id="env-template-missing",
                name="Environment template availability",
                severity=GuardrailSeverity.WARN,
                message="Environment template config/env/.env.template is missing",
                remediation="Restore the template file from version control",
            )

        template_vars = self._parse_env_file(self.env_template_path)

        if not self.env_file_path.exists():
            return GuardrailCheckResult(
                id="env-file-missing",
                name="Deployment environment configuration",
                severity=GuardrailSeverity.FAIL,
                message="config/env/.env is missing. Deployments must define runtime secrets.",
                remediation="Copy config/env/.env.template to config/env/.env and populate required values.",
                details={"expected_keys": sorted(template_vars.keys())},
            )

        runtime_vars = self._parse_env_file(self.env_file_path)

        missing_keys = sorted(set(template_vars) - set(runtime_vars))
        empty_keys = sorted(key for key, value in runtime_vars.items() if not value)
        weak_secret_keys = sorted(
            key
            for key in self.critical_secret_keys
            if runtime_vars.get(key) in {"", "changeme", template_vars.get(key, ""), None}
        )

        severity = GuardrailSeverity.PASS
        if missing_keys or weak_secret_keys:
            severity = GuardrailSeverity.FAIL
        elif empty_keys:
            severity = GuardrailSeverity.WARN

        message = "Environment variables aligned with template"
        if severity is GuardrailSeverity.FAIL:
            message = "Environment configuration requires remediation"
        elif severity is GuardrailSeverity.WARN:
            message = "Environment configuration has placeholders"

        details: Dict[str, Any] = {}
        if missing_keys:
            details["missing_keys"] = missing_keys
        if empty_keys:
            details["empty_keys"] = empty_keys
        if weak_secret_keys:
            details["weak_secret_keys"] = weak_secret_keys

        return GuardrailCheckResult(
            id="env-alignment",
            name="Environment configuration",
            severity=severity,
            message=message,
            remediation="Populate mandatory secrets and remove placeholder values in config/env/.env",
            details=details,
        )

    def _check_mcp_policy(self, agent_name: str) -> GuardrailCheckResult:
        """Validate MCP tool assignments for the agent."""

        if not self.mcp_mapping_path.exists():
            return GuardrailCheckResult(
                id="mcp-mapping-missing",
                name="MCP tool policy",
                severity=GuardrailSeverity.FAIL,
                message="config/mcp-agent-tool-mapping.yaml is missing",
                remediation="Regenerate the MCP mapping via scripts/generate-agent-manifest.ps1",
            )

        try:
            with self.mcp_mapping_path.open("r", encoding="utf-8") as handle:
                mapping = yaml.safe_load(handle) or {}
        except Exception as exc:  # pragma: no cover - defensive
            return GuardrailCheckResult(
                id="mcp-mapping-unreadable",
                name="MCP tool policy",
                severity=GuardrailSeverity.FAIL,
                message="Failed to parse MCP mapping file",
                remediation="Validate YAML syntax in config/mcp-agent-tool-mapping.yaml",
                details={"error": str(exc)},
            )

        agent_mappings = (mapping.get("agent_tool_mappings") or {}).get(agent_name)
        if not agent_mappings:
            return GuardrailCheckResult(
                id="mcp-mapping-missing-agent",
                name="MCP tool policy",
                severity=GuardrailSeverity.FAIL,
                message=f"No MCP mapping found for agent '{agent_name}'",
                remediation="Update config/mcp-agent-tool-mapping.yaml to include this agent",
            )

        declared_servers: Set[str] = set()
        for section in (agent_mappings.get("recommended_tools") or []):
            server = section.get("server")
            if server:
                declared_servers.add(server)
        for section in (agent_mappings.get("shared_tools") or []):
            server = section.get("server")
            if server:
                declared_servers.add(server)

        required_servers = self._REQUIRED_MCP_SERVERS.get(agent_name, set())
        missing_required = sorted(required_servers - declared_servers)

        high_risk_without_rationale = sorted(
            section.get("server")
            for section in (agent_mappings.get("recommended_tools") or [])
            if section.get("server") in self._HIGH_RISK_SERVERS and not section.get("rationale")
        )

        severity = GuardrailSeverity.PASS
        if missing_required:
            severity = GuardrailSeverity.FAIL
        elif high_risk_without_rationale:
            severity = GuardrailSeverity.WARN

        message = "MCP mappings validated"
        if severity is GuardrailSeverity.FAIL:
            message = "Required MCP mappings missing"
        elif severity is GuardrailSeverity.WARN:
            message = "High-risk MCP mappings missing rationale"

        details: Dict[str, Any] = {
            "declared_servers": sorted(declared_servers),
        }
        if missing_required:
            details["missing_required_servers"] = missing_required
        if high_risk_without_rationale:
            details["high_risk_servers_without_rationale"] = high_risk_without_rationale

        return GuardrailCheckResult(
            id="mcp-policy",
            name="MCP policy compliance",
            severity=severity,
            message=message,
            remediation="Ensure mandatory MCP servers are assigned and high-risk access is justified",
            details=details,
        )

    def _check_prometheus_security(self) -> GuardrailCheckResult:
        """Ensure Prometheus scrape configuration considers authentication."""

        if not self.prometheus_config_path.exists():
            return GuardrailCheckResult(
                id="prom-config-missing",
                name="Prometheus configuration",
                severity=GuardrailSeverity.WARN,
                message="Prometheus configuration file config/prometheus/prometheus.yml is missing",
                remediation="Restore the configuration and enable auth on external endpoints",
            )

        try:
            contents = self.prometheus_config_path.read_text(encoding="utf-8")
        except Exception as exc:  # pragma: no cover
            return GuardrailCheckResult(
                id="prom-config-unreadable",
                name="Prometheus configuration",
                severity=GuardrailSeverity.WARN,
                message="Unable to read Prometheus configuration",
                remediation="Verify file permissions and encoding",
                details={"error": str(exc)},
            )

        has_auth = "basic_auth" in contents or "authorization" in contents
        severity = GuardrailSeverity.WARN if not has_auth else GuardrailSeverity.PASS
        message = "Prometheus scrape configuration reviewed"
        if not has_auth:
            message = "Prometheus endpoints are missing authentication guards"

        details = {"auth_enabled": has_auth}

        return GuardrailCheckResult(
            id="prometheus-auth",
            name="Prometheus scrape security",
            severity=severity,
            message=message,
            remediation="Add basic_auth or bearer authorization to Prometheus scrape targets before exposing metrics externally",
            details=details,
        )

    async def _persist_report(self, report: GuardrailReport) -> None:
        """Persist report to the state service; failures are logged silently."""

        if not self.state_service_url:
            return

        payload = report.model_dump(mode="json")

        url = self.state_service_url.rstrip("/") + "/compliance"
        try:
            async with httpx.AsyncClient(timeout=self.http_timeout) as client:
                await client.post(url, json=payload)
        except Exception:
            # Guardrail persistence should not block workflows; log to stderr for visibility.
            print("[guardrail] Failed to persist compliance report to state service", flush=True)

    @staticmethod
    def _parse_env_file(path: Path) -> Dict[str, str]:
        values: Dict[str, str] = {}
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                key, value = line.split("=", 1)
                values[key.strip()] = value.strip()
        except FileNotFoundError:
            return {}
        return values