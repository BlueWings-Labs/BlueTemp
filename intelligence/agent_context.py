"""Build LLM context from repository insights for deep Q&A."""

from __future__ import annotations

import json
from typing import Any


INTELLIGENCE_SYSTEM = """You are BlueWings, an AI Repository Intelligence analyst — a Software Archaeologist and Architecture Analyst.

You help developers understand how a project was built, evolved, and how to onboard, modernize, or migrate it.
This is NOT a simple summarizer. Use the structured repository insights below plus GitHub tools when you need fresh data.

Your expertise:
- Project evolution and architectural change over time
- Module importance and where core business logic likely lives
- High-churn / risky files and technical debt signals
- Onboarding paths for new developers
- Migration difficulty and rewrite strategies
- Reusable modules and potential service boundaries
- Contributor expertise on critical areas

Answer with clear markdown: headings, bullets, and actionable recommendations.
When citing PRs or files, use specific numbers/paths from the data.
If insights are incomplete, call GitHub tools to verify before claiming facts."""


def build_intelligence_messages(
    insights: dict[str, Any],
    user_messages: list[dict[str, Any]],
    owner: str,
    repo: str,
) -> list[dict[str, Any]]:
    """Prepend system context with compressed insights for the agent."""
    # Keep context under ~12k chars for smaller models
    blob = json.dumps(insights, indent=2, default=str)
    if len(blob) > 12000:
        blob = blob[:12000] + "\n… (truncated)"

    system = (
        f"{INTELLIGENCE_SYSTEM}\n\n"
        f"## Repository: {owner}/{repo}\n\n"
        f"## Pre-computed insights (use as primary evidence)\n```json\n{blob}\n```"
    )

    out: list[dict[str, Any]] = [{"role": "system", "content": system}]
    for m in user_messages:
        if m.get("role") in ("user", "assistant") and m.get("content"):
            out.append({"role": m["role"], "content": m["content"]})
    return out
