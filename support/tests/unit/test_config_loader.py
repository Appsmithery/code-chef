"""
Unit Tests for ConfigLoader

Tests YAML loading, Pydantic validation, environment overrides, and hot-reload.
"""

import pytest
import sys
import yaml
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add shared/lib to path
repo_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(repo_root / "shared"))

from lib.config_loader import ConfigLoader
from lib.agent_config_schema import AgentConfig, ModelsConfig


class TestConfigLoader:
    """Test suite for ConfigLoader class"""

    @pytest.fixture
    def sample_yaml_config(self):
        """Sample valid YAML config for testing"""
        return """
version: "1.0"
provider: gradient

agents:
  orchestrator:
    model: llama3.3-70b-instruct
    provider: gradient
    temperature: 0.3
    max_tokens: 2000
    cost_per_1m_tokens: 0.60
    context_window: 128000
    use_case: complex_reasoning
    tags: [routing, orchestration]
    langsmith_project: agents-orchestrator

  feature-dev:
    model: codellama-13b
    provider: gradient
    temperature: 0.7
    max_tokens: 2000
    cost_per_1m_tokens: 0.30
    context_window: 16000
    use_case: code_generation
    tags: [feature-development, python]
    langsmith_project: agents-feature-dev

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
        assert loader._config.provider == "gradient"
        assert len(loader._config.agents) == 2

    def test_get_agent_config(self, temp_config_file):
        """Test retrieving specific agent config"""
        loader = ConfigLoader(config_path=temp_config_file, hot_reload=False)

        orchestrator = loader.get_agent_config("orchestrator")

        assert orchestrator.model == "llama3.3-70b-instruct"
        assert orchestrator.temperature == 0.3
        assert orchestrator.max_tokens == 2000
        assert orchestrator.cost_per_1m_tokens == 0.60
        assert orchestrator.context_window == 128000
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

        assert len(all_agents) == 2
        assert "orchestrator" in all_agents
        assert "feature-dev" in all_agents
        assert isinstance(all_agents["orchestrator"], AgentConfig)

    def test_environment_override_production(self, temp_config_file):
        """Test production environment uses base config (no override)"""
        with patch.dict(os.environ, {"NODE_ENV": "production"}):
            loader = ConfigLoader(config_path=temp_config_file, hot_reload=False)

            orchestrator = loader.get_agent_config("orchestrator")

            # Should use base config (no override)
            assert orchestrator.model == "llama3.3-70b-instruct"
            assert orchestrator.cost_per_1m_tokens == 0.60

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
            assert feature_dev.model == "codellama-13b"
            assert feature_dev.cost_per_1m_tokens == 0.30

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
    langsmith_project: agents-orchestrator
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
        assert original_model == "llama3.3-70b-instruct"

        # Modify config file
        modified_config = """
version: "1.0"
provider: gradient
agents:
  orchestrator:
    model: llama3-8b-instruct  # Changed model
    provider: gradient
    temperature: 0.3
    max_tokens: 2000
    cost_per_1m_tokens: 0.20
    context_window: 128000
    use_case: complex_reasoning
    tags: [routing, orchestration]
    langsmith_project: agents-orchestrator
"""
        with open(temp_config_file, "w") as f:
            f.write(modified_config)

        # Reload config
        loader.reload()

        # Verify change
        new_model = loader.get_agent_config("orchestrator").model
        assert new_model == "llama3-8b-instruct"

    def test_get_provider(self, temp_config_file):
        """Test retrieving default provider"""
        loader = ConfigLoader(config_path=temp_config_file, hot_reload=False)

        provider = loader.get_provider()
        assert provider == "gradient"

    def test_agent_name_normalization(self, temp_config_file):
        """Test underscore to hyphen normalization"""
        loader = ConfigLoader(config_path=temp_config_file, hot_reload=False)

        # Should accept both formats
        config1 = loader.get_agent_config("feature-dev")
        config2 = loader.get_agent_config("feature_dev")

        assert config1.model == config2.model
        assert config1.model == "codellama-13b"

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
        assert all(r == "llama3.3-70b-instruct" for r in results)

    @patch.dict(os.environ, {"NODE_ENV": "staging"})
    def test_unknown_environment(self, temp_config_file):
        """Test behavior with unknown environment (should use base config)"""
        loader = ConfigLoader(config_path=temp_config_file, hot_reload=False)

        orchestrator = loader.get_agent_config("orchestrator")

        # Should use base config (staging not defined)
        assert orchestrator.model == "llama3.3-70b-instruct"
        assert orchestrator.cost_per_1m_tokens == 0.60


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
