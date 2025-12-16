"""
Configuration Loader - Centralized YAML-based LLM config management

Features:
- Single source of truth (config/agents/models.yaml)
- Hot-reload on file changes (optional, for development)
- Environment-specific overrides (production, development, staging)
- Thread-safe caching
- Pydantic validation

Usage:
    from lib.config_loader import ConfigLoader

    loader = ConfigLoader()
    orchestrator_config = loader.get_agent_config("orchestrator")
    print(f"Model: {orchestrator_config.model}, Temp: {orchestrator_config.temperature}")
"""

import os
import yaml
import logging
from pathlib import Path
from typing import Dict, Optional
from threading import Lock
from datetime import datetime, timedelta
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent

try:
    from lib.agent_config_schema import ModelsConfig, AgentConfig
except ModuleNotFoundError:
    from agent_config_schema import ModelsConfig, AgentConfig


logger = logging.getLogger(__name__)


class ConfigFileWatcher(FileSystemEventHandler):
    """Watches models.yaml for changes and triggers reload."""

    def __init__(self, config_loader):
        self.config_loader = config_loader
        self.last_reload = datetime.now()
        self.debounce_seconds = 1  # Ignore rapid successive changes

    def on_modified(self, event):
        if isinstance(event, FileModifiedEvent) and event.src_path.endswith(
            "models.yaml"
        ):
            # Debounce: Ignore if we just reloaded
            if (
                datetime.now() - self.last_reload
            ).total_seconds() < self.debounce_seconds:
                return

            logger.info(f"Detected change in {event.src_path}, reloading config...")
            self.config_loader._load_config()
            self.last_reload = datetime.now()


class ConfigLoader:
    """
    Loads and caches agent LLM configurations from YAML.

    Thread-safe singleton pattern with optional hot-reload.
    """

    _instance = None
    _lock = Lock()

    def __new__(cls, *args, **kwargs):
        """Singleton pattern to ensure one config instance per process."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, config_path: Optional[Path] = None, hot_reload: bool = False):
        # Only initialize once (singleton pattern)
        if hasattr(self, "_initialized"):
            return

        self.config_path = config_path or self._get_default_config_path()
        self.hot_reload = hot_reload
        self.environment = os.getenv(
            "NODE_ENV", "production"
        )  # production, development, staging

        self._config: Optional[ModelsConfig] = None
        self._config_mtime: Optional[float] = None
        self._observer: Optional[Observer] = None

        # Load initial config
        self._load_config()

        # Start file watcher if hot_reload enabled
        if self.hot_reload:
            self._start_file_watcher()

        self._initialized = True
        logger.info(
            f"ConfigLoader initialized (environment={self.environment}, hot_reload={self.hot_reload})"
        )

    def _get_default_config_path(self) -> Path:
        """Resolve default config path relative to repo root."""
        # In Docker: /app/lib/config_loader.py (copied from shared/lib/)
        # Locally: <repo>/shared/lib/config_loader.py
        # repo_root should be /app in Docker, <repo> locally
        file_path = Path(__file__)  # /app/lib/config_loader.py or <repo>/shared/lib/config_loader.py
        
        # Check if running in Docker (file is in /app/lib instead of <repo>/shared/lib)
        if file_path.parts[-3:-1] == ('app', 'lib'):
            # Docker: /app/lib/config_loader.py → repo_root = /app
            repo_root = file_path.parent.parent
        else:
            # Local: <repo>/shared/lib/config_loader.py → repo_root = <repo>
            repo_root = file_path.parent.parent.parent
            
        config_path = repo_root / "config" / "agents" / "models.yaml"

        if not config_path.exists():
            raise FileNotFoundError(
                f"Config file not found: {config_path}. "
                "Create config/agents/models.yaml or pass custom path."
            )

        return config_path

    def _load_config(self):
        """Load and validate YAML config with Pydantic."""
        with self._lock:
            try:
                with open(self.config_path, "r") as f:
                    raw_config = yaml.safe_load(f)

                # Validate with Pydantic
                self._config = ModelsConfig(**raw_config)
                self._config_mtime = os.path.getmtime(self.config_path)

                logger.info(
                    f"Loaded config version {self._config.version} with {len(self._config.agents)} agents"
                )

            except FileNotFoundError:
                logger.error(f"Config file not found: {self.config_path}")
                raise

            except yaml.YAMLError as e:
                logger.error(f"Invalid YAML syntax in {self.config_path}: {e}")
                raise

            except Exception as e:
                logger.error(f"Failed to load config: {e}")
                raise

    def _start_file_watcher(self):
        """Start watchdog observer for hot-reload."""
        if self._observer is not None:
            return  # Already watching

        event_handler = ConfigFileWatcher(self)
        self._observer = Observer()
        self._observer.schedule(
            event_handler, str(self.config_path.parent), recursive=False
        )
        self._observer.start()
        logger.info(f"Started file watcher for {self.config_path}")

    def stop_file_watcher(self):
        """Stop watchdog observer (cleanup)."""
        if self._observer is not None:
            self._observer.stop()
            self._observer.join()
            self._observer = None
            logger.info("Stopped file watcher")

    def get_agent_config(self, agent_name: str) -> AgentConfig:
        """
        Get configuration for a specific agent with environment overrides.

        Args:
            agent_name: Agent identifier (orchestrator, feature-dev, code-review, etc.)

        Returns:
            AgentConfig with all settings resolved

        Raises:
            KeyError: If agent_name not found in config
        """
        if self._config is None:
            raise RuntimeError("Config not loaded. Call _load_config() first.")

        # Get base config
        agent_name_normalized = agent_name.replace(
            "_", "-"
        )  # feature_dev -> feature-dev
        if agent_name_normalized not in self._config.agents:
            raise KeyError(
                f"Agent '{agent_name}' not found in config. "
                f"Available agents: {list(self._config.agents.keys())}"
            )

        base_config = self._config.agents[agent_name_normalized]

        # Apply environment overrides if present
        if self._config.environments and self.environment in self._config.environments:
            env_overrides = self._config.environments[self.environment]
            agent_overrides = getattr(
                env_overrides, agent_name_normalized.replace("-", "_"), None
            )

            if agent_overrides:
                # Merge overrides into base config
                config_dict = base_config.model_dump()
                config_dict.update(agent_overrides)
                base_config = AgentConfig(**config_dict)
                logger.debug(f"Applied {self.environment} overrides for {agent_name}")

        return base_config

    def get_all_agents(self) -> Dict[str, AgentConfig]:
        """Get all agent configurations with environment overrides applied."""
        if self._config is None:
            raise RuntimeError("Config not loaded. Call _load_config() first.")

        return {
            agent_name: self.get_agent_config(agent_name)
            for agent_name in self._config.agents.keys()
        }

    def get_provider(self) -> str:
        """Get default LLM provider."""
        if self._config is None:
            raise RuntimeError("Config not loaded.")
        return self._config.provider

    def reload(self):
        """Manually trigger config reload (for testing or external triggers)."""
        logger.info("Manual config reload requested")
        self._load_config()


# Singleton instance for easy import
_loader = None


def get_config_loader(hot_reload: bool = False) -> ConfigLoader:
    """Get or create the global ConfigLoader instance."""
    global _loader
    if _loader is None:
        _loader = ConfigLoader(hot_reload=hot_reload)
    return _loader
