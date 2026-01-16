"""Google Gemini LLM provider implementation."""
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


class GeminiProvider(BaseLLMProvider):
    """Google Gemini provider implementation."""

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self._client = None

    def _get_client(self):
        """Lazy initialization of Gemini client."""
        if self._client is None:
            try:
                import google.generativeai as genai
                api_key = self.config.api_key or os.environ.get("GEMINI_API_KEY")
                if not api_key:
                    raise ValueError("GEMINI_API_KEY not configured")
                genai.configure(api_key=api_key)
                self._client = genai.GenerativeModel(self.config.get_model())
            except ImportError:
                raise ImportError(
                    "google-generativeai package not installed. "
                    "Install with: pip install google-generativeai"
                )
        return self._client

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Generate a response using Gemini."""
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
        """Generate a chat response using Gemini."""
        import google.generativeai as genai

        client = self._get_client()

        # Build the prompt with system context
        full_prompt = ""
        if system_prompt:
            full_prompt = f"System Instructions: {system_prompt}\n\n"

        # Add conversation history
        for msg in messages:
            if msg.role == "user":
                full_prompt += f"User: {msg.content}\n"
            elif msg.role == "assistant":
                full_prompt += f"Assistant: {msg.content}\n"

        # Configure generation
        generation_config = genai.types.GenerationConfig(
            temperature=temperature or self.config.temperature,
            max_output_tokens=max_tokens or self.config.max_tokens,
        )

        try:
            response = await client.generate_content_async(
                full_prompt,
                generation_config=generation_config,
            )

            # Extract token counts from usage metadata
            input_tokens = 0
            output_tokens = 0
            if hasattr(response, 'usage_metadata'):
                input_tokens = getattr(response.usage_metadata, 'prompt_token_count', 0)
                output_tokens = getattr(response.usage_metadata, 'candidates_token_count', 0)

            return LLMResponse(
                content=response.text,
                model=self.config.get_model(),
                provider=LLMProvider.GEMINI,
                usage={
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                },
                raw_response=response,
            )
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            raise

    def is_available(self) -> bool:
        """Check if Gemini is properly configured."""
        try:
            api_key = self.config.api_key or os.environ.get("GEMINI_API_KEY")
            return bool(api_key)
        except Exception:
            return False
