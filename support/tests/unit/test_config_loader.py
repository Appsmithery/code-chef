"""
Unit Tests for ConfigLoader

Tests YAML loading, Pydantic validation, environment overrides, and hot-reload.
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

# Add shared/lib to path
repo_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(repo_root / "shared"))

from lib.agent_config_schema import AgentConfig, ModelsConfig
from lib.config_loader import ConfigLoader


class TestConfigLoader:
    """Test suite for ConfigLoader class"""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset ConfigLoader singleton between tests"""
        ConfigLoader._instance = None
        yield
        ConfigLoader._instance = None

    @pytest.fixture
    def sample_yaml_config(self):
        """Sample valid YAML config for testing"""
        return """
version: "1.0"
provider: openrouter

agents:
  orchestrator:
    model: anthropic/claude-3-5-sonnet
    provider: openrouter
    temperature: 0.3
    max_tokens: 2000
    cost_per_1m_tokens: 3.00
    context_window: 200000
    use_case: complex_reasoning
    tags: [routing, orchestration]
    langsmith_project: code-chef-orchestrator

  feature-dev:
    model: qwen/qwen-2.5-coder-32b-instruct
    provider: openrouter
    temperature: 0.7
    max_tokens: 2000
    cost_per_1m_tokens: 0.07
    context_window: 131072
    use_case: code_generation
    tags: [feature-development, python]
    langsmith_project: code-chef-feature-dev

  code-review:
    model: deepseek/deepseek-chat
    provider: openrouter
    temperature: 0.3
    max_tokens: 4000
    cost_per_1m_tokens: 0.75
    context_window: 64000
    use_case: code_analysis
    tags: [quality-assurance, security]
    langsmith_project: code-chef-code-review

  infrastructure:
    model: google/gemini-2.0-flash-001
    provider: openrouter
    temperature: 0.5
    max_tokens: 2000
    cost_per_1m_tokens: 0.25
    context_window: 1000000
    use_case: infrastructure_config
    tags: [terraform, kubernetes, docker]
    langsmith_project: code-chef-infrastructure

  cicd:
    model: google/gemini-2.0-flash-001
    provider: openrouter
    temperature: 0.5
    max_tokens: 2000
    cost_per_1m_tokens: 0.25
    context_window: 1000000
    use_case: pipeline_generation
    tags: [github-actions, jenkins]
    langsmith_project: code-chef-cicd

  documentation:
    model: deepseek/deepseek-chat
    provider: openrouter
    temperature: 0.7
    max_tokens: 2000
    cost_per_1m_tokens: 0.20
    context_window: 8192
    use_case: documentation_generation
    tags: [markdown, technical-writing]
    langsmith_project: code-chef-documentation

environments:
  development:
    orchestrator:
      model: llama3-8b-instruct
      cost_per_1m_tokens: 0.20
"""

    @pytest.fixture
    def temp_config_file(self, sample_yaml_config):
        """Create temporary config file for testing"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(sample_yaml_config)
            temp_path = Path(f.name)

        yield temp_path

        # Cleanup
        if temp_path.exists():
            temp_path.unlink()

    def test_load_valid_config(self, temp_config_file):
        """Test loading valid YAML config"""
        loader = ConfigLoader(config_path=temp_config_file, hot_reload=False)

        assert loader._config is not None
        assert loader._config.version == "1.0"
        assert loader._config.provider == "openrouter"
        assert len(loader._config.agents) == 6

    def test_get_agent_config(self, temp_config_file):
        """Test retrieving specific agent config"""
        loader = ConfigLoader(config_path=temp_config_file, hot_reload=False)

        orchestrator = loader.get_agent_config("orchestrator")

        assert orchestrator.model == "anthropic/claude-3-5-sonnet"
        assert orchestrator.temperature == 0.3
        assert orchestrator.max_tokens == 2000
        assert orchestrator.cost_per_1m_tokens == 3.00
        assert orchestrator.context_window == 200000  # Claude 3.5 Sonnet context
        assert "routing" in orchestrator.tags

    def test_get_agent_config_not_found(self, temp_config_file):
        """Test error when agent not found"""
        loader = ConfigLoader(config_path=temp_config_file, hot_reload=False)

        with pytest.raises(KeyError, match="Agent 'nonexistent' not found"):
            loader.get_agent_config("nonexistent")

    def test_get_all_agents(self, temp_config_file):
        """Test retrieving all agent configs"""
        loader = ConfigLoader(config_path=temp_config_file, hot_reload=False)

        all_agents = loader.get_all_agents()

        assert len(all_agents) == 6
        assert "orchestrator" in all_agents
        assert "feature-dev" in all_agents
        assert "code-review" in all_agents
        assert "infrastructure" in all_agents
        assert "cicd" in all_agents
        assert "documentation" in all_agents
        assert isinstance(all_agents["orchestrator"], AgentConfig)

    def test_environment_override_production(self, temp_config_file):
        """Test production environment uses base config (no override)"""
        with patch.dict(os.environ, {"NODE_ENV": "production"}):
            loader = ConfigLoader(config_path=temp_config_file, hot_reload=False)

            orchestrator = loader.get_agent_config("orchestrator")

            # Should use base config (no override)
            assert orchestrator.model == "anthropic/claude-3-5-sonnet"
            assert orchestrator.cost_per_1m_tokens == 3.00

    def test_environment_override_development(self, temp_config_file):
        """Test development environment applies overrides"""
        with patch.dict(os.environ, {"NODE_ENV": "development"}):
            loader = ConfigLoader(config_path=temp_config_file, hot_reload=False)

            orchestrator = loader.get_agent_config("orchestrator")

            # Should use development override
            assert orchestrator.model == "llama3-8b-instruct"
            assert orchestrator.cost_per_1m_tokens == 0.20

            # Other fields should remain from base config
            assert orchestrator.temperature == 0.3
            assert orchestrator.max_tokens == 2000

    def test_environment_override_partial(self, temp_config_file):
        """Test environment overrides only specified fields"""
        with patch.dict(os.environ, {"NODE_ENV": "development"}):
            loader = ConfigLoader(config_path=temp_config_file, hot_reload=False)

            # feature-dev has no development override
            feature_dev = loader.get_agent_config("feature-dev")

            # Should use base config (no override available)
            assert feature_dev.model == "qwen/qwen-2.5-coder-32b-instruct"
            assert (
                feature_dev.cost_per_1m_tokens == 0.07
            )  # Qwen Coder cost via OpenRouter

    def test_invalid_yaml_syntax(self):
        """Test error handling for invalid YAML syntax"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: syntax: [")
            temp_path = Path(f.name)

        try:
            with pytest.raises(yaml.YAMLError):
                ConfigLoader(config_path=temp_path, hot_reload=False)
        finally:
            temp_path.unlink()

    def test_invalid_schema(self):
        """Test Pydantic validation error for invalid schema"""
        invalid_config = """
version: "1.0"
provider: gradient
agents:
  orchestrator:
    model: llama3.3-70b-instruct
    temperature: 5.0  # Invalid: > 2.0
    max_tokens: 100  # Invalid: < 256 for Gradient
    cost_per_1m_tokens: 0.60
    context_window: 128000
    use_case: complex_reasoning
    tags: []
    langsmith_project: code-chef-orchestrator
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(invalid_config)
            temp_path = Path(f.name)

        try:
            with pytest.raises(Exception):  # Pydantic ValidationError
                ConfigLoader(config_path=temp_path, hot_reload=False)
        finally:
            temp_path.unlink()

    def test_missing_config_file(self):
        """Test error when config file doesn't exist"""
        with pytest.raises(FileNotFoundError):
            ConfigLoader(
                config_path=Path("/nonexistent/path/models.yaml"), hot_reload=False
            )

    def test_reload(self, temp_config_file):
        """Test manual config reload"""
        loader = ConfigLoader(config_path=temp_config_file, hot_reload=False)

        # Get initial config
        original_model = loader.get_agent_config("orchestrator").model
        assert original_model == "anthropic/claude-3-5-sonnet"

        # Modify config file
        modified_config = """
version: "1.0"
provider: openrouter
agents:
  orchestrator:
    model: google/gemini-2.0-flash-001  # Changed model
    provider: openrouter
    temperature: 0.3
    max_tokens: 2000
    cost_per_1m_tokens: 0.25
    context_window: 1000000
    use_case: complex_reasoning
    tags: [routing, orchestration]
    langsmith_project: code-chef-orchestrator

  feature-dev:
    model: qwen/qwen-2.5-coder-32b-instruct
    provider: openrouter
    temperature: 0.7
    max_tokens: 2000
    cost_per_1m_tokens: 0.07
    context_window: 131072
    use_case: code_generation
    tags: [feature-development, python]
    langsmith_project: code-chef-feature-dev

  code-review:
    model: deepseek/deepseek-chat
    provider: openrouter
    temperature: 0.3
    max_tokens: 4000
    cost_per_1m_tokens: 0.75
    context_window: 64000
    use_case: code_analysis
    tags: [quality-assurance, security]
    langsmith_project: code-chef-code-review

  infrastructure:
    model: google/gemini-2.0-flash-001
    provider: openrouter
    temperature: 0.5
    max_tokens: 2000
    cost_per_1m_tokens: 0.25
    context_window: 1000000
    use_case: infrastructure_config
    tags: [terraform, kubernetes, docker]
    langsmith_project: code-chef-infrastructure

  cicd:
    model: google/gemini-2.0-flash-001
    provider: openrouter
    temperature: 0.5
    max_tokens: 2000
    cost_per_1m_tokens: 0.25
    context_window: 1000000
    use_case: pipeline_generation
    tags: [github-actions, jenkins]
    langsmith_project: code-chef-cicd

  documentation:
    model: deepseek/deepseek-chat
    provider: openrouter
    temperature: 0.7
    max_tokens: 2000
    cost_per_1m_tokens: 0.75
    context_window: 64000
    use_case: documentation_generation
    tags: [markdown, technical-writing]
    langsmith_project: code-chef-documentation
"""
        with open(temp_config_file, "w") as f:
            f.write(modified_config)

        # Reload config
        loader.reload()

        # Verify change
        new_model = loader.get_agent_config("orchestrator").model
        assert new_model == "google/gemini-2.0-flash-001"  # Changed to Gemini

    def test_get_provider(self, temp_config_file):
        """Test retrieving default provider"""
        loader = ConfigLoader(config_path=temp_config_file, hot_reload=False)

        provider = loader.get_provider()
        assert provider == "openrouter"

    def test_agent_name_normalization(self, temp_config_file):
        """Test underscore to hyphen normalization"""
        loader = ConfigLoader(config_path=temp_config_file, hot_reload=False)

        # Should accept both formats
        config1 = loader.get_agent_config("feature-dev")
        config2 = loader.get_agent_config("feature_dev")

        assert config1.model == config2.model
        assert config1.model == "qwen/qwen-2.5-coder-32b-instruct"

    def test_singleton_pattern(self, temp_config_file):
        """Test ConfigLoader follows singleton pattern"""
        loader1 = ConfigLoader(config_path=temp_config_file, hot_reload=False)
        loader2 = ConfigLoader(config_path=temp_config_file, hot_reload=False)

        # Should be same instance
        assert loader1 is loader2

    def test_thread_safety(self, temp_config_file):
        """Test concurrent access to config"""
        import threading

        loader = ConfigLoader(config_path=temp_config_file, hot_reload=False)
        results = []

        def read_config(agent_name):
            config = loader.get_agent_config(agent_name)
            results.append(config.model)

        threads = [
            threading.Thread(target=read_config, args=("orchestrator",))
            for _ in range(10)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All reads should succeed
        assert len(results) == 10
        assert all(r == "anthropic/claude-3-5-sonnet" for r in results)

    @patch.dict(os.environ, {"NODE_ENV": "staging"})
    def test_unknown_environment(self, temp_config_file):
        """Test behavior with unknown environment (should use base config)"""
        loader = ConfigLoader(config_path=temp_config_file, hot_reload=False)

        orchestrator = loader.get_agent_config("orchestrator")

        # Should use base config (staging not defined)
        assert orchestrator.model == "anthropic/claude-3-5-sonnet"
        assert orchestrator.cost_per_1m_tokens == 3.00


class TestGlobalConfigLoader:
    """Test the global get_config_loader() function"""

    def test_get_config_loader(self):
        """Test global loader retrieval"""
        from lib.config_loader import get_config_loader

        loader = get_config_loader(hot_reload=False)

        assert loader is not None
        assert isinstance(loader, ConfigLoader)

    def test_get_config_loader_singleton(self):
        """Test global loader is singleton"""
        from lib.config_loader import get_config_loader

        loader1 = get_config_loader(hot_reload=False)
        loader2 = get_config_loader(hot_reload=False)

        assert loader1 is loader2


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
