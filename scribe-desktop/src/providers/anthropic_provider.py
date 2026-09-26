from __future__ import annotations

from .base import BaseProvider, ProviderError, ReviewResult
from .prompt import SUMMARIZE_PROMPT, build_system_prompt, build_user_content

REVIEW_TOOL = {
    "name": "record_paper_review",
    "description": "Record the importance review for one arXiv paper.",
    "input_schema": {
        "type": "object",
        "properties": {
            "importance_score": {"type": "integer", "minimum": 1, "maximum": 10},
            "reasoning": {"type": "string", "description": "2-4 sentences justifying the score."},
            "growth_impact": {"type": "string", "description": "One sentence: the concrete growth lever."},
            "tags": {"type": "array", "items": {"type": "string"}, "description": "1-4 short tags."},
            "summary": {"type": "string", "description": "One plain sentence: what the paper does/proposes."},
        },
        "required": ["importance_score", "reasoning", "growth_impact", "tags", "summary"],
    },
}

SUMMARIZE_TOOL = {
    "name": "record_summary",
    "description": "Record a one-sentence summary of the paper.",
    "input_schema": {
        "type": "object",
        "properties": {
            "summary": {"type": "string", "description": "One plain sentence: what the paper does/proposes."},
        },
        "required": ["summary"],
    },
}


class AnthropicProvider(BaseProvider):
    name = "anthropic"

    def _client(self):
        import anthropic

        kwargs = {"api_key": self.api_key}
        if self.base_url:
            kwargs["base_url"] = self.base_url
        return anthropic.Anthropic(**kwargs)

    def test_connection(self) -> None:
        try:
            client = self._client()
            client.messages.create(
                model=self.model,
                max_tokens=8,
                messages=[{"role": "user", "content": "Reply with the word OK."}],
            )
        except Exception as e:  # noqa: BLE001 - surface any SDK/HTTP error uniformly
            raise ProviderError(f"Anthropic connection test failed: {e}") from e

    def review(self, paper: dict, criteria: dict) -> ReviewResult:
        client = self._client()
        try:
            response = client.messages.create(
                model=self.model,
                max_tokens=1024,
                system=build_system_prompt(criteria),
                tools=[REVIEW_TOOL],
                tool_choice={"type": "tool", "name": "record_paper_review"},
                messages=[{"role": "user", "content": build_user_content(paper)}],
            )
        except Exception as e:  # noqa: BLE001
            raise ProviderError(f"Anthropic review call failed: {e}") from e

        for block in response.content:
            if block.type == "tool_use" and block.name == "record_paper_review":
                data = dict(block.input)
                return ReviewResult(
                    importance_score=int(data["importance_score"]),
                    reasoning=data["reasoning"],
                    growth_impact=data["growth_impact"],
                    tags=list(data.get("tags", [])),
                    summary=data.get("summary", ""),
                )
        raise ProviderError("Anthropic did not return a tool_use block.")

    def summarize(self, paper: dict) -> str:
        client = self._client()
        try:
            response = client.messages.create(
                model=self.model,
                max_tokens=256,
                system=SUMMARIZE_PROMPT,
                tools=[SUMMARIZE_TOOL],
                tool_choice={"type": "tool", "name": "record_summary"},
                messages=[{"role": "user", "content": build_user_content(paper)}],
            )
        except Exception as e:  # noqa: BLE001
            raise ProviderError(f"Anthropic summarize call failed: {e}") from e

        for block in response.content:
            if block.type == "tool_use" and block.name == "record_summary":
                return dict(block.input).get("summary", "")
        raise ProviderError("Anthropic did not return a tool_use block.")
