"""Claude (Anthropic) LLM provider implementation."""
import logging
import os
from typing import List, Optional

from src.services.llm.base import (
    BaseLLMProvider,
    LLMConfig,
    LLMMessage,
    LLMProvider,
    LLMResponse,
)

logger = logging.getLogger(__name__)


class ClaudeProvider(BaseLLMProvider):
    """Anthropic Claude provider implementation."""

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self._client = None

    def _get_client(self):
        """Lazy initialization of Anthropic client."""
        if self._client is None:
            try:
                import anthropic
                api_key = self.config.api_key or os.environ.get("ANTHROPIC_API_KEY")
                if not api_key:
                    raise ValueError("ANTHROPIC_API_KEY not configured")
                self._client = anthropic.AsyncAnthropic(api_key=api_key)
            except ImportError:
                raise ImportError(
                    "anthropic package not installed. "
                    "Install with: pip install anthropic"
                )
        return self._client

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Generate a response using Claude."""
        messages = [LLMMessage(role="user", content=prompt)]
        return await self.generate_chat(
            messages=messages,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    async def generate_chat(
        self,
        messages: List[LLMMessage],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Generate a chat response using Claude."""
        client = self._get_client()

        # Convert messages to Anthropic format
        anthropic_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]

        # Build request parameters
        params = {
            "model": self.config.get_model(),
            "max_tokens": max_tokens or self.config.max_tokens,
            "messages": anthropic_messages,
        }

        if system_prompt:
            params["system"] = system_prompt

        if temperature is not None:
            params["temperature"] = temperature
        elif self.config.temperature is not None:
            params["temperature"] = self.config.temperature

        try:
            response = await client.messages.create(**params)

            return LLMResponse(
                content=response.content[0].text,
                model=response.model,
                provider=LLMProvider.CLAUDE,
                usage={
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                },
                raw_response=response,
            )
        except Exception as e:
            logger.error(f"Claude API error: {e}")
            raise

    def is_available(self) -> bool:
        """Check if Claude is properly configured."""
        try:
            api_key = self.config.api_key or os.environ.get("ANTHROPIC_API_KEY")
            return bool(api_key)
        except Exception:
            return False
