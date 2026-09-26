"""Shared rubric + criteria injection, used by every provider so scoring is
consistent regardless of which model actually runs it."""
from __future__ import annotations

RUBRIC = """You are a technical advisor to the leadership of an AI-driven company.
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
outscore a flashy narrow benchmark result."""

SUMMARIZE_PROMPT = """Summarize the arXiv paper below in exactly one plain-English
sentence describing what it actually does or proposes -- not why it matters,
not a score, just what it is. No preamble, no citation of the title verbatim."""

CRITERIA_LABELS = {
    "type": "Preferred paper type",
    "function": "Primary function/lens",
    "area": "Area of focus",
    "other": "Other conditions",
}


def build_system_prompt(criteria: dict | None) -> str:
    prompt = RUBRIC
    lines = []
    for key, label in CRITERIA_LABELS.items():
        value = (criteria or {}).get(key, "").strip()
        if value:
            lines.append(f"- {label}: {value}")
    if lines:
        prompt += (
            "\n\nAdditional criteria from the user -- weigh these heavily:\n"
            + "\n".join(lines)
            + "\nScore papers matching these higher even if narrower in scope; "
            "score strong-but-unrelated papers lower even if academically impressive."
        )
    return prompt


def build_user_content(paper: dict) -> str:
    return (
        f"Title: {paper['title']}\n"
        f"Primary subject: {paper.get('primary_subject', '')}\n"
        f"Subjects: {paper.get('subjects', '')}\n"
        f"Abstract: {paper['abstract']}\n"
    )
