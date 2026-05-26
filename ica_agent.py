"""
IBM ICA Agentic App Studio workflow client (Langflow API).

Configure via .env:
  ICA_API_KEY          — x-api-key from Workflow → Share → API Access
  ICA_FLOW_ID          — flow UUID (or use full ICA_WORKFLOW_URL)
  ICA_WORKFLOW_URL     — optional full URL (overrides FLOW_ID + host)
  ICA_STREAM           — true/false (default false)
"""

from __future__ import annotations

import json
import os
import uuid
from typing import Any

import httpx

LANGFLOW_BASE = "https://langflow.servicesessentials.ibm.com/api/v1/run"
ICA_FLOW_ID = os.getenv("ICA_FLOW_ID", "953b7d43-0475-4689-845a-3678a6e79aa3")
ICA_API_KEY = os.getenv("ICA_API_KEY", "")
ICA_WORKFLOW_URL = os.getenv("ICA_WORKFLOW_URL", "").strip()
ICA_STREAM = os.getenv("ICA_STREAM", "false").lower() in ("1", "true", "yes", "on")
ICA_TIMEOUT = float(os.getenv("ICA_TIMEOUT", "300"))


def is_ica_configured() -> bool:
    return bool(ICA_API_KEY and (ICA_WORKFLOW_URL or ICA_FLOW_ID))


def _workflow_url() -> str:
    if ICA_WORKFLOW_URL:
        url = ICA_WORKFLOW_URL
        if "stream=" not in url:
            sep = "&" if "?" in url else "?"
            url = f"{url}{sep}stream={'true' if ICA_STREAM else 'false'}"
        return url
    base = f"{LANGFLOW_BASE}/{ICA_FLOW_ID}"
    return f"{base}?stream={'true' if ICA_STREAM else 'false'}"


def _extract_text(payload: Any) -> str | None:
    """Best-effort parse of Langflow / Langchain run responses."""
    if payload is None:
        return None
    if isinstance(payload, str):
        return payload.strip() or None
    if isinstance(payload, list):
        parts = [_extract_text(item) for item in payload]
        joined = "\n\n".join(p for p in parts if p)
        return joined or None
    if not isinstance(payload, dict):
        return str(payload)

    for key in ("message", "text", "output", "result", "answer", "content"):
        if key in payload:
            t = _extract_text(payload[key])
            if t:
                return t

    if "data" in payload:
        t = _extract_text(payload["data"])
        if t:
            return t

    if "results" in payload:
        t = _extract_text(payload["results"])
        if t:
            return t

    if "outputs" in payload:
        t = _extract_text(payload["outputs"])
        if t:
            return t

    # Langflow message object: { "message": { "text": "..." } }
    if "message" in payload and isinstance(payload["message"], dict):
        inner = payload["message"]
        if isinstance(inner.get("text"), str):
            return inner["text"].strip() or None

    return None


def format_chat_input(
    messages: list[dict[str, Any]],
    *,
    owner: str | None = None,
    repo: str | None = None,
    insights: dict[str, Any] | None = None,
    latest_only: bool = False,
) -> str:
    """
    Build input_value for ICA workflow.

    If latest_only=True and session_id carries history server-side, send only
    the last user turn plus context. Otherwise send full transcript.
    """
    parts: list[str] = []

    if owner and repo:
        parts.append(f"Repository: {owner}/{repo} (use this owner/repo for all GitHub MCP tools).")

    if insights:
        blob = json.dumps(insights, indent=2, default=str)
        if len(blob) > 8000:
            blob = blob[:8000] + "\n… (truncated)"
        parts.append(f"Pre-computed repository insights:\n{blob}")

    if latest_only and messages:
        last = messages[-1]
        if last.get("role") == "user" and last.get("content"):
            parts.append(str(last["content"]))
        return "\n\n".join(parts)

    lines: list[str] = []
    for m in messages:
        role = m.get("role")
        content = (m.get("content") or "").strip()
        if role in ("user", "assistant") and content:
            label = "User" if role == "user" else "Assistant"
            lines.append(f"{label}: {content}")

    if lines:
        parts.append("Conversation:\n" + "\n".join(lines))

    return "\n\n".join(parts) if parts else "Hello"


async def run_ica_workflow(
    input_value: str,
    session_id: str | None = None,
) -> dict[str, Any]:
    """
    Call ICA workflow API. Returns AgentChatResponse-compatible dict.
    """
    if not is_ica_configured():
        raise ValueError(
            "ICA not configured. Set ICA_API_KEY and ICA_FLOW_ID (or ICA_WORKFLOW_URL) in .env"
        )

    sid = session_id or str(uuid.uuid4())
    payload = {
        "output_type": "chat",
        "input_type": "chat",
        "input_value": input_value,
        "session_id": sid,
    }
    headers = {
        "x-api-key": ICA_API_KEY,
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=ICA_TIMEOUT) as client:
        response = await client.post(_workflow_url(), json=payload, headers=headers)
        if response.status_code >= 400:
            raise RuntimeError(
                f"ICA workflow HTTP {response.status_code}: {response.text[:2000]}"
            )
        try:
            data = response.json()
        except json.JSONDecodeError:
            data = {"raw": response.text}

    message = _extract_text(data)
    if not message:
        message = json.dumps(data, indent=2)[:12000] if data else "ICA returned an empty response."

    return {
        "message": message,
        "tool_calls": [],
        "model": "ica-workflow",
        "provider": "ica",
        "session_id": sid,
        "raw": data if os.getenv("ICA_DEBUG", "").lower() in ("1", "true", "yes") else None,
    }


async def run_ica_agent_chat(
    messages: list[dict[str, Any]],
    owner: str | None = None,
    repo: str | None = None,
    session_id: str | None = None,
    *,
    latest_only: bool = True,
) -> dict[str, Any]:
    text = format_chat_input(
        messages, owner=owner, repo=repo, latest_only=latest_only
    )
    return await run_ica_workflow(text, session_id=session_id)


async def run_ica_intelligence_chat(
    messages: list[dict[str, Any]],
    insights: dict[str, Any],
    owner: str,
    repo: str,
    session_id: str | None = None,
) -> dict[str, Any]:
    text = format_chat_input(
        messages,
        owner=owner,
        repo=repo,
        insights=insights,
        latest_only=False,
    )
    return await run_ica_workflow(text, session_id=session_id)


def get_ica_status() -> dict[str, Any]:
    return {
        "configured": is_ica_configured(),
        "flow_id": ICA_FLOW_ID if is_ica_configured() else None,
        "workflow_url": _workflow_url() if is_ica_configured() else None,
    }
