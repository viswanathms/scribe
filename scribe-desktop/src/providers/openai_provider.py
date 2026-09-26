from __future__ import annotations

import json

from .base import BaseProvider, ProviderError, ReviewResult
from .prompt import SUMMARIZE_PROMPT, build_system_prompt, build_user_content

REVIEW_FUNCTION = {
    "type": "function",
    "function": {
        "name": "record_paper_review",
        "description": "Record the importance review for one arXiv paper.",
        "parameters": {
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
    },
}

SUMMARIZE_FUNCTION = {
    "type": "function",
    "function": {
        "name": "record_summary",
        "description": "Record a one-sentence summary of the paper.",
        "parameters": {
            "type": "object",
            "properties": {
                "summary": {"type": "string", "description": "One plain sentence: what the paper does/proposes."},
            },
            "required": ["summary"],
        },
    },
}


class OpenAIProvider(BaseProvider):
    name = "openai"

    def _client(self):
        import openai

        kwargs = {"api_key": self.api_key}
        if self.base_url:
            kwargs["base_url"] = self.base_url
        return openai.OpenAI(**kwargs)

    def test_connection(self) -> None:
        try:
            client = self._client()
            client.chat.completions.create(
                model=self.model,
                max_tokens=8,
                messages=[{"role": "user", "content": "Reply with the word OK."}],
            )
        except Exception as e:  # noqa: BLE001
            raise ProviderError(f"OpenAI connection test failed: {e}") from e

    def review(self, paper: dict, criteria: dict) -> ReviewResult:
        client = self._client()
        try:
            response = client.chat.completions.create(
                model=self.model,
                max_tokens=1024,
                tools=[REVIEW_FUNCTION],
                tool_choice={"type": "function", "function": {"name": "record_paper_review"}},
                messages=[
                    {"role": "system", "content": build_system_prompt(criteria)},
                    {"role": "user", "content": build_user_content(paper)},
                ],
            )
        except Exception as e:  # noqa: BLE001
            raise ProviderError(f"OpenAI review call failed: {e}") from e

        message = response.choices[0].message
        if not message.tool_calls:
            raise ProviderError("OpenAI did not return a tool call.")
        try:
            data = json.loads(message.tool_calls[0].function.arguments)
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            raise ProviderError(f"OpenAI returned an unparsable tool call: {e}") from e

        return ReviewResult(
            importance_score=int(data["importance_score"]),
            reasoning=data["reasoning"],
            growth_impact=data["growth_impact"],
            tags=list(data.get("tags", [])),
            summary=data.get("summary", ""),
        )

    def summarize(self, paper: dict) -> str:
        client = self._client()
        try:
            response = client.chat.completions.create(
                model=self.model,
                max_tokens=256,
                tools=[SUMMARIZE_FUNCTION],
                tool_choice={"type": "function", "function": {"name": "record_summary"}},
                messages=[
                    {"role": "system", "content": SUMMARIZE_PROMPT},
                    {"role": "user", "content": build_user_content(paper)},
                ],
            )
        except Exception as e:  # noqa: BLE001
            raise ProviderError(f"OpenAI summarize call failed: {e}") from e

        message = response.choices[0].message
        if not message.tool_calls:
            raise ProviderError("OpenAI did not return a tool call.")
        try:
            data = json.loads(message.tool_calls[0].function.arguments)
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            raise ProviderError(f"OpenAI returned an unparsable tool call: {e}") from e
        return data.get("summary", "")
