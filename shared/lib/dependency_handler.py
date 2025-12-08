"""
Dependency Error Handler for Orchestrator and Target Project Dependencies.

This module provides:
1. Detection and parsing of ModuleNotFoundError/ImportError
2. Classification: orchestrator vs. target project dependency
3. Auto-remediation: pip install or add to requirements.txt
4. Escalation to Linear when auto-remediation fails
5. Caching to prevent repeated remediation attempts for same module

Architecture:
- DependencyError: Pydantic model for parsed dependency errors
- DependencyRemediationStrategy: Enum for remediation approaches
- DependencyErrorHandler: Main handler class with remediation logic
"""

import asyncio
import logging
import os
import re
import subprocess
import sys
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from pydantic import BaseModel, Field
from langsmith import traceable

logger = logging.getLogger(__name__)


class DependencyScope(str, Enum):
    """Where the dependency is needed."""
    
    ORCHESTRATOR = "orchestrator"  # code-chef's own dependencies
    TARGET_PROJECT = "target_project"  # Dependency in the workspace being orchestrated
    UNKNOWN = "unknown"


class DependencyRemediationStrategy(str, Enum):
    """How to remediate the missing dependency."""
    
    PIP_INSTALL_ORCHESTRATOR = "pip_install_orchestrator"  # Install in orchestrator's environment
    PIP_INSTALL_TARGET = "pip_install_target"  # Install in target project's environment
    ADD_TO_REQUIREMENTS = "add_to_requirements"  # Add to requirements.txt and install
    DOCKER_REBUILD = "docker_rebuild"  # Requires container rebuild
    ESCALATE = "escalate"  # Cannot auto-remediate, escalate to human
    SKIP = "skip"  # Skip remediation (already attempted or not possible)


class DependencyRemediationResult(str, Enum):
    """Result of remediation attempt."""
    
    SUCCESS = "success"
    FAILED = "failed"
    ESCALATED = "escalated"
    SKIPPED = "skipped"


class DependencyError(BaseModel):
    """Parsed dependency error with context."""
    
    module_name: str  # The missing module (e.g., "jinja2")
    package_name: Optional[str] = None  # The pip package name if different
    scope: DependencyScope = DependencyScope.UNKNOWN
    original_exception: str  # Full exception string
    exception_type: str  # "ModuleNotFoundError" or "ImportError"
    traceback_file: Optional[str] = None  # File where error occurred
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Remediation tracking
    remediation_attempts: int = 0
    last_remediation_strategy: Optional[DependencyRemediationStrategy] = None
    remediation_result: Optional[DependencyRemediationResult] = None
    remediation_error: Optional[str] = None


class DependencyRemediationPlan(BaseModel):
    """Plan for remediating a dependency error."""
    
    error: DependencyError
    strategy: DependencyRemediationStrategy
    target_requirements_file: Optional[str] = None  # For ADD_TO_REQUIREMENTS
    target_environment: Optional[str] = None  # Python executable or venv path
    docker_service: Optional[str] = None  # For DOCKER_REBUILD
    escalation_reason: Optional[str] = None  # For ESCALATE


# Common module → package mappings (module name differs from pip package name)
MODULE_TO_PACKAGE_MAP: Dict[str, str] = {
    "cv2": "opencv-python",
    "PIL": "Pillow",
    "sklearn": "scikit-learn",
    "yaml": "pyyaml",
    "bs4": "beautifulsoup4",
    "dotenv": "python-dotenv",
    "git": "GitPython",
    "jose": "python-jose",
    "magic": "python-magic",
    "dateutil": "python-dateutil",
}

# Modules that should never be auto-installed (system/builtin)
BUILTIN_MODULES: Set[str] = {
    "sys", "os", "re", "json", "logging", "typing", "pathlib", "datetime",
    "asyncio", "collections", "functools", "itertools", "contextlib",
    "dataclasses", "enum", "abc", "io", "copy", "math", "random", "time",
    "threading", "multiprocessing", "subprocess", "tempfile", "shutil",
    "unittest", "inspect", "traceback", "warnings", "weakref", "gc",
}

# Orchestrator's own directories (if error originates here, it's orchestrator scope)
ORCHESTRATOR_PATHS = [
    "agent_orchestrator",
    "shared/lib",
    "shared/services",
    "shared/mcp",
]


class DependencyErrorHandler:
    """
    Handles dependency errors with auto-remediation and escalation.
    
    Usage:
        handler = DependencyErrorHandler()
        
        try:
            from jinja2 import Template
        except ModuleNotFoundError as e:
            error = handler.parse_error(e, traceback_file="workflow_engine.py")
            plan = handler.create_remediation_plan(error, workspace_path="/path/to/project")
            result = await handler.execute_remediation(plan)
    """
    
    def __init__(
        self,
        orchestrator_root: str = ".",
        linear_client: Optional[Any] = None,
        max_remediation_attempts: int = 2,
    ):
        """
        Initialize the dependency error handler.
        
        Args:
            orchestrator_root: Root path of the code-chef orchestrator
            linear_client: Optional Linear client for escalation
            max_remediation_attempts: Max times to attempt remediation per module
        """
        self.orchestrator_root = Path(orchestrator_root).resolve()
        self.linear_client = linear_client
        self.max_remediation_attempts = max_remediation_attempts
        
        # Cache of remediation attempts to prevent loops
        self._remediation_cache: Dict[str, DependencyError] = {}
        
        # Detect orchestrator requirements file
        self.orchestrator_requirements = self._find_requirements_file(
            self.orchestrator_root / "agent_orchestrator"
        )
        
        logger.info(
            f"DependencyErrorHandler initialized. "
            f"Orchestrator root: {self.orchestrator_root}, "
            f"Requirements: {self.orchestrator_requirements}"
        )
    
    def _find_requirements_file(self, path: Path) -> Optional[Path]:
        """Find requirements.txt in a directory."""
        for filename in ["requirements.txt", "requirements.in", "pyproject.toml"]:
            req_file = path / filename
            if req_file.exists():
                return req_file
        return None
    
    @traceable(name="dependency_parse_error", tags=["dependency", "error", "parsing"])
    def parse_error(
        self,
        exception: Exception,
        traceback_file: Optional[str] = None,
        traceback_str: Optional[str] = None,
    ) -> Optional[DependencyError]:
        """
        Parse a ModuleNotFoundError or ImportError to extract module info.
        
        Args:
            exception: The exception to parse
            traceback_file: File where the error occurred (optional)
            traceback_str: Full traceback string for context
            
        Returns:
            DependencyError if parseable, None otherwise
        """
        if not isinstance(exception, (ModuleNotFoundError, ImportError)):
            return None
        
        exception_str = str(exception)
        exception_type = type(exception).__name__
        
        # Extract module name from error message
        module_name = self._extract_module_name(exception_str)
        
        if not module_name:
            logger.warning(f"Could not extract module name from: {exception_str}")
            return None
        
        # Check if it's a builtin (shouldn't happen, but safety check)
        if module_name in BUILTIN_MODULES:
            logger.warning(f"Error for builtin module '{module_name}' - likely a deeper issue")
            return None
        
        # Determine package name (may differ from module name)
        package_name = MODULE_TO_PACKAGE_MAP.get(module_name, module_name)
        
        # Determine scope from traceback
        scope = self._determine_scope(traceback_file, traceback_str)
        
        # Check remediation cache
        cache_key = f"{module_name}:{scope.value}"
        if cache_key in self._remediation_cache:
            cached = self._remediation_cache[cache_key]
            cached.remediation_attempts += 1
            return cached
        
        error = DependencyError(
            module_name=module_name,
            package_name=package_name,
            scope=scope,
            original_exception=exception_str,
            exception_type=exception_type,
            traceback_file=traceback_file,
        )
        
        self._remediation_cache[cache_key] = error
        return error
    
    def _extract_module_name(self, error_message: str) -> Optional[str]:
        """Extract module name from error message."""
        # Pattern: "No module named 'module_name'" or "No module named 'parent.child'"
        patterns = [
            r"No module named ['\"]([^'\"]+)['\"]",
            r"cannot import name ['\"]([^'\"]+)['\"]",
            r"ImportError: ([a-zA-Z_][a-zA-Z0-9_]*)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, error_message)
            if match:
                module = match.group(1)
                # Return top-level module (e.g., "jinja2" from "jinja2.template")
                return module.split(".")[0]
        
        return None
    
    def _determine_scope(
        self,
        traceback_file: Optional[str],
        traceback_str: Optional[str],
    ) -> DependencyScope:
        """Determine if error is in orchestrator or target project."""
        
        # Check traceback file
        if traceback_file:
            for orch_path in ORCHESTRATOR_PATHS:
                if orch_path in traceback_file:
                    return DependencyScope.ORCHESTRATOR
        
        # Check full traceback for orchestrator paths
        if traceback_str:
            for orch_path in ORCHESTRATOR_PATHS:
                if orch_path in traceback_str:
                    return DependencyScope.ORCHESTRATOR
        
        # If we can't determine, assume target project (safer to not modify orchestrator)
        return DependencyScope.TARGET_PROJECT
    
    @traceable(name="dependency_create_plan", tags=["dependency", "remediation", "planning"])
    def create_remediation_plan(
        self,
        error: DependencyError,
        workspace_path: Optional[str] = None,
        docker_context: Optional[Dict[str, Any]] = None,
    ) -> DependencyRemediationPlan:
        """
        Create a remediation plan for a dependency error.
        
        Args:
            error: Parsed dependency error
            workspace_path: Path to target workspace (for target project errors)
            docker_context: Docker context if running in container
            
        Returns:
            DependencyRemediationPlan with strategy and context
        """
        # Check if we've exceeded remediation attempts
        if error.remediation_attempts >= self.max_remediation_attempts:
            return DependencyRemediationPlan(
                error=error,
                strategy=DependencyRemediationStrategy.ESCALATE,
                escalation_reason=f"Exceeded max remediation attempts ({self.max_remediation_attempts}) for module '{error.module_name}'",
            )
        
        # Determine strategy based on scope
        if error.scope == DependencyScope.ORCHESTRATOR:
            # Running in Docker?
            if docker_context and docker_context.get("in_container"):
                return DependencyRemediationPlan(
                    error=error,
                    strategy=DependencyRemediationStrategy.DOCKER_REBUILD,
                    target_requirements_file=str(self.orchestrator_requirements),
                    docker_service=docker_context.get("service_name", "agent_orchestrator"),
                )
            else:
                # Local execution - can pip install directly
                return DependencyRemediationPlan(
                    error=error,
                    strategy=DependencyRemediationStrategy.PIP_INSTALL_ORCHESTRATOR,
                    target_requirements_file=str(self.orchestrator_requirements) if self.orchestrator_requirements else None,
                    target_environment=sys.executable,
                )
        
        elif error.scope == DependencyScope.TARGET_PROJECT:
            if not workspace_path:
                return DependencyRemediationPlan(
                    error=error,
                    strategy=DependencyRemediationStrategy.ESCALATE,
                    escalation_reason="Cannot determine target workspace path for remediation",
                )
            
            # Find requirements.txt in target project
            target_req = self._find_requirements_file(Path(workspace_path))
            
            if target_req:
                return DependencyRemediationPlan(
                    error=error,
                    strategy=DependencyRemediationStrategy.ADD_TO_REQUIREMENTS,
                    target_requirements_file=str(target_req),
                    target_environment=self._find_target_python(workspace_path),
                )
            else:
                # No requirements.txt, just pip install
                return DependencyRemediationPlan(
                    error=error,
                    strategy=DependencyRemediationStrategy.PIP_INSTALL_TARGET,
                    target_environment=self._find_target_python(workspace_path),
                )
        
        else:
            # Unknown scope - escalate
            return DependencyRemediationPlan(
                error=error,
                strategy=DependencyRemediationStrategy.ESCALATE,
                escalation_reason=f"Unknown dependency scope for module '{error.module_name}'",
            )
    
    def _find_target_python(self, workspace_path: str) -> str:
        """Find Python executable for target workspace."""
        workspace = Path(workspace_path)
        
        # Check for common venv locations
        venv_paths = [
            workspace / ".venv" / "Scripts" / "python.exe",  # Windows
            workspace / ".venv" / "bin" / "python",  # Unix
            workspace / "venv" / "Scripts" / "python.exe",
            workspace / "venv" / "bin" / "python",
        ]
        
        for venv_python in venv_paths:
            if venv_python.exists():
                return str(venv_python)
        
        # Fall back to system Python
        return sys.executable
    
    @traceable(name="dependency_execute_remediation", tags=["dependency", "remediation", "execution"])
    async def execute_remediation(
        self,
        plan: DependencyRemediationPlan,
    ) -> Tuple[DependencyRemediationResult, Optional[str]]:
        """
        Execute a remediation plan.
        
        Args:
            plan: The remediation plan to execute
            
        Returns:
            Tuple of (result, error_message)
        """
        strategy = plan.strategy
        error = plan.error
        
        logger.info(
            f"Executing remediation for '{error.module_name}' "
            f"using strategy: {strategy.value}"
        )
        
        try:
            if strategy == DependencyRemediationStrategy.PIP_INSTALL_ORCHESTRATOR:
                return await self._pip_install(
                    error.package_name or error.module_name,
                    plan.target_environment,
                    add_to_requirements=plan.target_requirements_file,
                )
            
            elif strategy == DependencyRemediationStrategy.PIP_INSTALL_TARGET:
                return await self._pip_install(
                    error.package_name or error.module_name,
                    plan.target_environment,
                    add_to_requirements=None,
                )
            
            elif strategy == DependencyRemediationStrategy.ADD_TO_REQUIREMENTS:
                return await self._add_to_requirements_and_install(
                    error.package_name or error.module_name,
                    plan.target_requirements_file,
                    plan.target_environment,
                )
            
            elif strategy == DependencyRemediationStrategy.DOCKER_REBUILD:
                return await self._escalate_docker_rebuild(error, plan)
            
            elif strategy == DependencyRemediationStrategy.ESCALATE:
                return await self._escalate_to_linear(error, plan)
            
            else:
                return DependencyRemediationResult.SKIPPED, f"Unknown strategy: {strategy}"
        
        except Exception as e:
            logger.exception(f"Remediation failed for '{error.module_name}'")
            error.remediation_error = str(e)
            error.remediation_result = DependencyRemediationResult.FAILED
            return DependencyRemediationResult.FAILED, str(e)
    
    async def _pip_install(
        self,
        package_name: str,
        python_executable: Optional[str],
        add_to_requirements: Optional[str] = None,
    ) -> Tuple[DependencyRemediationResult, Optional[str]]:
        """Install package using pip."""
        python = python_executable or sys.executable
        
        logger.info(f"Installing '{package_name}' using: {python}")
        
        try:
            # Run pip install
            result = await asyncio.to_thread(
                subprocess.run,
                [python, "-m", "pip", "install", package_name],
                capture_output=True,
                text=True,
                timeout=120,
            )
            
            if result.returncode != 0:
                return DependencyRemediationResult.FAILED, result.stderr
            
            # Optionally add to requirements.txt
            if add_to_requirements:
                await self._append_to_requirements(add_to_requirements, package_name)
            
            logger.info(f"Successfully installed '{package_name}'")
            return DependencyRemediationResult.SUCCESS, None
            
        except subprocess.TimeoutExpired:
            return DependencyRemediationResult.FAILED, f"pip install timed out for '{package_name}'"
        except Exception as e:
            return DependencyRemediationResult.FAILED, str(e)
    
    async def _add_to_requirements_and_install(
        self,
        package_name: str,
        requirements_file: str,
        python_executable: Optional[str],
    ) -> Tuple[DependencyRemediationResult, Optional[str]]:
        """Add package to requirements.txt and install."""
        
        # Add to requirements first
        await self._append_to_requirements(requirements_file, package_name)
        
        # Then install
        return await self._pip_install(package_name, python_executable, add_to_requirements=None)
    
    async def _append_to_requirements(self, requirements_file: str, package_name: str):
        """Append package to requirements.txt if not already present."""
        req_path = Path(requirements_file)
        
        if not req_path.exists():
            logger.warning(f"Requirements file not found: {requirements_file}")
            return
        
        # Check if already in file
        content = req_path.read_text()
        package_base = package_name.split(">=")[0].split("==")[0].strip()
        
        if package_base.lower() in content.lower():
            logger.info(f"'{package_name}' already in {requirements_file}")
            return
        
        # Append with version specifier
        with open(req_path, "a") as f:
            f.write(f"\n{package_name}>=0.1.0  # Auto-added by dependency handler\n")
        
        logger.info(f"Added '{package_name}' to {requirements_file}")
    
    async def _escalate_docker_rebuild(
        self,
        error: DependencyError,
        plan: DependencyRemediationPlan,
    ) -> Tuple[DependencyRemediationResult, Optional[str]]:
        """Escalate: Docker container needs rebuild."""
        
        message = (
            f"**Dependency Missing in Docker Container**\n\n"
            f"Module `{error.module_name}` (package: `{error.package_name}`) is missing "
            f"in the `{plan.docker_service}` container.\n\n"
            f"**Remediation Required:**\n"
            f"1. Add `{error.package_name}>=0.1.0` to `{plan.target_requirements_file}`\n"
            f"2. Rebuild container: `docker compose build {plan.docker_service}`\n"
            f"3. Restart: `docker compose up -d {plan.docker_service}`\n\n"
            f"**Original Error:**\n```\n{error.original_exception}\n```"
        )
        
        return await self._create_linear_issue(
            title=f"[Dependency] Missing module '{error.module_name}' in {plan.docker_service}",
            description=message,
            labels=["dependency", "infrastructure", "auto-detected"],
        )
    
    async def _escalate_to_linear(
        self,
        error: DependencyError,
        plan: DependencyRemediationPlan,
    ) -> Tuple[DependencyRemediationResult, Optional[str]]:
        """Escalate to Linear for manual intervention."""
        
        message = (
            f"**Dependency Error Requires Manual Intervention**\n\n"
            f"Module `{error.module_name}` (package: `{error.package_name}`) is missing.\n\n"
            f"**Scope:** {error.scope.value}\n"
            f"**Escalation Reason:** {plan.escalation_reason}\n"
            f"**Remediation Attempts:** {error.remediation_attempts}\n\n"
            f"**Original Error:**\n```\n{error.original_exception}\n```\n\n"
            f"**Traceback File:** {error.traceback_file or 'Unknown'}"
        )
        
        return await self._create_linear_issue(
            title=f"[Dependency] Cannot auto-remediate '{error.module_name}'",
            description=message,
            labels=["dependency", "needs-attention", "auto-detected"],
        )
    
    async def _create_linear_issue(
        self,
        title: str,
        description: str,
        labels: List[str],
    ) -> Tuple[DependencyRemediationResult, Optional[str]]:
        """Create a Linear issue for escalation."""
        
        if self.linear_client:
            try:
                # Use existing Linear client
                issue = await self.linear_client.create_issue(
                    title=title,
                    description=description,
                    labels=labels,
                    priority=2,  # Medium priority
                )
                logger.info(f"Created Linear issue: {issue.get('id')}")
                return DependencyRemediationResult.ESCALATED, None
                
            except Exception as e:
                logger.error(f"Failed to create Linear issue: {e}")
                return DependencyRemediationResult.ESCALATED, f"Linear issue creation failed: {e}"
        else:
            # Log escalation without Linear
            logger.warning(
                f"ESCALATION (no Linear client):\n"
                f"Title: {title}\n"
                f"Description: {description}"
            )
            return DependencyRemediationResult.ESCALATED, "Logged escalation (no Linear client)"
    
    def clear_cache(self, module_name: Optional[str] = None):
        """Clear remediation cache."""
        if module_name:
            keys_to_remove = [k for k in self._remediation_cache if k.startswith(f"{module_name}:")]
            for key in keys_to_remove:
                del self._remediation_cache[key]
        else:
            self._remediation_cache.clear()


# Singleton instance for easy access
_handler_instance: Optional[DependencyErrorHandler] = None


def get_dependency_handler(
    orchestrator_root: str = ".",
    linear_client: Optional[Any] = None,
) -> DependencyErrorHandler:
    """Get or create the singleton DependencyErrorHandler instance."""
    global _handler_instance
    
    if _handler_instance is None:
        _handler_instance = DependencyErrorHandler(
            orchestrator_root=orchestrator_root,
            linear_client=linear_client,
        )
    
    return _handler_instance
