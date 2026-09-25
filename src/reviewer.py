"""Uses Claude to score each paper's importance to an AI-driven organization's growth."""
from __future__ import annotations

import json

import anthropic

from . import config

SYSTEM_PROMPT = """You are a technical advisor to the leadership of an AI-driven company.
You review new arXiv papers and score how much *implementing or adopting* the paper's
approach would help such an organization grow -- not how academically novel it is.

Score 1-10 using this rubric:
  1-2  Purely theoretical or narrow-domain result with no practical growth lever.
  3-4  Interesting but a stretch to apply; unclear or marginal business impact.
  5-6  Solid, applicable technique (efficiency, quality, or capability gain) a team
       could reasonably build on within a quarter or two.
  7-8  High-leverage: meaningfully cuts cost/latency/risk, or unlocks a new product
       capability, for teams building or deploying AI systems.
  9-10 Step-change: a technique/insight that could materially change how an AI
       organization builds products, scales infra, or competes, if adopted.

Weigh: reproducibility/practicality, cost or capability leverage, applicability
across many AI products (vs. one niche), and time-to-value if a team adopted it.
Ignore topic prestige -- a boring but broadly-applicable efficiency trick can
outscore a flashy narrow benchmark result.
"""

REVIEW_TOOL = {
    "name": "record_paper_review",
    "description": "Record the importance review for one arXiv paper.",
    "input_schema": {
        "type": "object",
        "properties": {
            "importance_score": {
                "type": "integer",
                "minimum": 1,
                "maximum": 10,
                "description": "1-10 per the rubric.",
            },
            "reasoning": {
                "type": "string",
                "description": "2-4 sentences justifying the score.",
            },
            "growth_impact": {
                "type": "string",
                "description": "One sentence: the concrete growth lever (cost, capability, speed, new product, risk reduction, etc).",
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "1-4 short tags, e.g. ['agents', 'inference-cost', 'evals'].",
            },
        },
        "required": ["importance_score", "reasoning", "growth_impact", "tags"],
    },
}


class ClaudeReviewer:
    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.client = anthropic.Anthropic(api_key=api_key or config.ANTHROPIC_API_KEY)
        self.model = model or config.ANTHROPIC_MODEL

    def review(self, paper: dict) -> dict:
        user_content = (
            f"Title: {paper['title']}\n"
            f"Primary subject: {paper.get('primary_subject', '')}\n"
            f"Subjects: {paper.get('subjects', '')}\n"
            f"Abstract: {paper['abstract']}\n"
        )
        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=[REVIEW_TOOL],
            tool_choice={"type": "tool", "name": "record_paper_review"},
            messages=[{"role": "user", "content": user_content}],
        )
        for block in response.content:
            if block.type == "tool_use" and block.name == "record_paper_review":
                result = dict(block.input)
                result["tags_json"] = json.dumps(result.pop("tags", []))
                return result
        raise RuntimeError(f"Claude did not return a tool_use block for {paper.get('arxiv_id')}")
