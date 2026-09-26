from __future__ import annotations

import json
import re

import requests

from .base import BaseProvider, ProviderError, ReviewResult
from .prompt import SUMMARIZE_PROMPT, build_system_prompt, build_user_content

REVIEW_SCHEMA = {
    "type": "object",
    "properties": {
        "importance_score": {"type": "integer", "minimum": 1, "maximum": 10},
        "reasoning": {"type": "string"},
        "growth_impact": {"type": "string"},
        "tags": {"type": "array", "items": {"type": "string"}},
        "summary": {"type": "string"},
    },
    "required": ["importance_score", "reasoning", "growth_impact", "tags", "summary"],
}

SUMMARIZE_SCHEMA = {
    "type": "object",
    "properties": {"summary": {"type": "string"}},
    "required": ["summary"],
}

DEFAULT_TIMEOUT = 120


class OllamaProvider(BaseProvider):
    name = "ollama"

    def _base_url(self) -> str:
        return (self.base_url or "http://localhost:11434").rstrip("/")

    def test_connection(self) -> None:
        try:
            resp = requests.get(f"{self._base_url()}/api/tags", timeout=10)
            resp.raise_for_status()
        except Exception as e:  # noqa: BLE001
            raise ProviderError(
                f"Couldn't reach Ollama at {self._base_url()}: {e}. Is `ollama serve` running?"
            ) from e

    def list_models(self) -> list[str]:
        try:
            resp = requests.get(f"{self._base_url()}/api/tags", timeout=10)
            resp.raise_for_status()
            return [m["name"] for m in resp.json().get("models", [])]
        except Exception:  # noqa: BLE001 - discovery is best-effort
            return []

    def _chat_json(self, system: str, user: str, schema: dict) -> dict:
        body = {
            "model": self.model,
            "stream": False,
            "think": False,  # reasoning models otherwise spend tens of seconds on hidden chain-of-thought
            "format": schema,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        try:
            resp = requests.post(f"{self._base_url()}/api/chat", json=body, timeout=DEFAULT_TIMEOUT)
            resp.raise_for_status()
        except Exception as e:  # noqa: BLE001
            raise ProviderError(f"Ollama call failed: {e}") from e

        try:
            content = resp.json()["message"]["content"]
        except KeyError as e:
            raise ProviderError(f"Ollama response had no message content: {e}") from e
        return self._parse_json(content)

    def review(self, paper: dict, criteria: dict) -> ReviewResult:
        data = self._chat_json(build_system_prompt(criteria), build_user_content(paper), REVIEW_SCHEMA)
        try:
            return ReviewResult(
                importance_score=int(data["importance_score"]),
                reasoning=str(data["reasoning"]),
                growth_impact=str(data["growth_impact"]),
                tags=list(data.get("tags", [])),
                summary=str(data.get("summary", "")),
            )
        except (KeyError, ValueError, TypeError) as e:
            raise ProviderError(f"Ollama's JSON was missing/malformed fields: {e}") from e

    def summarize(self, paper: dict) -> str:
        data = self._chat_json(SUMMARIZE_PROMPT, build_user_content(paper), SUMMARIZE_SCHEMA)
        return str(data.get("summary", ""))

    @staticmethod
    def _parse_json(content: str) -> dict:
        """`format`-constrained decoding isn't honored equally well by every local
        model (some reasoning-tuned models drift back to prose). Try a strict parse
        first, then fall back to pulling out the first {...} block."""
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        raise ProviderError(
            f"Ollama returned no parsable JSON (got: {content[:200]!r}...). "
            "Try a model that better follows structured output, e.g. mistral or llama3."
        )
