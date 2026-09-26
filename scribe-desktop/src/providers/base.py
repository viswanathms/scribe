from __future__ import annotations

from dataclasses import dataclass


class ProviderError(Exception):
    """Connection, auth, or response-parsing failure for an LLM provider."""


@dataclass
class ReviewResult:
    importance_score: int
    reasoning: str
    growth_impact: str
    tags: list[str]
    summary: str = ""


class BaseProvider:
    name: str = "base"

    def __init__(self, api_key: str | None, base_url: str | None, model: str):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model

    def test_connection(self) -> None:
        """Make one small real call. Raise ProviderError with a clear message on failure."""
        raise NotImplementedError

    def list_models(self) -> list[str]:
        """Best-effort list of available model names. Empty list if the provider
        doesn't support discovery (caller falls back to free-text entry)."""
        return []

    def review(self, paper: dict, criteria: dict) -> ReviewResult:
        raise NotImplementedError

    def summarize(self, paper: dict) -> str:
        """One plain sentence: what the paper does. Cheaper/separate from review()
        so already-reviewed papers can get this field backfilled without
        re-scoring them."""
        raise NotImplementedError
