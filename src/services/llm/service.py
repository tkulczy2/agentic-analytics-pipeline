"""Main LLM Service with provider abstraction and caching."""
import hashlib
import json
import logging
from typing import List, Optional

from src.services.llm.base import (
    BaseLLMProvider,
    LLMConfig,
    LLMMessage,
    LLMProvider,
    LLMResponse,
)
from src.services.llm.providers import ClaudeProvider, OpenAIProvider, GeminiProvider, OllamaProvider

logger = logging.getLogger(__name__)


class LLMService:
    """
    Vendor-agnostic LLM service with provider abstraction.

    Supports Claude (default), OpenAI, and Ollama (local models).
    Includes optional response caching via Redis.
    """

    PROVIDER_CLASSES = {
        LLMProvider.CLAUDE: ClaudeProvider,
        LLMProvider.OPENAI: OpenAIProvider,
        LLMProvider.GEMINI: GeminiProvider,
        LLMProvider.OLLAMA: OllamaProvider,
    }

    def __init__(
        self,
        config: Optional[LLMConfig] = None,
        cache_client=None,
        cache_ttl: int = 3600,
    ):
        """
        Initialize the LLM service.

        Args:
            config: LLM configuration. Defaults to Claude.
            cache_client: Optional Redis client for caching responses
            cache_ttl: Cache TTL in seconds (default 1 hour)
        """
        self.config = config or LLMConfig()
        self.cache_client = cache_client
        self.cache_ttl = cache_ttl
        self._provider: Optional[BaseLLMProvider] = None

    @classmethod
    def create(
        cls,
        provider: str = "claude",
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs,
    ) -> "LLMService":
        """
        Factory method to create an LLM service with specified provider.

        Args:
            provider: Provider name ("claude", "openai", "ollama")
            model: Model name (uses provider default if not specified)
            api_key: API key for the provider
            base_url: Base URL (for Ollama or custom endpoints)
            temperature: Temperature for generation
            **kwargs: Additional arguments passed to LLMService

        Returns:
            Configured LLMService instance
        """
        provider_enum = LLMProvider(provider.lower())
        config = LLMConfig(
            provider=provider_enum,
            model=model,
            api_key=api_key,
            base_url=base_url,
            temperature=temperature,
        )
        return cls(config=config, **kwargs)

    def _get_provider(self) -> BaseLLMProvider:
        """Get or create the LLM provider instance."""
        if self._provider is None:
            provider_class = self.PROVIDER_CLASSES.get(self.config.provider)
            if not provider_class:
                raise ValueError(f"Unknown provider: {self.config.provider}")
            self._provider = provider_class(self.config)
        return self._provider

    def _cache_key(self, prompt: str, system_prompt: Optional[str], **kwargs) -> str:
        """Generate a cache key for a request."""
        key_data = {
            "prompt": prompt,
            "system": system_prompt,
            "model": self.config.get_model(),
            "provider": self.config.provider.value,
            **kwargs,
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return f"llm:cache:{hashlib.sha256(key_str.encode()).hexdigest()[:16]}"

    async def _get_cached(self, cache_key: str) -> Optional[LLMResponse]:
        """Get a cached response if available."""
        if not self.cache_client:
            return None
        try:
            cached = await self.cache_client.get(cache_key)
            if cached:
                data = json.loads(cached)
                return LLMResponse(
                    content=data["content"],
                    model=data["model"],
                    provider=LLMProvider(data["provider"]),
                    usage=data.get("usage", {}),
                )
        except Exception as e:
            logger.warning(f"Cache read error: {e}")
        return None

    async def _set_cached(self, cache_key: str, response: LLMResponse):
        """Cache a response."""
        if not self.cache_client:
            return
        try:
            data = {
                "content": response.content,
                "model": response.model,
                "provider": response.provider.value,
                "usage": response.usage,
            }
            await self.cache_client.set(cache_key, json.dumps(data), ex=self.cache_ttl)
        except Exception as e:
            logger.warning(f"Cache write error: {e}")

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        use_cache: bool = True,
    ) -> LLMResponse:
        """
        Generate a response from the LLM.

        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt for context
            temperature: Override default temperature
            max_tokens: Override default max tokens
            use_cache: Whether to use caching (default True)

        Returns:
            LLMResponse with the generated content
        """
        # Check cache
        if use_cache:
            cache_key = self._cache_key(prompt, system_prompt, temp=temperature)
            cached = await self._get_cached(cache_key)
            if cached:
                logger.debug(f"Cache hit for prompt: {prompt[:50]}...")
                return cached

        # Generate response
        provider = self._get_provider()
        response = await provider.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        # Cache response
        if use_cache:
            await self._set_cached(cache_key, response)

        return response

    async def generate_chat(
        self,
        messages: List[LLMMessage],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """
        Generate a response from a chat conversation.

        Args:
            messages: List of conversation messages
            system_prompt: Optional system prompt
            temperature: Override default temperature
            max_tokens: Override default max tokens

        Returns:
            LLMResponse with the generated content
        """
        provider = self._get_provider()
        return await provider.generate_chat(
            messages=messages,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    def is_available(self) -> bool:
        """Check if the configured provider is available."""
        try:
            provider = self._get_provider()
            return provider.is_available()
        except Exception:
            return False

    @property
    def provider_name(self) -> str:
        """Get the name of the configured provider."""
        return self.config.provider.value

    @property
    def model_name(self) -> str:
        """Get the name of the configured model."""
        return self.config.get_model()
