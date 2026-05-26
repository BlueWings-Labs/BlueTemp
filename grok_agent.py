"""
LLM agent with GitHub tools — supports free providers (Gemini, Groq, Ollama) and paid (OpenAI, xAI).
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Literal

import httpx
from dotenv import load_dotenv

import github_services as gh
from github_services import GitHubError

load_dotenv()

# Paid / optional
XAI_API_KEY = os.getenv("XAI_API_KEY") or os.getenv("GROK_API_KEY")
XAI_BASE_URL = os.getenv("XAI_BASE_URL", "https://api.x.ai/v1")
GROK_MODEL = os.getenv("GROK_MODEL", "grok-3-mini")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Free tiers (recommended)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
GEMINI_BASE_URL = os.getenv(
    "GEMINI_BASE_URL",
    "https://generativelanguage.googleapis.com/v1beta/openai/",
)
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434/v1")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "auto").lower()
MAX_TOOL_ROUNDS = int(os.getenv("AGENT_MAX_TOOL_ROUNDS", "8"))

Provider = Literal["gemini", "groq", "ollama", "openai", "xai"]

FREE_SETUP_HINT = (
    "No LLM configured. Free options:\n"
    "  1) Gemini (recommended): get a free key at https://aistudio.google.com/apikey\n"
    "     → set GEMINI_API_KEY=... and LLM_PROVIDER=gemini\n"
    "  2) Groq: free key at https://console.groq.com/keys\n"
    "     → set GROQ_API_KEY=... and LLM_PROVIDER=groq\n"
    "  3) Ollama (100% local): install https://ollama.com → run `ollama pull llama3.1`\n"
    "     → set LLM_PROVIDER=ollama (no API key needed)"
)


@dataclass
class LlmConfig:
    provider: Provider
    api_key: str
    base_url: str
    model: str
    auth_required: bool = True


def _ollama_reachable() -> bool:
    try:
        base = OLLAMA_BASE_URL.rstrip("/").removesuffix("/v1")
        with httpx.Client(timeout=2.0) as client:
            return client.get(f"{base}/api/tags").status_code == 200
    except Exception:
        return False


def resolve_llm_config() -> LlmConfig:
    """Resolve LLM from LLM_PROVIDER or auto (prefers free providers)."""
    p = LLM_PROVIDER

    if p == "gemini":
        if not GEMINI_API_KEY:
            raise ValueError("LLM_PROVIDER=gemini but GEMINI_API_KEY is not set")
        return LlmConfig("gemini", GEMINI_API_KEY, GEMINI_BASE_URL, GEMINI_MODEL)

    if p == "groq":
        if not GROQ_API_KEY:
            raise ValueError("LLM_PROVIDER=groq but GROQ_API_KEY is not set")
        return LlmConfig("groq", GROQ_API_KEY, GROQ_BASE_URL, GROQ_MODEL)

    if p == "ollama":
        if not _ollama_reachable():
            raise ValueError(
                "Ollama is not running. Install from https://ollama.com, then run: "
                "ollama pull llama3.1 && ollama serve"
            )
        return LlmConfig("ollama", "ollama", OLLAMA_BASE_URL, OLLAMA_MODEL, auth_required=False)

    if p == "openai":
        if not OPENAI_API_KEY:
            raise ValueError("LLM_PROVIDER=openai but OPENAI_API_KEY is not set")
        return LlmConfig("openai", OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL)

    if p == "xai":
        if not XAI_API_KEY:
            raise ValueError("LLM_PROVIDER=xai but XAI_API_KEY is not set")
        return LlmConfig("xai", XAI_API_KEY, XAI_BASE_URL, GROK_MODEL)

    # auto — prefer free providers first
    if GEMINI_API_KEY:
        return LlmConfig("gemini", GEMINI_API_KEY, GEMINI_BASE_URL, GEMINI_MODEL)
    if GROQ_API_KEY:
        return LlmConfig("groq", GROQ_API_KEY, GROQ_BASE_URL, GROQ_MODEL)
    if _ollama_reachable():
        return LlmConfig("ollama", "ollama", OLLAMA_BASE_URL, OLLAMA_MODEL, auth_required=False)
    if OPENAI_API_KEY:
        return LlmConfig("openai", OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL)
    if XAI_API_KEY:
        return LlmConfig("xai", XAI_API_KEY, XAI_BASE_URL, GROK_MODEL)

    raise ValueError(FREE_SETUP_HINT)


def get_agent_status() -> dict[str, Any]:
    try:
        cfg = resolve_llm_config()
        configured = True
    except ValueError:
        cfg = None
        configured = False
    return {
        "llm_configured": configured,
        "provider": cfg.provider if cfg else None,
        "model": cfg.model if cfg else None,
        "gemini_configured": bool(GEMINI_API_KEY),
        "groq_configured": bool(GROQ_API_KEY),
        "ollama_reachable": _ollama_reachable(),
        "grok_configured": bool(XAI_API_KEY),
        "openai_configured": bool(OPENAI_API_KEY),
        "github_token_set": bool(os.getenv("GITHUB_TOKEN")),
        "free_options": ["gemini", "groq", "ollama"],
    }


def _extract_api_error_message(data: Any, fallback: str) -> str:
    """Normalize provider error payloads (dict, list, nested)."""
    if isinstance(data, str):
        return data
    if isinstance(data, list):
        parts: list[str] = []
        for item in data:
            parts.append(_extract_api_error_message(item, ""))
        return "; ".join(p for p in parts if p) or fallback
    if isinstance(data, dict):
        if "message" in data:
            return str(data["message"])
        if "error" in data:
            return _extract_api_error_message(data["error"], fallback)
        return json.dumps(data)
    return str(data) if data is not None else fallback


def _friendly_api_error(status: int, body: str, provider: str) -> str:
    failed_gen = ""
    try:
        data = json.loads(body)
        if isinstance(data, dict):
            fg = data.get("failed_generation")
            err_obj = data.get("error")
            if isinstance(err_obj, dict):
                fg = fg or err_obj.get("failed_generation")
            if fg:
                fg_str = str(fg).strip()
                if len(fg_str) > 800:
                    fg_str = fg_str[:800] + "…"
                failed_gen = f" [failed_generation: {fg_str}]"
            err = _extract_api_error_message(data.get("error", data), body)
        else:
            err = _extract_api_error_message(data, body)
    except json.JSONDecodeError:
        err = body

    err_lower = str(err).lower()
    if status == 403 and ("credit" in err_lower or "license" in err_lower or "permission" in err_lower):
        if provider == "xai":
            return (
                "xAI has no credits/licenses. Use a free provider instead: "
                "set GEMINI_API_KEY (https://aistudio.google.com/apikey) or GROQ_API_KEY "
                "(https://console.groq.com/keys), or LLM_PROVIDER=ollama for local Ollama."
            )
        return f"LLM API permission denied (403): {err}"

    if status == 401:
        return f"Invalid API key for {provider}. Check your .env file."

    if status == 429:
        return f"{provider} rate limit hit. Wait a moment or switch LLM_PROVIDER (e.g. groq or ollama)."

    if status == 400 and provider == "groq" and "failed to call a function" in err_lower:
        return (
            f"{provider} API error 400: {err}{failed_gen}\n"
            "Tip: use GROQ_MODEL=llama-3.3-70b-versatile (best tool-calling on Groq). "
            "Smaller models often emit invalid tool JSON."
        )

    return f"{provider} API error {status}: {err}{failed_gen}"


def _param_schema(properties: dict[str, Any], required: list[str]) -> dict[str, Any]:
    """JSON Schema for tools — Groq is strict: no bare enums on optionals, use number not integer."""
    return {
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": False,
    }


GITHUB_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_repo_info",
            "description": "Get repository metadata: stars, forks, language, topics.",
            "parameters": _param_schema(
                {"owner": {"type": "string"}, "repo": {"type": "string"}},
                ["owner", "repo"],
            ),
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_pull_requests",
            "description": "List pull requests. state: open, closed, or all (default all).",
            "parameters": _param_schema(
                {
                    "owner": {"type": "string"},
                    "repo": {"type": "string"},
                    "state": {
                        "type": "string",
                        "description": "Optional. One of: open, closed, all.",
                    },
                },
                ["owner", "repo"],
            ),
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_pull_request_detail",
            "description": "Full detail for one pull request. pr_number must be a whole number.",
            "parameters": _param_schema(
                {
                    "owner": {"type": "string"},
                    "repo": {"type": "string"},
                    "pr_number": {"type": "number", "description": "Pull request number (integer)."},
                },
                ["owner", "repo", "pr_number"],
            ),
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_pr_reviews",
            "description": "List reviews on a pull request.",
            "parameters": _param_schema(
                {
                    "owner": {"type": "string"},
                    "repo": {"type": "string"},
                    "pr_number": {"type": "number", "description": "Pull request number (integer)."},
                },
                ["owner", "repo", "pr_number"],
            ),
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_issues",
            "description": "List issues (not PRs). state: open, closed, or all.",
            "parameters": _param_schema(
                {
                    "owner": {"type": "string"},
                    "repo": {"type": "string"},
                    "state": {
                        "type": "string",
                        "description": "Optional. One of: open, closed, all.",
                    },
                    "labels": {
                        "type": "string",
                        "description": "Optional comma-separated label names.",
                    },
                },
                ["owner", "repo"],
            ),
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_issue_detail",
            "description": "Full detail for one issue.",
            "parameters": _param_schema(
                {
                    "owner": {"type": "string"},
                    "repo": {"type": "string"},
                    "issue_number": {"type": "number", "description": "Issue number (integer)."},
                },
                ["owner", "repo", "issue_number"],
            ),
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_issue_comments",
            "description": "List comments on an issue.",
            "parameters": _param_schema(
                {
                    "owner": {"type": "string"},
                    "repo": {"type": "string"},
                    "issue_number": {"type": "number", "description": "Issue number (integer)."},
                },
                ["owner", "repo", "issue_number"],
            ),
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_repo_contributors",
            "description": "List contributors with commit counts.",
            "parameters": _param_schema(
                {"owner": {"type": "string"}, "repo": {"type": "string"}},
                ["owner", "repo"],
            ),
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_issues_and_prs",
            "description": "Search issues and PRs. kind: issue, pr, or both.",
            "parameters": _param_schema(
                {
                    "owner": {"type": "string"},
                    "repo": {"type": "string"},
                    "query": {"type": "string"},
                    "kind": {
                        "type": "string",
                        "description": "Optional. One of: issue, pr, both.",
                    },
                },
                ["owner", "repo", "query"],
            ),
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_repository_dependency_graph",
            "description": (
                "Build code import dependency graph (JSON: nodes, edges, file_tree). "
                "Use for architecture maps and file relationships."
            ),
            "parameters": _param_schema(
                {
                    "owner": {"type": "string"},
                    "repo": {"type": "string"},
                    "max_files": {
                        "type": "number",
                        "description": "Optional. Max source files to analyze (50-800, default 400).",
                    },
                    "include_packages": {
                        "type": "boolean",
                        "description": "Optional. Include external npm/pip package nodes.",
                    },
                },
                ["owner", "repo"],
            ),
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_change_impact",
            "description": (
                "Blast radius for editing a file: reverse dependents (who imports it), "
                "forward dependencies, related PRs, risk level, highlight subgraph."
            ),
            "parameters": _param_schema(
                {
                    "owner": {"type": "string"},
                    "repo": {"type": "string"},
                    "file_path": {
                        "type": "string",
                        "description": "Repository-relative path, e.g. src/app/page.tsx",
                    },
                    "max_files": {
                        "type": "number",
                        "description": "Optional. Max source files in graph (50-800).",
                    },
                    "max_depth_dependents": {
                        "type": "number",
                        "description": "Optional. How many import hops upstream (1-8, default 4).",
                    },
                },
                ["owner", "repo", "file_path"],
            ),
        },
    },
]

TOOL_ALLOWED_KEYS: dict[str, frozenset[str]] = {
    "get_repo_info": frozenset({"owner", "repo"}),
    "list_pull_requests": frozenset({"owner", "repo", "state", "sort", "direction"}),
    "get_pull_request_detail": frozenset({"owner", "repo", "pr_number"}),
    "list_pr_reviews": frozenset({"owner", "repo", "pr_number"}),
    "list_issues": frozenset({"owner", "repo", "state", "sort", "direction", "labels"}),
    "get_issue_detail": frozenset({"owner", "repo", "issue_number"}),
    "list_issue_comments": frozenset({"owner", "repo", "issue_number"}),
    "list_repo_contributors": frozenset({"owner", "repo"}),
    "search_issues_and_prs": frozenset({"owner", "repo", "query", "kind"}),
    "get_repository_dependency_graph": frozenset({
        "owner", "repo", "ref", "max_files", "include_packages",
    }),
    "get_change_impact": frozenset({
        "owner",
        "repo",
        "file_path",
        "ref",
        "max_files",
        "include_packages",
        "max_depth_dependents",
        "max_depth_dependencies",
        "pr_sample_size",
    }),
}

_INT_FIELDS = frozenset({"pr_number", "issue_number"})

TOOL_HANDLERS = {
    "get_repo_info": gh.get_repo_info,
    "list_pull_requests": gh.list_pull_requests,
    "get_pull_request_detail": gh.get_pull_request_detail,
    "list_pr_reviews": gh.list_pr_reviews,
    "list_pr_comments": gh.list_pr_comments,
    "list_pr_commits": gh.list_pr_commits,
    "list_issues": gh.list_issues,
    "get_issue_detail": gh.get_issue_detail,
    "list_issue_comments": gh.list_issue_comments,
    "list_issue_events": gh.list_issue_events,
    "list_repo_contributors": gh.list_repo_contributors,
    "list_repo_labels": gh.list_repo_labels,
    "search_issues_and_prs": gh.search_issues_and_prs,
}

async def _get_repository_dependency_graph(**kwargs: Any) -> dict:
    from dependency_graph.builder import build_dependency_graph

    owner = kwargs["owner"]
    repo = kwargs["repo"]
    return await build_dependency_graph(
        owner,
        repo,
        ref=kwargs.get("ref") or None,
        max_files=int(kwargs.get("max_files") or 400),
        include_packages=kwargs.get("include_packages", True),
    )


TOOL_HANDLERS["get_repository_dependency_graph"] = _get_repository_dependency_graph


async def _get_change_impact(**kwargs: Any) -> dict:
    from dependency_graph.impact import build_change_impact

    return await build_change_impact(
        kwargs["owner"],
        kwargs["repo"],
        kwargs["file_path"],
        ref=kwargs.get("ref") or None,
        max_files=int(kwargs.get("max_files") or 400),
        include_packages=kwargs.get("include_packages", True),
        max_depth_dependents=int(kwargs.get("max_depth_dependents") or 4),
        max_depth_dependencies=int(kwargs.get("max_depth_dependencies") or 3),
        pr_sample_size=int(kwargs.get("pr_sample_size") or 40),
    )


TOOL_HANDLERS["get_change_impact"] = _get_change_impact


def normalize_tool_arguments(name: str, raw: Any) -> dict[str, Any]:
    """Strip unknown keys (avoids TypeError), coerce numeric IDs, drop empty strings."""
    if not isinstance(raw, dict):
        raw = {}
    allowed = TOOL_ALLOWED_KEYS.get(name)
    if allowed is None:
        args = dict(raw)
    else:
        args = {k: raw[k] for k in allowed if k in raw}
    for k in list(args.keys()):
        if args[k] == "":
            del args[k]
    for key in _INT_FIELDS:
        if key in args and args[key] is not None and not isinstance(args[key], int):
            try:
                args[key] = int(float(str(args[key]).replace(",", "").strip()))
            except (TypeError, ValueError):
                pass
    return args


def _sanitize_assistant_message(message: dict[str, Any]) -> dict[str, Any]:
    """Groq/OpenAI-compatible: assistant turns with tool_calls must not use content: null."""
    out = dict(message)
    if out.get("content") is None:
        out["content"] = ""
    return out


def _system_prompt(owner: str | None, repo: str | None, provider: str) -> str:
    ctx = f" Default repository context: {owner}/{repo}." if owner and repo else ""
    groq_note = ""
    if provider == "groq":
        groq_note = (
            " Tool rules: reply with valid JSON only inside tool arguments. "
            "Use JSON numbers for pr_number and issue_number (e.g. 42), not strings."
        )
    return (
        f"You are a GitHub repository analyst assistant (powered by {provider})."
        " Use the provided tools to fetch real data from GitHub — never invent PR/issue numbers or stats."
        " Summarize clearly with markdown. Be concise unless the user asks for detail."
        f"{ctx}"
        " When owner/repo are omitted in a tool call, use the default repository if set."
        f"{groq_note}"
    )


def _request_headers(cfg: LlmConfig) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if cfg.auth_required:
        headers["Authorization"] = f"Bearer {cfg.api_key}"
    return headers


async def execute_tool(name: str, arguments: dict[str, Any]) -> str:
    fn = TOOL_HANDLERS.get(name)
    if not fn:
        return json.dumps({"error": f"Unknown tool: {name}"})
    try:
        result = await fn(**arguments)
        return json.dumps(result, default=str)
    except GitHubError as e:
        return json.dumps({"error": e.detail, "status": e.status_code})
    except TypeError as e:
        return json.dumps({"error": str(e)})
    except Exception as e:
        return json.dumps({"error": str(e)})


async def _run_agent_loop(
    cfg: LlmConfig,
    api_messages: list[dict[str, Any]],
    owner: str | None,
    repo: str | None,
) -> dict[str, Any]:
    tool_calls_log: list[dict[str, Any]] = []
    base = cfg.base_url.rstrip("/") + "/"

    async with httpx.AsyncClient(timeout=120) as client:
        for _ in range(MAX_TOOL_ROUNDS):
            payload: dict[str, Any] = {
                "model": cfg.model,
                "messages": api_messages,
                "tools": GITHUB_TOOLS,
                "tool_choice": "auto",
            }
            if cfg.provider == "groq":
                payload["parallel_tool_calls"] = False
                payload["temperature"] = 0

            resp = await client.post(
                f"{base}chat/completions",
                headers=_request_headers(cfg),
                json=payload,
            )
            if resp.status_code != 200:
                raise RuntimeError(_friendly_api_error(resp.status_code, resp.text, cfg.provider))

            data = resp.json()
            choice = data["choices"][0]
            message = choice["message"]
            finish = choice.get("finish_reason")

            tool_calls = message.get("tool_calls") or []
            if not tool_calls:
                return {
                    "message": message.get("content") or "",
                    "tool_calls": tool_calls_log,
                    "model": data.get("model", cfg.model),
                    "provider": cfg.provider,
                }

            api_messages.append(_sanitize_assistant_message(message))

            for tc in tool_calls:
                fn = tc.get("function", {})
                name = fn.get("name", "")
                raw_args = fn.get("arguments") or "{}"
                try:
                    parsed = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                except json.JSONDecodeError:
                    parsed = {}
                args = normalize_tool_arguments(name, parsed)

                if owner and repo:
                    args.setdefault("owner", owner)
                    args.setdefault("repo", repo)

                result = await execute_tool(name, args)
                tool_calls_log.append({"name": name, "arguments": args})

                api_messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": result,
                    }
                )

            if finish == "stop":
                break

    return {
        "message": "I hit the tool-call limit. Please ask a more specific question.",
        "tool_calls": tool_calls_log,
        "model": cfg.model,
        "provider": cfg.provider,
    }


async def run_completion(
    messages: list[dict[str, Any]],
    *,
    temperature: float = 0.2,
) -> str:
    """Single-turn or multi-turn chat completion without tools (Context Studio docs, etc.)."""
    cfg = resolve_llm_config()
    base = cfg.base_url.rstrip("/") + "/"
    payload: dict[str, Any] = {
        "model": cfg.model,
        "messages": messages,
        "temperature": temperature,
    }
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            f"{base}chat/completions",
            headers=_request_headers(cfg),
            json=payload,
        )
        if resp.status_code != 200:
            raise RuntimeError(_friendly_api_error(resp.status_code, resp.text, cfg.provider))
        data = resp.json()
        return (data["choices"][0]["message"].get("content") or "").strip()


async def run_agent(
    messages: list[dict[str, Any]],
    owner: str | None = None,
    repo: str | None = None,
) -> dict[str, Any]:
    cfg = resolve_llm_config()
    api_messages: list[dict[str, Any]] = [
        {"role": "system", "content": _system_prompt(owner, repo, cfg.provider)}
    ]
    for m in messages:
        role = m.get("role")
        if role in ("user", "assistant") and m.get("content"):
            api_messages.append({"role": role, "content": m["content"]})
    return await _run_agent_loop(cfg, api_messages, owner, repo)


async def run_intelligence_agent(
    messages: list[dict[str, Any]],
    insights: dict[str, Any],
    owner: str,
    repo: str,
) -> dict[str, Any]:
    from intelligence.agent_context import build_intelligence_messages

    cfg = resolve_llm_config()
    api_messages = build_intelligence_messages(insights, messages, owner, repo)
    return await _run_agent_loop(cfg, api_messages, owner, repo)
