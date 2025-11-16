"""
DigitalOcean Gradient AI Serverless Inference Client

Uses official Gradient SDK for serverless model inference with automatic Langfuse tracing.
https://gradient-sdk.digitalocean.com/getting-started/serverless-inference
"""

import os
import json
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

# Gradient Serverless Inference Configuration
GRADIENT_MODEL_ACCESS_KEY = os.getenv("GRADIENT_MODEL_ACCESS_KEY")
GRADIENT_MODEL = os.getenv("GRADIENT_MODEL", "llama-3.1-8b-instruct")

# Langfuse Configuration
LANGFUSE_ENABLED = all([
    os.getenv("LANGFUSE_SECRET_KEY"),
    os.getenv("LANGFUSE_PUBLIC_KEY"),
    os.getenv("LANGFUSE_HOST")
])

# Validate configuration
GRADIENT_ENABLED = bool(GRADIENT_MODEL_ACCESS_KEY)


class GradientClient:
    """
    Gradient AI Serverless Inference client with automatic Langfuse tracing.
    
    Uses the official Gradient SDK (not OpenAI SDK) for serverless model inference.
    Langfuse tracing is automatically enabled when environment variables are set.
    
    Authentication:
        - GRADIENT_MODEL_ACCESS_KEY: For serverless inference (sk-do-* format)
    
    Langfuse Tracing (automatic when configured):
        - LANGFUSE_SECRET_KEY
        - LANGFUSE_PUBLIC_KEY
        - LANGFUSE_HOST
    """
    
    def __init__(
        self,
        agent_name: str,
        model: Optional[str] = None,
        model_access_key: Optional[str] = None
    ):
        """
        Initialize Gradient serverless inference client.
        
        Args:
            agent_name: Name of the calling agent (for logging/metadata)
            model: Model override (defaults to GRADIENT_MODEL env var)
            model_access_key: API key override (defaults to GRADIENT_MODEL_ACCESS_KEY)
        """
        self.agent_name = agent_name
        self.model = model or GRADIENT_MODEL
        self.model_access_key = model_access_key or GRADIENT_MODEL_ACCESS_KEY
        
        # Initialize Langfuse callback handler if configured
        self.langfuse_handler = None
        if LANGFUSE_ENABLED:
            try:
                from langfuse.callback import CallbackHandler
                self.langfuse_handler = CallbackHandler(
                    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
                    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
                    host=os.getenv("LANGFUSE_HOST")
                )
                logger.info(f"[{agent_name}] Langfuse callback handler initialized")
            except ImportError:
                logger.warning(f"[{agent_name}] Langfuse package not installed, tracing disabled")
            except Exception as e:
                logger.error(f"[{agent_name}] Failed to initialize Langfuse handler: {e}")

        if not self.model_access_key:
            logger.warning(f"[{agent_name}] GRADIENT_MODEL_ACCESS_KEY not set, LLM calls will fail")
            self.client = None
        else:
            try:
                # Import Gradient SDK
                from gradient import Gradient

                # Initialize client for serverless inference
                self.client = Gradient(
                    model_access_key=self.model_access_key
                )

                logger.info(f"[{agent_name}] Gradient SDK initialized for serverless inference")
                logger.info(f"[{agent_name}] Model: {self.model}")
                logger.info(f"[{agent_name}] Model access key: {self.model_access_key[:20]}...")

                if self.langfuse_handler:
                    logger.info(f"[{agent_name}] Langfuse tracing ENABLED (host: {os.getenv('LANGFUSE_HOST')})")
                else:
                    logger.info(f"[{agent_name}] Langfuse tracing DISABLED (env vars not set)")

            except ImportError:
                logger.error(f"[{agent_name}] Gradient SDK not installed. Run: pip install gradient")
                self.client = None
            except Exception as e:
                logger.error(f"[{agent_name}] Failed to initialize Gradient client: {e}")
                self.client = None
    
    async def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate completion using Gradient serverless inference.
        
        Langfuse tracing is automatic if environment variables are configured.
        
        Args:
            prompt: User prompt
            system_prompt: System prompt (optional)
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            metadata: Additional metadata for logging (not passed to API)
            
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
        
        try:
            # Call Gradient serverless inference
            # SDK automatically traces with Langfuse if configured
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            return {
                "content": response.choices[0].message.content,
                "model": self.model,
                "tokens": response.usage.total_tokens if hasattr(response, 'usage') else 0,
                "prompt_tokens": response.usage.prompt_tokens if hasattr(response, 'usage') else 0,
                "completion_tokens": response.usage.completion_tokens if hasattr(response, 'usage') else 0,
                "finish_reason": response.choices[0].finish_reason if response.choices else "unknown"
            }
            
        except Exception as e:
            logger.error(f"[{self.agent_name}] Gradient API error: {e}")
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
        Generate structured JSON completion using Gradient serverless inference.
        
        Args:
            prompt: User prompt
            system_prompt: System prompt (optional)
            response_format: JSON schema for structured output (defaults to json_object)
            temperature: Sampling temperature
            max_tokens: Maximum tokens
            metadata: Metadata for logging (stored but not passed to API)
            
        Returns:
            Dict with 'content' (parsed JSON), 'model', 'tokens'
        """
        if not self.client:
            raise RuntimeError(f"{self.agent_name}: Gradient client not initialized")
        
        # Log metadata for debugging (don't pass to API)
        if metadata:
            logger.debug(f"[{self.agent_name}] Request metadata: {json.dumps(metadata)}")
        
        # Enhance system prompt to request JSON output (Gradient SDK doesn't support response_format)
        json_instruction = "\n\nIMPORTANT: Respond ONLY with valid JSON. Do not include any text before or after the JSON object."
        enhanced_system = (system_prompt or "") + json_instruction
        
        messages = []
        messages.append({"role": "system", "content": enhanced_system})
        messages.append({"role": "user", "content": prompt})
        
        try:
            # Call Gradient inference without response_format parameter
            # Gradient SDK doesn't support OpenAI's response_format parameter
            # Instead, rely on prompt engineering to request JSON output
            logger.debug(f"[{self.agent_name}] Calling Gradient API with model={self.model}")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            content = response.choices[0].message.content
            logger.debug(f"[{self.agent_name}] Received response, parsing JSON...")
            
            parsed = json.loads(content) if content else {}
            
            result = {
                "content": parsed,
                "raw_content": content,
                "model": self.model,
                "tokens": response.usage.total_tokens if hasattr(response, 'usage') else 0
            }
            
            logger.info(f"[{self.agent_name}] Structured completion successful ({result['tokens']} tokens)")
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"[{self.agent_name}] Failed to parse JSON response: {e}")
            logger.error(f"[{self.agent_name}] Raw response content: {content}")
            raise
        except Exception as e:
            logger.error(f"[{self.agent_name}] Gradient structured completion error: {e}", exc_info=True)
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
