"""LangChain-backed client wrapper used across agents.

Historically this module talked to the DigitalOcean Gradient SDK directly,
but we now route every LLM call through LangChain so LangSmith tracing works
out-of-the-box whenever ``LANGCHAIN_TRACING_V2=true``.

The public surface area of :class:`GradientClient` stays the same (``complete``
and ``complete_structured``) which keeps all existing agents untouched while
shifting the implementation to LangChain's ``ChatOpenAI`` wrapper that already
handles the DigitalOcean Serverless Inference endpoint.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser
import time

from lib.llm_providers import get_llm
from lib.token_tracker import token_tracker
from lib.config_loader import get_config_loader

logger = logging.getLogger(__name__)


def _coerce_text(content: Any) -> str:
    """Normalize LangChain message content into a plain string."""

    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for chunk in content:
            if isinstance(chunk, str):
                parts.append(chunk)
            elif isinstance(chunk, dict):
                parts.append(chunk.get("text", ""))
        return "".join(parts)
    return str(content)


def _strip_code_fences(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped

    lines = stripped.split("\n")
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


class GradientClient:
    """Compatibility wrapper that now delegates to LangChain's ChatOpenAI."""

    def __init__(self, agent_name: str, model: Optional[str] = None):
        self.agent_name = agent_name
        self.model = model
        self._default_llm = get_llm(agent_name, model=model)
        self._enabled = self._default_llm is not None
        if self._enabled:
            logger.info(
                "[%s] LangChain client initialized for model=%s",
                agent_name,
                self._default_llm.model_name,
            )
        else:
            logger.warning(
                "[%s] LangChain client unavailable (missing provider credentials)",
                agent_name,
            )

    def _usage_from_response(self, response) -> Dict[str, int]:
        metadata = getattr(response, "response_metadata", {}) or {}
        usage = metadata.get("token_usage") or metadata.get("usage") or {}
        return {
            "tokens": usage.get("total_tokens", 0),
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
        }

    def _get_llm(self, temperature: float, max_tokens: int):
        llm = get_llm(
            self.agent_name,
            model=self.model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        if not llm:
            raise RuntimeError(
                f"{self.agent_name}: LangChain LLM not configured (check GRADIENT_MODEL_ACCESS_KEY / provider keys)"
            )
        return llm

    async def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if metadata:
            logger.debug("[%s] Metadata for completion: %s", self.agent_name, metadata)

        llm = self._get_llm(temperature=temperature, max_tokens=max_tokens)
        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))

        start_time = time.time()
        response = await llm.ainvoke(messages)
        latency = time.time() - start_time

        content = _coerce_text(response.content)
        usage = self._usage_from_response(response)

        # Track token usage and cost
        self._track_tokens(
            prompt_tokens=usage["prompt_tokens"],
            completion_tokens=usage["completion_tokens"],
            latency_seconds=latency,
            model=llm.model_name,
        )

        return {
            "content": content,
            "model": llm.model_name,
            "tokens": usage["tokens"],
            "prompt_tokens": usage["prompt_tokens"],
            "completion_tokens": usage["completion_tokens"],
            "finish_reason": response.response_metadata.get("finish_reason", "stop"),
        }

    async def complete_structured(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        response_format: Optional[Dict[str, Any]] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if metadata:
            logger.debug("[%s] Structured metadata: %s", self.agent_name, metadata)

        llm = self._get_llm(temperature=temperature, max_tokens=max_tokens)
        parser = JsonOutputParser()
        format_instructions = parser.get_format_instructions()
        combined_system = (system_prompt or "").strip()
        if combined_system:
            combined_system += "\n\n"
        combined_system += format_instructions

        messages = [
            SystemMessage(content=combined_system),
            HumanMessage(content=prompt),
        ]

        start_time = time.time()
        response = await llm.ainvoke(messages)
        latency = time.time() - start_time

        raw_content = _strip_code_fences(_coerce_text(response.content))

        try:
            parsed = parser.parse(raw_content)
        except Exception:
            logger.warning(
                "[%s] JsonOutputParser failed, attempting manual json.loads",
                self.agent_name,
            )
            try:
                parsed = json.loads(raw_content)
            except json.JSONDecodeError as exc:
                logger.error(
                    "[%s] Failed to parse structured response: %s",
                    self.agent_name,
                    exc,
                    exc_info=True,
                )
                raise

        usage = self._usage_from_response(response)

        # Track token usage and cost
        self._track_tokens(
            prompt_tokens=usage["prompt_tokens"],
            completion_tokens=usage["completion_tokens"],
            latency_seconds=latency,
            model=llm.model_name,
        )

        result = {
            "content": parsed,
            "raw_content": raw_content,
            "model": llm.model_name,
            "tokens": usage["tokens"],
        }

        logger.info(
            "[%s] Structured completion successful (%s tokens)",
            self.agent_name,
            usage["tokens"],
        )
        return result

    def _track_tokens(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        latency_seconds: float,
        model: str,
    ):
        """Calculate cost and track token usage."""
        try:
            # Get cost per 1M tokens from YAML config
            config_loader = get_config_loader()
            agent_config = config_loader.get_agent_config(self.agent_name)
            cost_per_1m = agent_config.cost_per_1m_tokens

            # Calculate cost for this call
            total_tokens = prompt_tokens + completion_tokens
            cost = (total_tokens / 1_000_000) * cost_per_1m

            # Track via TokenTracker
            token_tracker.track(
                agent_name=self.agent_name,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                cost=cost,
                latency_seconds=latency_seconds,
                model=model,
            )
        except Exception as e:
            # Don't fail requests if tracking fails
            logger.warning(f"[{self.agent_name}] Token tracking failed: {e}")

    def is_enabled(self) -> bool:
        return self._enabled

    async def ainvoke(
        self,
        messages: list,
        config: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Async invoke method for LangChain Runnable interface compatibility.

        This allows GradientClient to be used as a drop-in replacement for
        LangChain LLMs when tools are unavailable.

        Args:
            messages: List of LangChain message objects
            config: Optional runnable configuration (ignored)

        Returns:
            LangChain AIMessage with response content
        """
        from langchain_core.messages import AIMessage

        # Extract system and human messages
        system_prompt = None
        prompt = ""
        for msg in messages:
            if hasattr(msg, "type"):
                if msg.type == "system":
                    system_prompt = msg.content
                elif msg.type == "human":
                    prompt = msg.content
            elif hasattr(msg, "content"):
                # Fallback for message-like objects
                prompt = msg.content

        result = await self.complete(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.7,
            max_tokens=2000,
        )

        return AIMessage(content=result["content"])

    def invoke(
        self,
        messages: list,
        config: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Sync invoke method for LangChain Runnable interface compatibility.

        Wraps the async ainvoke method for synchronous contexts.

        Args:
            messages: List of LangChain message objects
            config: Optional runnable configuration (ignored)

        Returns:
            LangChain AIMessage with response content
        """
        import asyncio
        return asyncio.get_event_loop().run_until_complete(
            self.ainvoke(messages, config)
        )

    def get_llm_with_tools(
        self, tools: list, temperature: float = 0.7, max_tokens: int = 2000
    ):
        """Get LLM instance with tools bound for function calling.

        Args:
            tools: List of LangChain BaseTool instances
            temperature: Sampling temperature
            max_tokens: Maximum completion tokens

        Returns:
            LangChain LLM with tools bound via bind_tools()
        """
        llm = self._get_llm(temperature=temperature, max_tokens=max_tokens)
        if not tools:
            return llm
        return llm.bind_tools(tools)


_clients: Dict[str, GradientClient] = {}


def get_gradient_client(agent_name: str, model: Optional[str] = None) -> GradientClient:
    cache_key = f"{agent_name}:{model or 'default'}"
    if cache_key not in _clients:
        _clients[cache_key] = GradientClient(agent_name=agent_name, model=model)
    return _clients[cache_key]
