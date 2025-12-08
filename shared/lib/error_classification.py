"""
Error Classification System for Code-Chef Self-Healing Architecture.

Provides 12-category error taxonomy with severity levels and suggested recovery tiers.
This is the foundation of the tiered error recovery system.

Categories:
    - Network: Connection failures, timeouts, DNS errors
    - Auth: Token expiry, invalid credentials, permission denied
    - Resource: OOM, disk full, file not found
    - Dependency: Module not found, import errors
    - LLM: Context overflow, rate limits, model errors
    - MCP: Server crashes, tool failures, connection lost
    - Docker: Container failures, image pull errors
    - Git: Merge conflicts, push failures, stale branches
    - Config: Invalid YAML, missing env vars, schema validation
    - Workflow: State corruption, deadlocks, infinite loops
    - Database: Connection errors, query failures, deadlocks
    - External: Third-party API failures, webhook errors
"""

import re
import logging
import traceback
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)


class ErrorCategory(str, Enum):
    """12-type error categorization for tiered recovery."""
    
    NETWORK = "network"
    AUTH = "auth"
    RESOURCE = "resource"
    DEPENDENCY = "dependency"
    LLM = "llm"
    MCP = "mcp"
    DOCKER = "docker"
    GIT = "git"
    CONFIG = "config"
    WORKFLOW = "workflow"
    DATABASE = "database"
    EXTERNAL = "external"


class ErrorSeverity(str, Enum):
    """Error severity levels aligned with recovery urgency."""
    
    LOW = "low"           # Informational, can be ignored or auto-recovered
    MEDIUM = "medium"     # Should be addressed, may affect single task
    HIGH = "high"         # Critical for current workflow, blocks progress
    CRITICAL = "critical" # System-wide impact, requires immediate attention


class RecoveryTier(int, Enum):
    """Recovery tiers with increasing cost and latency."""
    
    TIER_0 = 0  # Instant heuristic triage (<10ms, 0 tokens)
    TIER_1 = 1  # Automatic remediation (<5s, 0 tokens)
    TIER_2 = 2  # RAG-assisted recovery (<30s, ~50 tokens)
    TIER_3 = 3  # Agent-assisted diagnosis (<2min, ~500 tokens)
    TIER_4 = 4  # Human-in-the-loop escalation (async)


@dataclass
class ErrorClassification:
    """Detailed error classification result."""
    
    category: ErrorCategory
    severity: ErrorSeverity
    suggested_tier: RecoveryTier
    error_code: str
    is_retriable: bool
    requires_state_reset: bool = False
    requires_resource_cleanup: bool = False
    matched_patterns: List[str] = field(default_factory=list)
    remediation_hints: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ErrorSignature:
    """Unique error signature for pattern matching and caching."""
    
    category: ErrorCategory
    error_type: str  # Exception class name
    message_hash: str  # Hash of normalized error message
    file_context: Optional[str] = None  # File where error occurred
    
    def to_key(self) -> str:
        """Generate cache key for error pattern lookup."""
        return f"{self.category.value}:{self.error_type}:{self.message_hash}"
    
    @classmethod
    def from_exception(cls, exception: Exception, category: ErrorCategory) -> "ErrorSignature":
        """Create signature from exception."""
        error_type = type(exception).__name__
        
        # Normalize message: remove variable parts like IDs, timestamps, etc.
        message = str(exception)
        normalized_message = _normalize_error_message(message)
        message_hash = hashlib.md5(normalized_message.encode()).hexdigest()[:12]
        
        # Extract file context from traceback if available
        file_context = None
        try:
            tb = traceback.extract_tb(exception.__traceback__)
            if tb:
                last_frame = tb[-1]
                file_context = f"{last_frame.filename}:{last_frame.lineno}"
        except:
            pass
        
        return cls(
            category=category,
            error_type=error_type,
            message_hash=message_hash,
            file_context=file_context,
        )


# Pattern matchers for each category
# Each pattern is (regex, severity, tier, hints)
ERROR_PATTERNS: Dict[ErrorCategory, List[Tuple[str, ErrorSeverity, RecoveryTier, List[str]]]] = {
    ErrorCategory.NETWORK: [
        (r"connection\s*(refused|reset|timed?\s*out)", ErrorSeverity.MEDIUM, RecoveryTier.TIER_1, 
         ["Retry with exponential backoff", "Check network connectivity", "Verify service is running"]),
        (r"(dns|name\s*resolution)\s*fail", ErrorSeverity.HIGH, RecoveryTier.TIER_1,
         ["Check DNS configuration", "Verify hostname", "Try IP address directly"]),
        (r"ssl|certificate|tls", ErrorSeverity.HIGH, RecoveryTier.TIER_3,
         ["Verify SSL certificates", "Check certificate expiry", "Update CA bundle"]),
        (r"(socket|tcp|udp)\s*error", ErrorSeverity.MEDIUM, RecoveryTier.TIER_1,
         ["Retry connection", "Check firewall rules", "Verify port availability"]),
    ],
    
    ErrorCategory.AUTH: [
        (r"401|unauthorized|unauthenticated", ErrorSeverity.HIGH, RecoveryTier.TIER_1,
         ["Refresh access token", "Re-authenticate", "Check credentials"]),
        (r"403|forbidden|permission\s*denied", ErrorSeverity.HIGH, RecoveryTier.TIER_3,
         ["Check user permissions", "Verify API key scopes", "Contact admin"]),
        (r"token\s*(expired|invalid|revoked)", ErrorSeverity.MEDIUM, RecoveryTier.TIER_1,
         ["Refresh token", "Re-authenticate", "Check token validity"]),
        (r"api[_\s]?key\s*(invalid|missing|expired)", ErrorSeverity.HIGH, RecoveryTier.TIER_3,
         ["Regenerate API key", "Check environment variables", "Verify key permissions"]),
    ],
    
    ErrorCategory.RESOURCE: [
        (r"(out\s*of\s*memory|oom|memory\s*error)", ErrorSeverity.CRITICAL, RecoveryTier.TIER_3,
         ["Reduce batch size", "Increase memory limits", "Optimize memory usage"]),
        (r"(disk\s*full|no\s*space\s*left)", ErrorSeverity.CRITICAL, RecoveryTier.TIER_3,
         ["Clean up temp files", "Prune Docker images", "Increase disk space"]),
        (r"file\s*not\s*found|no\s*such\s*file", ErrorSeverity.MEDIUM, RecoveryTier.TIER_2,
         ["Check file path", "Verify file exists", "Check permissions"]),
        (r"(too\s*many\s*open\s*files|fd\s*limit)", ErrorSeverity.HIGH, RecoveryTier.TIER_3,
         ["Close unused file handles", "Increase ulimit", "Check for resource leaks"]),
    ],
    
    ErrorCategory.DEPENDENCY: [
        (r"(module|package)\s*not\s*found", ErrorSeverity.MEDIUM, RecoveryTier.TIER_1,
         ["Auto-install package", "Check requirements.txt", "Verify virtual environment"]),
        (r"import\s*error|cannot\s*import", ErrorSeverity.MEDIUM, RecoveryTier.TIER_1,
         ["Check import path", "Install missing package", "Verify package version"]),
        (r"version\s*conflict|incompatible\s*version", ErrorSeverity.HIGH, RecoveryTier.TIER_2,
         ["Check version constraints", "Update dependencies", "Use virtual environment"]),
        (r"(circular\s*import|import\s*cycle)", ErrorSeverity.HIGH, RecoveryTier.TIER_3,
         ["Refactor imports", "Use lazy imports", "Check module structure"]),
    ],
    
    ErrorCategory.LLM: [
        (r"(context|token)\s*(overflow|too\s*long|limit\s*exceeded)", ErrorSeverity.MEDIUM, RecoveryTier.TIER_1,
         ["Truncate context", "Summarize input", "Use smaller context window"]),
        (r"(rate\s*limit|429|too\s*many\s*requests)", ErrorSeverity.MEDIUM, RecoveryTier.TIER_1,
         ["Exponential backoff", "Reduce request frequency", "Use request queue"]),
        (r"(model\s*not\s*found|model\s*unavailable)", ErrorSeverity.HIGH, RecoveryTier.TIER_2,
         ["Fallback to alternative model", "Check model availability", "Verify model name"]),
        (r"(content\s*filter|safety|blocked)", ErrorSeverity.HIGH, RecoveryTier.TIER_3,
         ["Modify prompt", "Check content policy", "Use different approach"]),
        (r"(invalid\s*response|json\s*parse|malformed)", ErrorSeverity.MEDIUM, RecoveryTier.TIER_1,
         ["Retry request", "Improve prompt clarity", "Add output format constraints"]),
    ],
    
    ErrorCategory.MCP: [
        (r"mcp\s*server\s*(crash|down|unavailable)", ErrorSeverity.HIGH, RecoveryTier.TIER_1,
         ["Restart MCP server", "Check server logs", "Verify configuration"]),
        (r"tool\s*(not\s*found|unavailable|failed)", ErrorSeverity.MEDIUM, RecoveryTier.TIER_2,
         ["Check tool registration", "Verify tool server", "Use alternative tool"]),
        (r"mcp\s*connection\s*(lost|timeout)", ErrorSeverity.MEDIUM, RecoveryTier.TIER_1,
         ["Reconnect to server", "Check network", "Verify server status"]),
        (r"(partial|incomplete)\s*tool\s*response", ErrorSeverity.MEDIUM, RecoveryTier.TIER_2,
         ["Retry with smaller input", "Check tool timeout", "Handle partial result"]),
    ],
    
    ErrorCategory.DOCKER: [
        (r"container\s*(failed|crash|exit)", ErrorSeverity.HIGH, RecoveryTier.TIER_1,
         ["Restart container", "Check container logs", "Verify Dockerfile"]),
        (r"image\s*(not\s*found|pull\s*fail)", ErrorSeverity.HIGH, RecoveryTier.TIER_1,
         ["Pull image", "Check registry auth", "Verify image name"]),
        (r"port\s*(in\s*use|conflict|bind)", ErrorSeverity.MEDIUM, RecoveryTier.TIER_1,
         ["Use different port", "Stop conflicting container", "Check port mapping"]),
        (r"(volume|mount)\s*(fail|denied)", ErrorSeverity.HIGH, RecoveryTier.TIER_3,
         ["Check volume permissions", "Verify mount path", "Fix SELinux/AppArmor"]),
    ],
    
    ErrorCategory.GIT: [
        (r"merge\s*conflict", ErrorSeverity.HIGH, RecoveryTier.TIER_3,
         ["Resolve conflicts manually", "Use merge tool", "Abort and retry"]),
        (r"(push|pull)\s*(rejected|failed)", ErrorSeverity.MEDIUM, RecoveryTier.TIER_2,
         ["Fetch and rebase", "Check remote status", "Verify credentials"]),
        (r"stale\s*branch|diverged", ErrorSeverity.MEDIUM, RecoveryTier.TIER_2,
         ["Fetch latest changes", "Rebase on main", "Force update if safe"]),
        (r"(detached\s*head|no\s*branch)", ErrorSeverity.LOW, RecoveryTier.TIER_1,
         ["Create new branch", "Checkout existing branch", "Stash changes"]),
    ],
    
    ErrorCategory.CONFIG: [
        (r"(yaml|json)\s*(parse|syntax)\s*error", ErrorSeverity.HIGH, RecoveryTier.TIER_2,
         ["Validate config syntax", "Check for special characters", "Use linter"]),
        (r"(missing|undefined)\s*(env|environment)\s*var", ErrorSeverity.HIGH, RecoveryTier.TIER_2,
         ["Set environment variable", "Check .env file", "Use default value"]),
        (r"(schema|validation)\s*(error|fail)", ErrorSeverity.MEDIUM, RecoveryTier.TIER_2,
         ["Check config against schema", "Fix validation errors", "Update config"]),
        (r"(config|settings)\s*not\s*found", ErrorSeverity.HIGH, RecoveryTier.TIER_2,
         ["Create config file", "Check config path", "Use default config"]),
    ],
    
    ErrorCategory.WORKFLOW: [
        (r"(deadlock|cycle\s*detect|circular)", ErrorSeverity.CRITICAL, RecoveryTier.TIER_3,
         ["Break deadlock", "Reset workflow state", "Check step dependencies"]),
        (r"(state\s*corrupt|invalid\s*state)", ErrorSeverity.CRITICAL, RecoveryTier.TIER_3,
         ["Reset to last checkpoint", "Rebuild state", "Escalate to HITL"]),
        (r"(infinite\s*loop|max\s*iterations)", ErrorSeverity.HIGH, RecoveryTier.TIER_1,
         ["Break loop", "Increment backoff", "Add termination condition"]),
        (r"(workflow\s*collision|concurrent\s*mod)", ErrorSeverity.HIGH, RecoveryTier.TIER_2,
         ["Acquire lock", "Retry with backoff", "Use optimistic locking"]),
    ],
    
    ErrorCategory.DATABASE: [
        (r"(db|database)\s*connection\s*(fail|refused)", ErrorSeverity.HIGH, RecoveryTier.TIER_1,
         ["Retry connection", "Check database status", "Verify credentials"]),
        (r"(query|sql)\s*(error|fail|timeout)", ErrorSeverity.MEDIUM, RecoveryTier.TIER_2,
         ["Optimize query", "Check query syntax", "Increase timeout"]),
        (r"(db|database)\s*deadlock", ErrorSeverity.HIGH, RecoveryTier.TIER_1,
         ["Retry transaction", "Check lock ordering", "Reduce transaction scope"]),
        (r"constraint\s*(violation|error)", ErrorSeverity.MEDIUM, RecoveryTier.TIER_2,
         ["Check data integrity", "Fix constraint issue", "Update related records"]),
    ],
    
    ErrorCategory.EXTERNAL: [
        (r"(third[_\-]?party|external)\s*(api|service)\s*(fail|down)", ErrorSeverity.HIGH, RecoveryTier.TIER_1,
         ["Retry with backoff", "Check service status", "Use fallback service"]),
        (r"webhook\s*(fail|timeout|error)", ErrorSeverity.MEDIUM, RecoveryTier.TIER_1,
         ["Retry webhook", "Check endpoint", "Queue for later delivery"]),
        (r"(linear|github|slack)\s*(api|integration)\s*(fail|error)", ErrorSeverity.HIGH, RecoveryTier.TIER_2,
         ["Retry API call", "Check integration status", "Verify API tokens"]),
        (r"(rate\s*limit|quota)\s*exceeded", ErrorSeverity.MEDIUM, RecoveryTier.TIER_1,
         ["Wait and retry", "Reduce request rate", "Upgrade API tier"]),
    ],
}


def _normalize_error_message(message: str) -> str:
    """Normalize error message for consistent hashing.
    
    Removes variable parts like:
    - UUIDs, IDs
    - Timestamps
    - IP addresses
    - File paths with variable names
    - Memory addresses
    """
    # Remove UUIDs
    message = re.sub(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", "<UUID>", message, flags=re.IGNORECASE)
    
    # Remove hex addresses (e.g., 0x7fff...)
    message = re.sub(r"0x[0-9a-f]+", "<ADDR>", message, flags=re.IGNORECASE)
    
    # Remove IP addresses
    message = re.sub(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(:\d+)?", "<IP>", message)
    
    # Remove timestamps (ISO format)
    message = re.sub(r"\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}(\.\d+)?([+-]\d{2}:?\d{2}|Z)?", "<TIMESTAMP>", message)
    
    # Remove numeric IDs (standalone numbers > 3 digits)
    message = re.sub(r"\b\d{4,}\b", "<ID>", message)
    
    # Normalize whitespace
    message = re.sub(r"\s+", " ", message).strip().lower()
    
    return message


def classify_error(
    exception: Exception,
    context: Optional[Dict[str, Any]] = None,
) -> ErrorClassification:
    """Classify an exception into category, severity, and suggested recovery tier.
    
    Args:
        exception: The exception to classify
        context: Optional context dict with additional info (workflow_id, step_id, etc.)
    
    Returns:
        ErrorClassification with full classification details
    
    Example:
        >>> try:
        ...     raise ConnectionError("Connection timed out to api.example.com")
        ... except Exception as e:
        ...     classification = classify_error(e)
        ...     print(f"Category: {classification.category}, Tier: {classification.suggested_tier}")
        Category: ErrorCategory.NETWORK, Tier: RecoveryTier.TIER_1
    """
    context = context or {}
    error_message = str(exception).lower()
    error_type = type(exception).__name__
    
    # Try to match against known patterns
    matched_category = None
    matched_severity = ErrorSeverity.MEDIUM
    matched_tier = RecoveryTier.TIER_2
    matched_patterns = []
    remediation_hints = []
    
    # First, try type-based classification
    type_classifications = {
        # Network errors
        (ConnectionError, ConnectionRefusedError, ConnectionResetError, TimeoutError): 
            (ErrorCategory.NETWORK, ErrorSeverity.MEDIUM, RecoveryTier.TIER_1),
        
        # Auth errors
        (PermissionError,): 
            (ErrorCategory.AUTH, ErrorSeverity.HIGH, RecoveryTier.TIER_3),
        
        # Resource errors
        (MemoryError, FileNotFoundError, OSError): 
            (ErrorCategory.RESOURCE, ErrorSeverity.HIGH, RecoveryTier.TIER_2),
        
        # Dependency errors
        (ModuleNotFoundError, ImportError): 
            (ErrorCategory.DEPENDENCY, ErrorSeverity.MEDIUM, RecoveryTier.TIER_1),
        
        # Config errors
        (ValueError, TypeError, AttributeError, KeyError): 
            (ErrorCategory.CONFIG, ErrorSeverity.MEDIUM, RecoveryTier.TIER_2),
    }
    
    for exc_types, (category, severity, tier) in type_classifications.items():
        if isinstance(exception, exc_types):
            matched_category = category
            matched_severity = severity
            matched_tier = tier
            break
    
    # Then, refine with pattern matching
    for category, patterns in ERROR_PATTERNS.items():
        for pattern, severity, tier, hints in patterns:
            if re.search(pattern, error_message, re.IGNORECASE):
                matched_patterns.append(pattern)
                remediation_hints.extend(hints)
                
                # Prefer pattern-based category if found (more specific)
                if matched_category is None or category != matched_category:
                    matched_category = category
                    matched_severity = severity
                    matched_tier = tier
    
    # Default if no match
    if matched_category is None:
        matched_category = ErrorCategory.EXTERNAL
        matched_tier = RecoveryTier.TIER_2
    
    # Determine if retriable
    is_retriable = matched_tier in (RecoveryTier.TIER_0, RecoveryTier.TIER_1, RecoveryTier.TIER_2)
    
    # Check for state reset requirements
    requires_state_reset = matched_category in (ErrorCategory.WORKFLOW, ErrorCategory.DATABASE)
    requires_resource_cleanup = matched_category in (ErrorCategory.RESOURCE, ErrorCategory.DOCKER)
    
    # Generate error code
    error_code = f"{matched_category.value.upper()}_{error_type.upper()}"
    
    return ErrorClassification(
        category=matched_category,
        severity=matched_severity,
        suggested_tier=matched_tier,
        error_code=error_code,
        is_retriable=is_retriable,
        requires_state_reset=requires_state_reset,
        requires_resource_cleanup=requires_resource_cleanup,
        matched_patterns=matched_patterns[:3],  # Limit patterns for logging
        remediation_hints=list(set(remediation_hints))[:5],  # Dedupe and limit hints
        context=context,
    )


def get_error_signature(
    exception: Exception,
    classification: Optional[ErrorClassification] = None,
) -> ErrorSignature:
    """Generate unique signature for an error for pattern matching.
    
    Args:
        exception: The exception
        classification: Optional pre-computed classification
    
    Returns:
        ErrorSignature for cache lookups
    """
    if classification is None:
        classification = classify_error(exception)
    
    return ErrorSignature.from_exception(exception, classification.category)


# Convenience functions for specific error types
def is_network_error(exception: Exception) -> bool:
    """Check if exception is a network error."""
    return classify_error(exception).category == ErrorCategory.NETWORK


def is_auth_error(exception: Exception) -> bool:
    """Check if exception is an auth error."""
    return classify_error(exception).category == ErrorCategory.AUTH


def is_llm_error(exception: Exception) -> bool:
    """Check if exception is an LLM error."""
    return classify_error(exception).category == ErrorCategory.LLM


def is_retriable(exception: Exception) -> bool:
    """Check if exception is retriable at Tier 0-2."""
    return classify_error(exception).is_retriable


def needs_human_intervention(exception: Exception) -> bool:
    """Check if exception requires human intervention (Tier 4)."""
    classification = classify_error(exception)
    return (
        classification.suggested_tier == RecoveryTier.TIER_4 or
        classification.severity == ErrorSeverity.CRITICAL
    )
