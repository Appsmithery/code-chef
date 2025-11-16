"""
LangChain-compatible wrapper for Gradient AI client.

Provides LLM interface for LangGraph nodes to use with existing gradient_client.
"""

import logging
from typing import Any, Dict, List, Optional
from langchain_core.language_models.llms import LLM
from langchain_core.outputs import Generation, LLMResult
from langchain_core.callbacks.manager import CallbackManagerForLLMRun

from agents._shared.gradient_client import get_gradient_client

# Initialize Langfuse callback handler if configured
_langfuse_handler = None
try:
    import os
    if all([
        os.getenv("LANGFUSE_SECRET_KEY"),
        os.getenv("LANGFUSE_PUBLIC_KEY"),
        os.getenv("LANGFUSE_HOST")
    ]):
        from langfuse.callback import CallbackHandler
        _langfuse_handler = CallbackHandler(
            secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
            public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
            host=os.getenv("LANGFUSE_HOST")
        )
        logger = logging.getLogger(__name__)
        logger.info("Langfuse callback handler initialized for LangChain wrapper")
except ImportError:
    pass  # Langfuse not installed
except Exception as e:
    logger = logging.getLogger(__name__)
    logger.warning(f"Failed to initialize Langfuse handler: {e}")

logger = logging.getLogger(__name__)


class GradientLLM(LLM):
    """
    LangChain-compatible LLM wrapper for Gradient AI.
    
    Integrates existing gradient_client with LangGraph's LLM interface,
    enabling use in LangChain tools, prompts, and agents.
    
    Usage:
        llm = GradientLLM(agent_name="orchestrator", model="llama-3.1-70b-instruct")
        result = await llm.ainvoke("Explain LangGraph workflows")
    """
    
    agent_name: str
    model: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 2000
    
    @property
    def _llm_type(self) -> str:
        """Return identifier for this LLM."""
        return "gradient"
    
    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any
    ) -> str:
        """
        Synchronous call (not implemented - use ainvoke instead).
        """
        raise NotImplementedError("Use ainvoke for async calls")
    
    async def _acall(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any
    ) -> str:
        """
        Async call to Gradient AI via gradient_client.

        Args:
            prompt: Input prompt
            stop: Stop sequences (currently ignored)
            run_manager: LangChain callback manager
            **kwargs: Additional parameters (temperature, max_tokens, system_prompt)

        Returns:
            Generated text
        """
        client = get_gradient_client(
            agent_name=self.agent_name,
            model=self.model
        )

        if not client.is_enabled():
            raise RuntimeError(f"{self.agent_name}: Gradient client not enabled (missing API key)")

        # Extract parameters
        temperature = kwargs.get("temperature", self.temperature)
        max_tokens = kwargs.get("max_tokens", self.max_tokens)
        system_prompt = kwargs.get("system_prompt")

        # Invoke gradient_client
        try:
            result = await client.complete(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                metadata={
                    "agent_name": self.agent_name,
                    "model": self.model or client.model
                }
            )

            # Report token usage via callback manager
            if run_manager:
                await run_manager.on_llm_new_token(
                    result["content"],
                    verbose=True
                )

            return result["content"]

        except Exception as e:
            logger.error(f"[{self.agent_name}] Gradient LLM error: {e}")
            raise
    
    @property
    def _identifying_params(self) -> Dict[str, Any]:
        """Return identifying parameters for caching."""
        return {
            "agent_name": self.agent_name,
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }


def get_gradient_llm(
    agent_name: str,
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 2000
) -> GradientLLM:
    """
    Factory function for creating GradientLLM instances.
    
    Args:
        agent_name: Name of the calling agent
        model: Optional model override
        temperature: Sampling temperature (default 0.7)
        max_tokens: Max tokens to generate (default 2000)
        
    Returns:
        GradientLLM instance ready for LangGraph use
    """
    return GradientLLM(
        agent_name=agent_name,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens
    )
