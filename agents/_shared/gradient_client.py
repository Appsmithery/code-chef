"""
DigitalOcean Gradient AI Platform Client

Provides OpenAI-compatible interface to Gradient with automatic Langfuse tracing.
Supports agent-specific model selection and fallback handling.
"""

import os
from typing import Optional, Dict, Any, List
from langfuse.openai import openai

# Langfuse configuration (must be set before importing langfuse)
os.environ.setdefault("LANGFUSE_HOST", os.getenv("LANGFUSE_HOST", "https://us.cloud.langfuse.com"))
os.environ.setdefault("LANGFUSE_SECRET_KEY", os.getenv("LANGFUSE_SECRET_KEY", ""))
os.environ.setdefault("LANGFUSE_PUBLIC_KEY", os.getenv("LANGFUSE_PUBLIC_KEY", ""))

# Gradient configuration
GRADIENT_API_KEY = os.getenv("GRADIENT_MODEL_ACCESS_KEY") or os.getenv("GRADIENT_API_KEY")  # Prefer MODEL_ACCESS_KEY for OpenAI compatibility
GRADIENT_BASE_URL = os.getenv("GRADIENT_BASE_URL", "https://api.digitalocean.com/v2/ai/inference")  # Full inference path
GRADIENT_MODEL = os.getenv("GRADIENT_MODEL", "llama-3.1-8b-instruct")

# Validate configuration
GRADIENT_ENABLED = bool(GRADIENT_API_KEY)
LANGFUSE_ENABLED = bool(os.getenv("LANGFUSE_SECRET_KEY") and os.getenv("LANGFUSE_PUBLIC_KEY"))


class GradientClient:
    """
    Gradient AI Platform client with Langfuse tracing.
    
    Automatically wraps OpenAI-compatible calls with Langfuse for observability.
    Supports per-agent model selection and fallback to shared model.
    """
    
    def __init__(
        self,
        agent_name: str,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None
    ):
        """
        Initialize Gradient client.
        
        Args:
            agent_name: Name of the calling agent (for Langfuse metadata)
            model: Specific model override (defaults to GRADIENT_MODEL env var)
            api_key: API key override (defaults to GRADIENT_API_KEY env var)
            base_url: Base URL override (defaults to GRADIENT_BASE_URL env var)
        """
        self.agent_name = agent_name
        self.model = model or GRADIENT_MODEL
        self.api_key = api_key or GRADIENT_API_KEY
        self.base_url = base_url or GRADIENT_BASE_URL
        
        if not self.api_key:
            print(f"[WARNING] {agent_name}: GRADIENT_API_KEY not set, LLM calls will fail")
            self.client = None
        else:
            # Initialize OpenAI client with Gradient endpoint
            # Langfuse wrapper automatically traces all calls
            self.client = openai.OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
            print(f"[GRADIENT] {agent_name}: Initialized with model {self.model}")
            if LANGFUSE_ENABLED:
                print(f"[LANGFUSE] {agent_name}: Tracing ENABLED (host: {os.getenv('LANGFUSE_HOST')})")
            else:
                print(f"[LANGFUSE] {agent_name}: Tracing DISABLED (missing keys)")
    
    async def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate completion with automatic Langfuse tracing.
        
        Args:
            prompt: User prompt
            system_prompt: System prompt (optional)
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            metadata: Additional metadata for Langfuse trace
            
        Returns:
            Dict with 'content', 'model', 'tokens', 'finish_reason'
        """
        if not self.client:
            raise RuntimeError(f"{self.agent_name}: Gradient client not initialized (missing API key)")
        
        # Build messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        # Build Langfuse metadata
        trace_metadata = {
            "langfuse_session_id": metadata.get("task_id", "unknown") if metadata else "unknown",
            "langfuse_user_id": self.agent_name,
            "langfuse_tags": ["gradient", "production", self.agent_name],
            **(metadata or {})
        }
        
        try:
            # Call Gradient API with Langfuse tracing
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                metadata=trace_metadata
            )
            
            return {
                "content": response.choices[0].message.content,
                "model": self.model,
                "tokens": response.usage.total_tokens,
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "finish_reason": response.choices[0].finish_reason
            }
            
        except Exception as e:
            print(f"[ERROR] {self.agent_name}: Gradient API error: {e}")
            raise
    
    async def complete_structured(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        response_format: Optional[Dict[str, Any]] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate structured completion (JSON mode) with Langfuse tracing.
        
        Args:
            prompt: User prompt
            system_prompt: System prompt (optional)
            response_format: JSON schema for structured output
            temperature: Sampling temperature
            max_tokens: Maximum tokens
            metadata: Langfuse metadata
            
        Returns:
            Dict with 'content' (parsed JSON), 'model', 'tokens'
        """
        if not self.client:
            raise RuntimeError(f"{self.agent_name}: Gradient client not initialized")
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        trace_metadata = {
            "langfuse_session_id": metadata.get("task_id", "unknown") if metadata else "unknown",
            "langfuse_user_id": self.agent_name,
            "langfuse_tags": ["gradient", "structured", self.agent_name],
            **(metadata or {})
        }
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format=response_format or {"type": "json_object"},
                metadata=trace_metadata
            )
            
            import json
            content = response.choices[0].message.content
            parsed = json.loads(content) if content else {}
            
            return {
                "content": parsed,
                "raw_content": content,
                "model": self.model,
                "tokens": response.usage.total_tokens
            }
            
        except Exception as e:
            print(f"[ERROR] {self.agent_name}: Gradient structured completion error: {e}")
            raise
    
    def is_enabled(self) -> bool:
        """Check if Gradient is properly configured."""
        return bool(self.client)


# Global client instances per agent (lazy-initialized)
_clients: Dict[str, GradientClient] = {}


def get_gradient_client(
    agent_name: str,
    model: Optional[str] = None
) -> GradientClient:
    """
    Get or create Gradient client for agent.
    
    Args:
        agent_name: Name of the calling agent
        model: Optional model override
        
    Returns:
        GradientClient instance
    """
    cache_key = f"{agent_name}:{model or 'default'}"
    
    if cache_key not in _clients:
        _clients[cache_key] = GradientClient(
            agent_name=agent_name,
            model=model
        )
    
    return _clients[cache_key]
