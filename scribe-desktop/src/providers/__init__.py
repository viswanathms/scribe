from __future__ import annotations

from .base import BaseProvider, ProviderError, ReviewResult


def get_provider(settings: dict) -> BaseProvider:
    provider = settings.get("provider")
    model = settings.get("model")
    api_key = settings.get("api_key")
    base_url = settings.get("base_url")

    if not provider or not model:
        raise ProviderError("No provider/model configured yet. Finish setup first.")

    if provider == "anthropic":
        from .anthropic_provider import AnthropicProvider

        return AnthropicProvider(api_key=api_key, base_url=base_url, model=model)
    if provider == "openai":
        from .openai_provider import OpenAIProvider

        return OpenAIProvider(api_key=api_key, base_url=base_url, model=model)
    if provider == "ollama":
        from .ollama_provider import OllamaProvider

        return OllamaProvider(api_key=api_key, base_url=base_url, model=model)

    raise ProviderError(f"Unknown provider: {provider!r}")


__all__ = ["get_provider", "BaseProvider", "ProviderError", "ReviewResult"]
