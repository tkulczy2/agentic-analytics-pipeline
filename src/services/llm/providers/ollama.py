"""Ollama LLM provider implementation for local models."""
import logging
import os
from typing import List, Optional

import httpx

from src.services.llm.base import (
    BaseLLMProvider,
    LLMConfig,
    LLMMessage,
    LLMProvider,
    LLMResponse,
)

logger = logging.getLogger(__name__)


class OllamaProvider(BaseLLMProvider):
    """Ollama provider for local LLM inference."""

    DEFAULT_BASE_URL = "http://localhost:11434"

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.base_url = config.base_url or os.environ.get(
            "OLLAMA_BASE_URL", self.DEFAULT_BASE_URL
        )

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Generate a response using Ollama."""
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
        """Generate a chat response using Ollama."""
        # Build messages list with optional system prompt
        ollama_messages = []
        if system_prompt:
            ollama_messages.append({"role": "system", "content": system_prompt})

        ollama_messages.extend([
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ])

        # Build request payload
        payload = {
            "model": self.config.get_model(),
            "messages": ollama_messages,
            "stream": False,
            "options": {},
        }

        if temperature is not None:
            payload["options"]["temperature"] = temperature
        elif self.config.temperature is not None:
            payload["options"]["temperature"] = self.config.temperature

        if max_tokens or self.config.max_tokens:
            payload["options"]["num_predict"] = max_tokens or self.config.max_tokens

        try:
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()

                return LLMResponse(
                    content=data["message"]["content"],
                    model=data.get("model", self.config.get_model()),
                    provider=LLMProvider.OLLAMA,
                    usage={
                        "input_tokens": data.get("prompt_eval_count", 0),
                        "output_tokens": data.get("eval_count", 0),
                    },
                    raw_response=data,
                )
        except httpx.ConnectError:
            raise ConnectionError(
                f"Could not connect to Ollama at {self.base_url}. "
                "Make sure Ollama is running."
            )
        except Exception as e:
            logger.error(f"Ollama API error: {e}")
            raise

    def is_available(self) -> bool:
        """Check if Ollama is running and accessible."""
        import httpx
        try:
            with httpx.Client(timeout=5) as client:
                response = client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except Exception:
            return False
