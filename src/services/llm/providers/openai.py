"""OpenAI LLM provider implementation."""
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


class OpenAIProvider(BaseLLMProvider):
    """OpenAI provider implementation."""

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self._client = None

    def _get_client(self):
        """Lazy initialization of OpenAI client."""
        if self._client is None:
            try:
                import openai
                api_key = self.config.api_key or os.environ.get("OPENAI_API_KEY")
                if not api_key:
                    raise ValueError("OPENAI_API_KEY not configured")
                self._client = openai.AsyncOpenAI(api_key=api_key)
            except ImportError:
                raise ImportError(
                    "openai package not installed. "
                    "Install with: pip install openai"
                )
        return self._client

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Generate a response using OpenAI."""
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
        """Generate a chat response using OpenAI."""
        client = self._get_client()

        # Build messages list with optional system prompt
        openai_messages = []
        if system_prompt:
            openai_messages.append({"role": "system", "content": system_prompt})

        openai_messages.extend([
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ])

        # Build request parameters
        params = {
            "model": self.config.get_model(),
            "max_tokens": max_tokens or self.config.max_tokens,
            "messages": openai_messages,
        }

        if temperature is not None:
            params["temperature"] = temperature
        elif self.config.temperature is not None:
            params["temperature"] = self.config.temperature

        try:
            response = await client.chat.completions.create(**params)

            return LLMResponse(
                content=response.choices[0].message.content,
                model=response.model,
                provider=LLMProvider.OPENAI,
                usage={
                    "input_tokens": response.usage.prompt_tokens,
                    "output_tokens": response.usage.completion_tokens,
                },
                raw_response=response,
            )
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise

    def is_available(self) -> bool:
        """Check if OpenAI is properly configured."""
        try:
            api_key = self.config.api_key or os.environ.get("OPENAI_API_KEY")
            return bool(api_key)
        except Exception:
            return False
