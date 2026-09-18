"""Provider-agnostic LLM service abstraction.

This module defines the abstract interface for all Large Language Model integrations.
The application never couples directly to vendor-specific SDKs.

CRITICAL ARCHITECTURAL CONSTRAINTS:
1. No fake or mock LLM fallback is implemented inside the application runtime.
2. If no provider is configured, the service fails explicitly with a clear configuration error.
3. Tests must mock this service at the test boundary via pytest.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional, Type, TypeVar
from pydantic import BaseModel

from app.config import settings

T = TypeVar("T", bound=BaseModel)


class BaseLLMService(ABC):
    """Abstract interface defining required LLM capabilities."""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        """Generates a text completion for a given prompt."""
        pass

    @abstractmethod
    async def structured_output(
        self,
        prompt: str,
        schema: Type[T],
        system_prompt: Optional[str] = None,
        **kwargs: Any,
    ) -> T:
        """Generates structured output conforming strictly to a Pydantic schema."""
        pass


class OpenAILLMService(BaseLLMService):
    """OpenAI implementation of the LLM service."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None) -> None:
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.model = model or settings.LLM_MODEL or "gpt-4o"
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY must be set when using the 'openai' provider.")

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        raise NotImplementedError("OpenAI provider integration will be implemented in Phase 2.")

    async def structured_output(
        self,
        prompt: str,
        schema: Type[T],
        system_prompt: Optional[str] = None,
        **kwargs: Any,
    ) -> T:
        raise NotImplementedError("OpenAI structured output will be implemented in Phase 2.")


class AnthropicLLMService(BaseLLMService):
    """Anthropic implementation of the LLM service."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None) -> None:
        self.api_key = api_key or settings.ANTHROPIC_API_KEY
        self.model = model or settings.LLM_MODEL or "claude-3-5-sonnet-20241022"
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY must be set when using the 'anthropic' provider.")

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        raise NotImplementedError("Anthropic provider integration will be implemented in Phase 2.")

    async def structured_output(
        self,
        prompt: str,
        schema: Type[T],
        system_prompt: Optional[str] = None,
        **kwargs: Any,
    ) -> T:
        raise NotImplementedError("Anthropic structured output will be implemented in Phase 2.")


class OllamaLLMService(BaseLLMService):
    """Local Ollama provider implementation."""

    def __init__(self, base_url: Optional[str] = None, model: Optional[str] = None) -> None:
        self.base_url = base_url or settings.OLLAMA_BASE_URL
        self.model = model or settings.LLM_MODEL or "llama3.1"

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        raise NotImplementedError("Ollama provider integration will be implemented in Phase 2.")

    async def structured_output(
        self,
        prompt: str,
        schema: Type[T],
        system_prompt: Optional[str] = None,
        **kwargs: Any,
    ) -> T:
        raise NotImplementedError("Ollama structured output will be implemented in Phase 2.")


def get_llm_service(provider: Optional[str] = None) -> BaseLLMService:
    """Factory that resolves and instantiates the configured LLM provider.
    
    Fails explicitly if no provider is configured or an unknown provider is specified.
    Never falls back to fabricated or fake AI responses.
    """
    resolved_provider = (provider or settings.LLM_PROVIDER or "").strip().lower()

    if not resolved_provider:
        raise ValueError(
            "No LLM provider configured. Set LLM_PROVIDER ('openai', 'anthropic', or 'ollama') "
            "and corresponding credentials in environment variables."
        )

    if resolved_provider == "openai":
        return OpenAILLMService()
    elif resolved_provider == "anthropic":
        return AnthropicLLMService()
    elif resolved_provider == "ollama":
        return OllamaLLMService()
    else:
        raise ValueError(
            f"Unsupported LLM provider: '{resolved_provider}'. "
            "Supported providers are: 'openai', 'anthropic', 'ollama'."
        )
