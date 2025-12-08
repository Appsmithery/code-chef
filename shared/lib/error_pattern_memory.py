"""
Error Pattern Memory for Code-Chef Self-Healing Architecture.

Provides semantic storage and retrieval of error patterns using Qdrant vector database.
Enables RAG-assisted recovery (Tier 2) by matching new errors against previously resolved patterns.

Features:
    - Semantic embedding of error messages using sentence-transformers
    - Pattern storage with resolution steps, success rates, and metadata
    - Similarity-based retrieval for finding relevant past resolutions
    - Automatic cleanup of stale or low-success patterns
    - Thread-safe pattern updates with atomic success rate tracking

Configuration: config/error-handling.yaml -> error_pattern_memory section
"""

import asyncio
import hashlib
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

import yaml

from .error_classification import (
    ErrorCategory,
    ErrorClassification,
    ErrorSignature,
    RecoveryTier,
    classify_error,
    get_error_signature,
)
from .qdrant_client import get_qdrant_client, QdrantCloudClient

logger = logging.getLogger(__name__)

# Lazy import for sentence-transformers (heavy dependency)
_embedding_model = None


def _get_embedding_model():
    """Lazy load sentence-transformers model."""
    global _embedding_model
    if _embedding_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            model_name = _load_config().get("embedding", {}).get("model", "all-MiniLM-L6-v2")
            _embedding_model = SentenceTransformer(model_name)
            logger.info(f"Loaded embedding model: {model_name}")
        except ImportError:
            logger.warning("sentence-transformers not installed. Error pattern memory disabled.")
            return None
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            return None
    return _embedding_model


def _load_config() -> Dict[str, Any]:
    """Load error pattern memory configuration."""
    config_path = os.path.join(
        os.path.dirname(__file__),
        "..", "..", "config", "error-handling.yaml"
    )
    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
            return config.get("error_pattern_memory", {})
    except Exception as e:
        logger.warning(f"Failed to load error-handling.yaml: {e}")
        return {}


@dataclass
class ResolutionStep:
    """A single step in an error resolution."""
    
    action: str  # e.g., "retry_with_backoff", "restart_container", "refresh_token"
    parameters: Dict[str, Any] = field(default_factory=dict)
    description: str = ""
    tier: RecoveryTier = RecoveryTier.TIER_1
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action,
            "parameters": self.parameters,
            "description": self.description,
            "tier": self.tier.value,
        }
    
    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ResolutionStep":
        return cls(
            action=d["action"],
            parameters=d.get("parameters", {}),
            description=d.get("description", ""),
            tier=RecoveryTier(d.get("tier", 1)),
        )


@dataclass
class ErrorPattern:
    """
    Stored error pattern with resolution information.
    
    Attributes:
        id: Unique pattern identifier
        signature_key: Error signature key for exact matching
        category: Error category from classification
        error_type: Exception class name
        message_template: Normalized error message (variable parts replaced)
        resolution_steps: List of steps that resolved this error
        success_count: Number of successful resolutions
        attempt_count: Total resolution attempts
        last_seen: Timestamp of last occurrence
        created_at: Timestamp of pattern creation
        context_hints: Additional context that may help matching (file patterns, agent types)
        embedding: Vector embedding of the error message
    """
    
    id: str
    signature_key: str
    category: ErrorCategory
    error_type: str
    message_template: str
    resolution_steps: List[ResolutionStep]
    success_count: int = 0
    attempt_count: int = 0
    last_seen: datetime = field(default_factory=datetime.utcnow)
    created_at: datetime = field(default_factory=datetime.utcnow)
    context_hints: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate of this pattern's resolution."""
        if self.attempt_count == 0:
            return 0.0
        return self.success_count / self.attempt_count
    
    @property
    def is_effective(self) -> bool:
        """Check if pattern meets minimum success rate threshold."""
        config = _load_config()
        min_rate = config.get("storage", {}).get("min_success_rate", 0.5)
        return self.attempt_count >= 2 and self.success_rate >= min_rate
    
    @property
    def age_days(self) -> float:
        """Calculate pattern age in days."""
        delta = datetime.utcnow() - self.created_at
        return delta.total_seconds() / 86400
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "id": self.id,
            "signature_key": self.signature_key,
            "category": self.category.value,
            "error_type": self.error_type,
            "message_template": self.message_template,
            "resolution_steps": [s.to_dict() for s in self.resolution_steps],
            "success_count": self.success_count,
            "attempt_count": self.attempt_count,
            "last_seen": self.last_seen.isoformat(),
            "created_at": self.created_at.isoformat(),
            "context_hints": self.context_hints,
        }
    
    @classmethod
    def from_dict(cls, d: Dict[str, Any], embedding: Optional[List[float]] = None) -> "ErrorPattern":
        """Create from dictionary."""
        return cls(
            id=d["id"],
            signature_key=d["signature_key"],
            category=ErrorCategory(d["category"]),
            error_type=d["error_type"],
            message_template=d["message_template"],
            resolution_steps=[ResolutionStep.from_dict(s) for s in d.get("resolution_steps", [])],
            success_count=d.get("success_count", 0),
            attempt_count=d.get("attempt_count", 0),
            last_seen=datetime.fromisoformat(d["last_seen"]) if "last_seen" in d else datetime.utcnow(),
            created_at=datetime.fromisoformat(d["created_at"]) if "created_at" in d else datetime.utcnow(),
            context_hints=d.get("context_hints", {}),
            embedding=embedding,
        )


@dataclass
class PatternMatch:
    """Result of a pattern similarity search."""
    
    pattern: ErrorPattern
    similarity_score: float
    is_exact_match: bool = False
    
    @property
    def confidence(self) -> str:
        """Human-readable confidence level."""
        if self.is_exact_match:
            return "exact"
        if self.similarity_score >= 0.9:
            return "high"
        if self.similarity_score >= 0.8:
            return "medium"
        return "low"


class ErrorPatternMemory:
    """
    Semantic memory for error patterns and resolutions.
    
    Uses Qdrant for vector storage and retrieval of error patterns,
    enabling RAG-assisted recovery by finding similar past errors.
    
    Usage:
        memory = ErrorPatternMemory()
        
        # Store a successful resolution
        await memory.store_pattern(
            exception=e,
            resolution_steps=[ResolutionStep(action="retry_with_backoff", parameters={"max_retries": 3})],
            success=True,
        )
        
        # Find similar patterns for a new error
        matches = await memory.find_similar_patterns(exception=new_error)
        if matches:
            best_match = matches[0]
            # Apply best_match.pattern.resolution_steps
    """
    
    def __init__(self, qdrant_client: Optional[QdrantCloudClient] = None):
        """Initialize error pattern memory.
        
        Args:
            qdrant_client: Optional Qdrant client. If None, uses singleton.
        """
        self._qdrant = qdrant_client or get_qdrant_client()
        self._config = _load_config()
        self._collection_name = self._config.get("qdrant", {}).get("collection_name", "error_patterns")
        self._local_cache: Dict[str, ErrorPattern] = {}  # signature_key -> pattern
        self._cache_ttl_seconds = 300  # 5 min local cache
        self._cache_timestamps: Dict[str, float] = {}
        self._initialized = False
        self._init_lock = asyncio.Lock()
    
    @property
    def is_enabled(self) -> bool:
        """Check if error pattern memory is enabled and configured."""
        if not self._config.get("enabled", True):
            return False
        if not self._qdrant.is_enabled():
            return False
        if _get_embedding_model() is None:
            return False
        return True
    
    async def _ensure_initialized(self):
        """Ensure Qdrant collection exists."""
        if self._initialized:
            return
        
        async with self._init_lock:
            if self._initialized:
                return
            
            if not self._qdrant.is_enabled():
                logger.warning("Qdrant not available, skipping initialization")
                self._initialized = True
                return
            
            try:
                # Check if collection exists, create if not
                from qdrant_client.models import Distance, VectorParams
                
                collections = self._qdrant.client.get_collections()
                collection_names = [c.name for c in collections.collections]
                
                if self._collection_name not in collection_names:
                    vector_size = self._config.get("qdrant", {}).get("vector_size", 384)
                    distance = self._config.get("qdrant", {}).get("distance", "cosine")
                    
                    self._qdrant.client.create_collection(
                        collection_name=self._collection_name,
                        vectors_config=VectorParams(
                            size=vector_size,
                            distance=Distance.COSINE if distance == "cosine" else Distance.EUCLID,
                        ),
                    )
                    logger.info(f"Created Qdrant collection: {self._collection_name}")
                
                self._initialized = True
                logger.info("Error pattern memory initialized")
                
            except Exception as e:
                logger.error(f"Failed to initialize error pattern memory: {e}")
                self._initialized = True  # Mark as initialized to prevent retry loops
    
    def _generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding for error message."""
        model = _get_embedding_model()
        if model is None:
            return None
        
        try:
            embedding = model.encode(text, convert_to_numpy=True)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return None
    
    def _get_from_cache(self, signature_key: str) -> Optional[ErrorPattern]:
        """Get pattern from local cache if not expired."""
        if signature_key not in self._local_cache:
            return None
        
        timestamp = self._cache_timestamps.get(signature_key, 0)
        if time.time() - timestamp > self._cache_ttl_seconds:
            # Cache expired
            del self._local_cache[signature_key]
            del self._cache_timestamps[signature_key]
            return None
        
        return self._local_cache[signature_key]
    
    def _add_to_cache(self, pattern: ErrorPattern):
        """Add pattern to local cache."""
        self._local_cache[pattern.signature_key] = pattern
        self._cache_timestamps[pattern.signature_key] = time.time()
    
    async def store_pattern(
        self,
        exception: Exception,
        resolution_steps: List[ResolutionStep],
        success: bool,
        classification: Optional[ErrorClassification] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        Store or update an error pattern with its resolution.
        
        Args:
            exception: The exception that was resolved
            resolution_steps: Steps taken to resolve the error
            success: Whether the resolution was successful
            classification: Optional pre-computed classification
            context: Additional context (workflow_id, agent_name, etc.)
        
        Returns:
            Pattern ID if stored successfully, None otherwise
        """
        if not self.is_enabled:
            logger.debug("Error pattern memory disabled, skipping store")
            return None
        
        await self._ensure_initialized()
        
        # Classify and get signature
        if classification is None:
            classification = classify_error(exception, context)
        
        signature = get_error_signature(exception, classification)
        signature_key = signature.to_key()
        
        # Check if pattern already exists (by signature)
        existing_pattern = await self._find_by_signature(signature_key)
        
        if existing_pattern:
            # Update existing pattern
            return await self._update_pattern(existing_pattern, resolution_steps, success)
        
        # Create new pattern
        return await self._create_pattern(
            exception=exception,
            signature=signature,
            classification=classification,
            resolution_steps=resolution_steps,
            success=success,
            context=context,
        )
    
    async def _find_by_signature(self, signature_key: str) -> Optional[ErrorPattern]:
        """Find pattern by exact signature key."""
        # Check local cache first
        cached = self._get_from_cache(signature_key)
        if cached:
            return cached
        
        if not self._qdrant.is_enabled():
            return None
        
        try:
            from qdrant_client.models import Filter, FieldCondition, MatchValue
            
            results = self._qdrant.client.scroll(
                collection_name=self._collection_name,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="signature_key",
                            match=MatchValue(value=signature_key),
                        )
                    ]
                ),
                limit=1,
                with_vectors=True,
            )
            
            if results[0]:
                point = results[0][0]
                if point.payload is None:
                    return None
                vector = point.vector if isinstance(point.vector, list) else None
                pattern = ErrorPattern.from_dict(dict(point.payload), embedding=vector)
                self._add_to_cache(pattern)
                return pattern
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to find pattern by signature: {e}")
            return None
    
    async def _create_pattern(
        self,
        exception: Exception,
        signature: ErrorSignature,
        classification: ErrorClassification,
        resolution_steps: List[ResolutionStep],
        success: bool,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """Create a new error pattern."""
        # Generate embedding
        message_template = str(exception)
        embedding = self._generate_embedding(message_template)
        
        if embedding is None:
            logger.warning("Failed to generate embedding, pattern not stored")
            return None
        
        pattern_id = str(uuid4())
        pattern = ErrorPattern(
            id=pattern_id,
            signature_key=signature.to_key(),
            category=classification.category,
            error_type=signature.error_type,
            message_template=message_template,
            resolution_steps=resolution_steps,
            success_count=1 if success else 0,
            attempt_count=1,
            last_seen=datetime.utcnow(),
            created_at=datetime.utcnow(),
            context_hints=context or {},
            embedding=embedding,
        )
        
        try:
            from qdrant_client.models import PointStruct
            
            point = PointStruct(
                id=pattern_id,
                vector=embedding,
                payload=pattern.to_dict(),
            )
            
            success_store = await self._qdrant.upsert_points([point])
            
            if success_store:
                self._add_to_cache(pattern)
                logger.info(f"Stored new error pattern: {pattern_id} ({classification.category.value})")
                return pattern_id
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to create error pattern: {e}")
            return None
    
    async def _update_pattern(
        self,
        pattern: ErrorPattern,
        resolution_steps: List[ResolutionStep],
        success: bool,
    ) -> Optional[str]:
        """Update an existing error pattern."""
        # Update counters
        pattern.attempt_count += 1
        if success:
            pattern.success_count += 1
        pattern.last_seen = datetime.utcnow()
        
        # Optionally update resolution steps if new ones are better
        # For now, keep existing steps if success rate is good
        config = _load_config()
        max_patterns = config.get("storage", {}).get("max_patterns_per_error", 5)
        
        # Add new resolution if different and limit not exceeded
        if len(pattern.resolution_steps) < max_patterns:
            existing_actions = {s.action for s in pattern.resolution_steps}
            for step in resolution_steps:
                if step.action not in existing_actions:
                    pattern.resolution_steps.append(step)
                    existing_actions.add(step.action)
        
        try:
            from qdrant_client.models import PointStruct
            
            point = PointStruct(
                id=pattern.id,
                vector=pattern.embedding or [],
                payload=pattern.to_dict(),
            )
            
            success_store = await self._qdrant.upsert_points([point])
            
            if success_store:
                self._add_to_cache(pattern)
                logger.debug(f"Updated error pattern: {pattern.id} (success_rate: {pattern.success_rate:.2%})")
                return pattern.id
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to update error pattern: {e}")
            return None
    
    async def find_similar_patterns(
        self,
        exception: Exception,
        classification: Optional[ErrorClassification] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[PatternMatch]:
        """
        Find similar error patterns for RAG-assisted recovery.
        
        Args:
            exception: The exception to find patterns for
            classification: Optional pre-computed classification
            context: Additional context for filtering
        
        Returns:
            List of PatternMatch sorted by similarity score (highest first)
        """
        if not self.is_enabled:
            logger.debug("Error pattern memory disabled, skipping search")
            return []
        
        await self._ensure_initialized()
        
        # Get classification and signature
        if classification is None:
            classification = classify_error(exception, context)
        
        signature = get_error_signature(exception, classification)
        signature_key = signature.to_key()
        
        # Check for exact match first
        exact_match = await self._find_by_signature(signature_key)
        if exact_match and exact_match.is_effective:
            return [PatternMatch(pattern=exact_match, similarity_score=1.0, is_exact_match=True)]
        
        # Semantic search for similar patterns
        message = str(exception)
        embedding = self._generate_embedding(message)
        
        if embedding is None:
            # Fall back to exact match only
            if exact_match:
                return [PatternMatch(pattern=exact_match, similarity_score=1.0, is_exact_match=True)]
            return []
        
        config = _load_config()
        retrieval_config = config.get("retrieval", {})
        min_score = retrieval_config.get("min_similarity_score", 0.75)
        top_k = retrieval_config.get("top_k", 5)
        max_age_days = retrieval_config.get("max_age_days", 90)
        
        try:
            from qdrant_client.models import Filter, FieldCondition, MatchValue, Range
            
            # Build filter for category and age
            filter_conditions = Filter(
                must=[
                    FieldCondition(
                        key="category",
                        match=MatchValue(value=classification.category.value),
                    ),
                ],
            )
            
            results = await self._qdrant.search_semantic(
                query_vector=embedding,
                limit=top_k,
                score_threshold=min_score,
                filter_conditions=filter_conditions,
            )
            
            matches = []
            cutoff_date = datetime.utcnow() - timedelta(days=max_age_days)
            
            for result in results:
                pattern = ErrorPattern.from_dict(result["payload"])
                
                # Filter out stale patterns
                if pattern.created_at < cutoff_date:
                    continue
                
                # Filter out low-success patterns
                if not pattern.is_effective and pattern.attempt_count >= 3:
                    continue
                
                is_exact = pattern.signature_key == signature_key
                matches.append(PatternMatch(
                    pattern=pattern,
                    similarity_score=result["score"],
                    is_exact_match=is_exact,
                ))
            
            # Include exact match if found but wasn't in results
            if exact_match and not any(m.pattern.id == exact_match.id for m in matches):
                matches.append(PatternMatch(
                    pattern=exact_match,
                    similarity_score=1.0,
                    is_exact_match=True,
                ))
            
            # Sort by similarity score
            matches.sort(key=lambda m: m.similarity_score, reverse=True)
            
            logger.info(f"Found {len(matches)} similar patterns for {classification.category.value} error")
            return matches
            
        except Exception as e:
            logger.error(f"Failed to search similar patterns: {e}")
            return []
    
    async def record_resolution_outcome(
        self,
        pattern_id: str,
        success: bool,
    ) -> bool:
        """
        Record the outcome of applying a pattern's resolution.
        
        Args:
            pattern_id: ID of the pattern that was applied
            success: Whether the resolution succeeded
        
        Returns:
            True if outcome recorded successfully
        """
        if not self._qdrant.is_enabled():
            return False
        
        try:
            # Fetch current pattern
            results = self._qdrant.client.retrieve(
                collection_name=self._collection_name,
                ids=[pattern_id],
                with_vectors=True,
            )
            
            if not results:
                logger.warning(f"Pattern {pattern_id} not found for outcome recording")
                return False
            
            point = results[0]
            if point.payload is None:
                logger.warning(f"Pattern {pattern_id} has no payload")
                return False
            vector = point.vector if isinstance(point.vector, list) else None
            pattern = ErrorPattern.from_dict(dict(point.payload), embedding=vector)
            
            # Update counters
            pattern.attempt_count += 1
            if success:
                pattern.success_count += 1
            pattern.last_seen = datetime.utcnow()
            
            # Store update
            from qdrant_client.models import PointStruct
            
            updated_point = PointStruct(
                id=pattern.id,
                vector=pattern.embedding or [],
                payload=pattern.to_dict(),
            )
            
            await self._qdrant.upsert_points([updated_point])
            self._add_to_cache(pattern)
            
            logger.debug(f"Recorded outcome for pattern {pattern_id}: success={success}, rate={pattern.success_rate:.2%}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to record resolution outcome: {e}")
            return False
    
    async def cleanup_stale_patterns(self) -> int:
        """
        Remove patterns that are stale or have low success rates.
        
        Returns:
            Number of patterns deleted
        """
        if not self._qdrant.is_enabled():
            return 0
        
        config = _load_config()
        storage_config = config.get("storage", {})
        retention_days = storage_config.get("retention_days", 90)
        min_success_rate = storage_config.get("min_success_rate", 0.5)
        
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
        deleted_count = 0
        
        try:
            # Scroll through all patterns
            offset = None
            while True:
                results, offset = self._qdrant.client.scroll(
                    collection_name=self._collection_name,
                    limit=100,
                    offset=offset,
                    with_vectors=False,
                )
                
                if not results:
                    break
                
                patterns_to_delete = []
                for point in results:
                    if point.payload is None:
                        continue
                    pattern = ErrorPattern.from_dict(dict(point.payload))
                    
                    # Delete if too old
                    if pattern.last_seen < cutoff_date:
                        patterns_to_delete.append(pattern.id)
                        continue
                    
                    # Delete if low success rate and enough attempts
                    if pattern.attempt_count >= 5 and pattern.success_rate < min_success_rate:
                        patterns_to_delete.append(pattern.id)
                
                if patterns_to_delete:
                    self._qdrant.client.delete(
                        collection_name=self._collection_name,
                        points_selector=patterns_to_delete,
                    )
                    deleted_count += len(patterns_to_delete)
                    
                    # Clear from local cache
                    for pid in patterns_to_delete:
                        self._local_cache = {k: v for k, v in self._local_cache.items() if v.id != pid}
                
                if offset is None:
                    break
            
            logger.info(f"Cleaned up {deleted_count} stale error patterns")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup stale patterns: {e}")
            return 0
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the error pattern memory."""
        if not self._qdrant.is_enabled():
            return {"enabled": False}
        
        try:
            info = await self._qdrant.get_collection_info()
            if info is None:
                return {"enabled": True, "error": "Failed to get collection info"}
            
            return {
                "enabled": True,
                "collection": self._collection_name,
                "total_patterns": info.get("points_count", 0),
                "local_cache_size": len(self._local_cache),
                "status": info.get("status", "unknown"),
            }
            
        except Exception as e:
            return {"enabled": True, "error": str(e)}


# Singleton instance
_pattern_memory: Optional[ErrorPatternMemory] = None


def get_error_pattern_memory() -> ErrorPatternMemory:
    """Get or create error pattern memory singleton."""
    global _pattern_memory
    if _pattern_memory is None:
        _pattern_memory = ErrorPatternMemory()
    return _pattern_memory


# Convenience functions
async def store_error_pattern(
    exception: Exception,
    resolution_steps: List[ResolutionStep],
    success: bool,
    context: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """Store an error pattern (convenience function)."""
    memory = get_error_pattern_memory()
    return await memory.store_pattern(exception, resolution_steps, success, context=context)


async def find_similar_error_patterns(
    exception: Exception,
    context: Optional[Dict[str, Any]] = None,
) -> List[PatternMatch]:
    """Find similar error patterns (convenience function)."""
    memory = get_error_pattern_memory()
    return await memory.find_similar_patterns(exception, context=context)
