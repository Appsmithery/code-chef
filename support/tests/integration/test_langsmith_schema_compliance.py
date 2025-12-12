"""LangSmith trace metadata schema compliance tests.

Tests verify traces comply with config/observability/tracing-schema.yaml:
- Required metadata fields present
- Valid values for enums
- Correct field formats (semver, sha256, UUID)
- Project routing logic
"""

import os
import re
from pathlib import Path

import pytest
import yaml
from langsmith import Client


class TestLangSmithSchemaCompliance:
    """Verify traces comply with tracing-schema.yaml."""

    @pytest.fixture
    def langsmith_client(self):
        """Provide LangSmith client."""
        api_key = os.getenv("LANGCHAIN_API_KEY")
        if not api_key:
            pytest.skip("LANGCHAIN_API_KEY not set")
        return Client(api_key=api_key)

    @pytest.fixture
    def tracing_schema(self):
        """Load tracing schema definition."""
        schema_path = Path("config/observability/tracing-schema.yaml")
        with open(schema_path, "r") as f:
            return yaml.safe_load(f)

    @pytest.mark.integration
    @pytest.mark.langsmith
    def test_trace_has_required_fields(self, langsmith_client, tracing_schema):
        """Verify all traces have 7 required metadata fields."""
        # Fetch recent trace from code-chef-production
        project = "code-chef-production"
        runs = list(langsmith_client.list_runs(project_name=project, limit=1))

        if not runs:
            pytest.skip(f"No traces found in project {project}")

        trace = runs[0]
        metadata = trace.extra.get("metadata", {}) if trace.extra else {}

        # Required fields from tracing-schema.yaml
        required_fields = [
            "experiment_group",
            "environment",
            "module",
            "extension_version",
            "model_version",
            "config_hash",
            # Note: task_id is optional
        ]

        # Validate metadata presence
        for field in required_fields:
            assert (
                field in metadata
            ), f"Missing required field: {field} in trace {trace.id}"

        # Validate field formats
        assert metadata["experiment_group"] in [
            "code-chef",
            "baseline",
        ], f"Invalid experiment_group: {metadata['experiment_group']}"

        assert metadata["environment"] in [
            "production",
            "training",
            "evaluation",
            "test",
        ], f"Invalid environment: {metadata['environment']}"

        # Validate semver format for extension_version
        semver_pattern = r"^\d+\.\d+\.\d+$"
        assert re.match(
            semver_pattern, metadata["extension_version"]
        ), f"Invalid semver format: {metadata['extension_version']}"

        # Validate config_hash format (sha256 hex)
        sha256_pattern = r"^[a-f0-9]{64}$"
        config_hash = metadata["config_hash"].replace("sha256:", "")
        assert re.match(
            sha256_pattern, config_hash
        ), f"Invalid config_hash format: {metadata['config_hash']}"

        # Validate task_id format if present (UUID)
        if "task_id" in metadata:
            uuid_pattern = (
                r"^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$"
            )
            assert re.match(
                uuid_pattern, metadata["task_id"]
            ), f"Invalid task_id format: {metadata['task_id']}"

    @pytest.mark.integration
    @pytest.mark.langsmith
    def test_experiment_group_values(self, langsmith_client):
        """Verify experiment_group uses valid values only."""
        valid_values = ["code-chef", "baseline"]

        # Fetch last 100 traces from production
        project = "code-chef-production"
        runs = list(langsmith_client.list_runs(project_name=project, limit=100))

        if not runs:
            pytest.skip(f"No traces found in project {project}")

        invalid_traces = []

        for run in runs:
            metadata = run.extra.get("metadata", {}) if run.extra else {}
            experiment_group = metadata.get("experiment_group")

            if experiment_group and experiment_group not in valid_values:
                invalid_traces.append(
                    {"trace_id": run.id, "experiment_group": experiment_group}
                )

        # Fail if any invalid values found
        assert (
            len(invalid_traces) == 0
        ), f"Found {len(invalid_traces)} traces with invalid experiment_group: {invalid_traces}"

    @pytest.mark.integration
    @pytest.mark.langsmith
    def test_environment_values(self, langsmith_client):
        """Verify environment uses valid values only."""
        valid_values = ["production", "training", "evaluation", "test"]

        # Check all 4 projects
        projects = [
            "code-chef-production",
            "code-chef-training",
            "code-chef-evaluation",
            "code-chef-experiments",
        ]

        invalid_traces = []

        for project in projects:
            try:
                runs = list(langsmith_client.list_runs(project_name=project, limit=50))
            except Exception:
                # Project might not exist yet
                continue

            for run in runs:
                metadata = run.extra.get("metadata", {}) if run.extra else {}
                environment = metadata.get("environment")

                if environment and environment not in valid_values:
                    invalid_traces.append(
                        {
                            "trace_id": run.id,
                            "project": project,
                            "environment": environment,
                        }
                    )

        # Fail if any invalid values found
        assert (
            len(invalid_traces) == 0
        ), f"Found {len(invalid_traces)} traces with invalid environment: {invalid_traces}"

    @pytest.mark.integration
    @pytest.mark.langsmith
    def test_module_field_routing(self, langsmith_client):
        """Verify module field contains correct agent/operation name."""
        projects_and_expected_modules = {
            "code-chef-production": [
                "supervisor",
                "feature_dev",
                "code_review",
                "infrastructure",
                "cicd",
                "documentation",
            ],
            "code-chef-training": ["training"],
            "code-chef-evaluation": ["evaluation", "deployment"],
        }

        violations = []

        for project, expected_modules in projects_and_expected_modules.items():
            try:
                runs = list(langsmith_client.list_runs(project_name=project, limit=50))
            except Exception:
                continue

            for run in runs:
                metadata = run.extra.get("metadata", {}) if run.extra else {}
                module = metadata.get("module")

                if module and module not in expected_modules:
                    violations.append(
                        {
                            "trace_id": run.id,
                            "project": project,
                            "module": module,
                            "expected_one_of": expected_modules,
                        }
                    )

        # Verify consistency
        assert (
            len(violations) == 0
        ), f"Found {len(violations)} traces with incorrect module routing: {violations}"

    @pytest.mark.integration
    @pytest.mark.langsmith
    def test_config_hash_generation(self):
        """Verify config hash is deterministic."""
        from shared.lib.config_hash import generate_config_hash

        # Load config/agents/models.yaml
        config_path = Path("config/agents/models.yaml")
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)

        # Generate hash twice
        hash1 = generate_config_hash(config)
        hash2 = generate_config_hash(config)

        # Verify hashes identical
        assert hash1 == hash2, "Config hash should be deterministic"

        # Verify format
        sha256_pattern = r"^sha256:[a-f0-9]{64}$"
        assert re.match(sha256_pattern, hash1), f"Invalid hash format: {hash1}"

        # Modify config slightly
        modified_config = config.copy()
        modified_config["agents"]["feature_dev"]["temperature"] = 0.5

        # Verify hash changes
        hash3 = generate_config_hash(modified_config)
        assert hash3 != hash1, "Config hash should change when config changes"

    @pytest.mark.integration
    @pytest.mark.langsmith
    def test_trace_metadata_schema_validation(self, langsmith_client, tracing_schema):
        """Validate full schema compliance against tracing-schema.yaml."""
        # Load config/observability/tracing-schema.yaml
        schema = tracing_schema

        # Fetch recent traces from all projects
        projects = [
            "code-chef-production",
            "code-chef-training",
            "code-chef-evaluation",
            "code-chef-experiments",
        ]

        violations = []

        for project in projects:
            try:
                runs = list(langsmith_client.list_runs(project_name=project, limit=20))
            except Exception:
                continue

            for run in runs:
                metadata = run.extra.get("metadata", {}) if run.extra else {}

                # Validate each field against schema
                for field_name, field_schema in schema.get("fields", {}).items():
                    # Check required
                    if field_schema.get("required", False):
                        if field_name not in metadata:
                            violations.append(
                                {
                                    "trace_id": run.id,
                                    "project": project,
                                    "field": field_name,
                                    "error": "Required field missing",
                                }
                            )
                            continue

                    # Check type
                    if field_name in metadata:
                        value = metadata[field_name]
                        expected_type = field_schema.get("type")

                        if expected_type == "string" and not isinstance(value, str):
                            violations.append(
                                {
                                    "trace_id": run.id,
                                    "project": project,
                                    "field": field_name,
                                    "error": f"Expected string, got {type(value).__name__}",
                                }
                            )

                        # Check enum values
                        if "enum" in field_schema:
                            if value not in field_schema["enum"]:
                                violations.append(
                                    {
                                        "trace_id": run.id,
                                        "project": project,
                                        "field": field_name,
                                        "error": f"Invalid enum value: {value}",
                                        "valid_values": field_schema["enum"],
                                    }
                                )

                        # Check pattern
                        if "pattern" in field_schema:
                            pattern = field_schema["pattern"]
                            if not re.match(pattern, value):
                                violations.append(
                                    {
                                        "trace_id": run.id,
                                        "project": project,
                                        "field": field_name,
                                        "error": f"Value does not match pattern: {pattern}",
                                        "value": value,
                                    }
                                )

        # Report violations with details
        if violations:
            violation_summary = "\n".join(
                [
                    f"  - Trace {v['trace_id']} in {v['project']}: "
                    f"{v['field']} - {v['error']}"
                    for v in violations[:10]  # Show first 10
                ]
            )

            pytest.fail(
                f"Found {len(violations)} schema violations:\n{violation_summary}\n"
                f"{'...(showing first 10)' if len(violations) > 10 else ''}"
            )

    @pytest.mark.integration
    @pytest.mark.langsmith
    def test_project_routing_logic(self, langsmith_client):
        """Verify traces are routed to correct LangSmith projects."""
        # Define expected routing rules
        routing_rules = {
            "code-chef-production": {
                "environment": "production",
                "experiment_group": "code-chef",
            },
            "code-chef-training": {"environment": "training", "module": "training"},
            "code-chef-evaluation": {
                "environment": "evaluation",
                "module": ["evaluation", "deployment"],
            },
            "code-chef-experiments": {
                "experiment_id": lambda v: v is not None  # Must have experiment_id
            },
        }

        misrouted_traces = []

        for project, rules in routing_rules.items():
            try:
                runs = list(langsmith_client.list_runs(project_name=project, limit=50))
            except Exception:
                continue

            for run in runs:
                metadata = run.extra.get("metadata", {}) if run.extra else {}

                # Check if trace matches project routing rules
                matches = True
                for field, expected_value in rules.items():
                    actual_value = metadata.get(field)

                    if callable(expected_value):
                        # Lambda validator
                        if not expected_value(actual_value):
                            matches = False
                            break
                    elif isinstance(expected_value, list):
                        # Multiple valid values
                        if actual_value not in expected_value:
                            matches = False
                            break
                    else:
                        # Exact match
                        if actual_value != expected_value:
                            matches = False
                            break

                if not matches:
                    misrouted_traces.append(
                        {
                            "trace_id": run.id,
                            "project": project,
                            "metadata": metadata,
                            "expected_rules": rules,
                        }
                    )

        # Report misrouted traces
        assert (
            len(misrouted_traces) == 0
        ), f"Found {len(misrouted_traces)} misrouted traces: {misrouted_traces[:5]}"
