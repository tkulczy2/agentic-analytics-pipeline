"""Base classes for LLM provider abstraction."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    CLAUDE = "claude"
    OPENAI = "openai"
    GEMINI = "gemini"
    OLLAMA = "ollama"  # For local models


@dataclass
class LLMConfig:
    """Configuration for LLM service."""
    provider: LLMProvider = LLMProvider.CLAUDE
    model: Optional[str] = None  # Provider-specific model name
    api_key: Optional[str] = None
    base_url: Optional[str] = None  # For Ollama or custom endpoints
    temperature: float = 0.7
    max_tokens: int = 2048
    timeout: int = 60

    # Default models per provider
    DEFAULT_MODELS = {
        LLMProvider.CLAUDE: "claude-sonnet-4-20250514",
        LLMProvider.OPENAI: "gpt-4o",
        LLMProvider.GEMINI: "gemini-2.0-flash",
        LLMProvider.OLLAMA: "llama3.1",
    }

    def get_model(self) -> str:
        """Get the model name, using default if not specified."""
        return self.model or self.DEFAULT_MODELS.get(self.provider, "")


@dataclass
class LLMMessage:
    """A message in a conversation."""
    role: str  # "user", "assistant", "system"
    content: str


@dataclass
class LLMResponse:
    """Response from an LLM provider."""
    content: str
    model: str
    provider: LLMProvider
    usage: Dict[str, int] = field(default_factory=dict)
    raw_response: Optional[Any] = None

    @property
    def input_tokens(self) -> int:
        return self.usage.get("input_tokens", 0)

    @property
    def output_tokens(self) -> int:
        return self.usage.get("output_tokens", 0)


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""

    def __init__(self, config: LLMConfig):
        self.config = config

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """
        Generate a response from the LLM.

        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt for context
            temperature: Override default temperature
            max_tokens: Override default max tokens

        Returns:
            LLMResponse with the generated content
        """
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is properly configured and available."""
        pass
