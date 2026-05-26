"""
Route agent chat to ICA workflow or local LLM + GitHub tools (grok_agent).
"""

from __future__ import annotations

import os
from typing import Any, Literal

from grok_agent import get_agent_status as get_local_agent_status
from grok_agent import run_agent as run_local_agent
from grok_agent import run_intelligence_agent as run_local_intelligence_agent
from dependency_graph.impact_context import IMPACT_CHAT_SYSTEM, build_impact_chat_context, format_impact_context_text
from dependency_graph.insight_graph import (
    GRAPH_APPEND_INSTRUCTION,
    build_insight_graph,
    get_quick_actions,
    merge_ai_insight_graph,
    parse_insight_graph_from_message,
)
from ica_agent import (
    format_chat_input,
    get_ica_status,
    is_ica_configured,
    run_ica_agent_chat,
    run_ica_intelligence_chat,
    run_ica_workflow,
)

AgentBackend = Literal["ica", "local", "auto"]

DEFAULT_BACKEND: AgentBackend = os.getenv("AGENT_BACKEND", "auto").lower()  # type: ignore[assignment]


def resolve_backend(requested: str | None = None) -> AgentBackend:
    """Pick backend: request override > env > auto (ICA if configured else local)."""
    raw = (requested or DEFAULT_BACKEND or "auto").lower().strip()
    if raw not in ("ica", "local", "auto"):
        raw = "auto"
    if raw == "auto":
        return "ica" if is_ica_configured() else "local"
    if raw == "ica" and not is_ica_configured():
        raise ValueError(
            "AGENT_BACKEND=ica but ICA is not configured. "
            "Set ICA_API_KEY and ICA_FLOW_ID (or ICA_WORKFLOW_URL) in .env"
        )
    return raw  # type: ignore[return-value]


def get_unified_agent_status() -> dict[str, Any]:
    local = get_local_agent_status()
    ica = get_ica_status()
    default = resolve_backend(None)
    ica_ok = ica["configured"]
    local_ok = local.get("llm_configured", False)
    return {
        **local,
        "llm_configured": ica_ok or local_ok,
        "ica": ica,
        "default_backend": default,
        "ica_configured": ica_ok,
        "backends_available": {
            "ica": ica_ok,
            "local": local_ok,
        },
    }


async def run_agent_chat(
    messages: list[dict[str, Any]],
    owner: str | None = None,
    repo: str | None = None,
    *,
    backend: str | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    chosen = resolve_backend(backend)
    if chosen == "ica":
        out = await run_ica_agent_chat(
            messages, owner=owner, repo=repo, session_id=session_id
        )
        out["backend"] = "ica"
        return out
    out = await run_local_agent(messages, owner=owner, repo=repo)
    out["backend"] = "local"
    return out


async def run_intelligence_chat(
    messages: list[dict[str, Any]],
    insights: dict[str, Any],
    owner: str,
    repo: str,
    *,
    backend: str | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    chosen = resolve_backend(backend)
    if chosen == "ica":
        out = await run_ica_intelligence_chat(
            messages, insights, owner, repo, session_id=session_id
        )
        out["backend"] = "ica"
        return out
    out = await run_local_intelligence_agent(messages, insights, owner, repo)
    out["backend"] = "local"
    return out


async def run_impact_chat(
    messages: list[dict[str, Any]],
    impact: dict[str, Any],
    owner: str,
    repo: str,
    *,
    backend: str | None = None,
    session_id: str | None = None,
    max_context_files: int = 8,
    ref: str | None = None,
    action_id: str | None = None,
) -> dict[str, Any]:
    """Chat about a file using blast-radius context + related source snippets."""
    ctx = await build_impact_chat_context(
        impact, owner, repo, ref=ref, max_files=max_context_files
    )
    context_text = format_impact_context_text(ctx)
    chosen = resolve_backend(backend)

    graph_kind = action_id or "blast_map"
    actions_by_id = {a["id"]: a for a in get_quick_actions(impact)}
    action = actions_by_id.get(action_id or "")
    if action:
        graph_kind = action.get("graph_kind", graph_kind)
    base_graph = build_insight_graph(impact, graph_kind)

    request_ai_graph = bool(action and action.get("request_ai_graph"))
    extra_system = GRAPH_APPEND_INSTRUCTION if request_ai_graph else ""

    if chosen == "ica":
        user_text = format_chat_input(messages, owner=owner, repo=repo, latest_only=True)
        combined = (
            f"{IMPACT_CHAT_SYSTEM}{extra_system}\n\n"
            f"{context_text}\n\n"
            f"---\nUser question:\n{user_text}"
        )
        out = await run_ica_workflow(combined, session_id=session_id)
        out["backend"] = "ica"
        out["context_files"] = len(ctx.get("files", []))
    else:
        api_messages: list[dict[str, Any]] = [
            {
                "role": "system",
                "content": f"{IMPACT_CHAT_SYSTEM}{extra_system}\n\n{context_text}",
            },
        ]
        for m in messages:
            if m.get("role") in ("user", "assistant") and m.get("content"):
                api_messages.append({"role": m["role"], "content": m["content"]})

        from grok_agent import resolve_llm_config, _run_agent_loop

        cfg = resolve_llm_config()
        out = await _run_agent_loop(cfg, api_messages, owner, repo)
        out["backend"] = "local"
        out["context_files"] = len(ctx.get("files", []))

    raw_message = out.get("message", "")
    clean_message, ai_graph = parse_insight_graph_from_message(raw_message)
    out["message"] = clean_message or raw_message
    out["insight_graph"] = merge_ai_insight_graph(base_graph, ai_graph)
    out["action_id"] = action_id
    out["quick_actions"] = get_quick_actions(impact)
    return out
