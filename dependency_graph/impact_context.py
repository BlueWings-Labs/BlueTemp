"""
Build chat context from blast-radius (change impact) + related file contents.
"""

from __future__ import annotations

import json
from typing import Any

import github_services as gh

IMPACT_CHAT_SYSTEM = """You are BlueWings Impact Analyst — a senior engineer helping review a specific file change.

You receive:
- Blast radius summary (who imports this file, what it imports, risk level)
- Source code snippets from the target file and related files in the dependency neighborhood
- Related pull requests that touched the target file

Answer questions about:
- What this file does, key functions, classes, exports, and important variables
- What would break or need updates if the user changes this file
- How related files connect (imports / dependents)
- What the related PRs suggest about past changes

Rules:
- Ground answers in the provided file contents and impact data only.
- If code was not fetched for a path, say so — do not invent file contents.
- Reference paths and line-level detail when visible in snippets.
- Be concise but specific (bullets, short paragraphs).
"""

MAX_CONTEXT_FILES = 8
MAX_CHARS_PER_FILE = 6000


def _collect_paths(impact: dict[str, Any], max_files: int) -> list[str]:
    target = impact.get("target", {})
    if not target.get("resolved"):
        return []

    paths: list[str] = []
    seen: set[str] = set()

    def add(p: str) -> None:
        if not p or p.startswith("pkg:") or p in seen:
            return
        seen.add(p)
        paths.append(p)

    add(target["path"])
    for item in impact.get("dependents", {}).get("direct", [])[: max_files // 2]:
        add(item.get("path", ""))
    for item in impact.get("dependencies", {}).get("direct", [])[: max_files // 2]:
        add(item.get("path", ""))
    for item in impact.get("dependents", {}).get("transitive", [])[:2]:
        add(item.get("path", ""))

    return paths[:max_files]


async def build_impact_chat_context(
    impact: dict[str, Any],
    owner: str,
    repo: str,
    *,
    ref: str | None = None,
    max_files: int = MAX_CONTEXT_FILES,
    max_chars_per_file: int = MAX_CHARS_PER_FILE,
) -> dict[str, Any]:
    """Fetch snippets + structured impact metadata for LLM context."""
    paths = _collect_paths(impact, max_files)
    contents: dict[str, str | None] = {}
    fetch_stats: dict[str, Any] = {}

    if paths:
        contents, fetch_stats = await gh.get_file_contents_batch(owner, repo, paths, ref=ref)

    files: list[dict[str, Any]] = []
    for path in paths:
        raw = contents.get(path)
        if raw is None:
            files.append({"path": path, "content": None, "truncated": False, "missing": True})
            continue
        truncated = len(raw) > max_chars_per_file
        files.append(
            {
                "path": path,
                "content": raw[:max_chars_per_file] if truncated else raw,
                "truncated": truncated,
                "missing": False,
            }
        )

    return {
        "repository": impact.get("repository", {"owner": owner, "repo": repo}),
        "target": impact.get("target"),
        "summary": impact.get("summary"),
        "dependents": impact.get("dependents"),
        "dependencies": impact.get("dependencies"),
        "related_prs": (impact.get("related_prs") or [])[:8],
        "highlight": impact.get("highlight"),
        "files": files,
        "fetch_stats": fetch_stats,
    }


def format_impact_context_text(ctx: dict[str, Any]) -> str:
    """Serialize context bundle for LLM / ICA workflow input."""
    parts: list[str] = []

    target = ctx.get("target") or {}
    summary = ctx.get("summary") or {}
    parts.append(f"## Target file: {target.get('path', '?')}")
    parts.append(f"Risk: {summary.get('risk_level', 'unknown')} — {summary.get('message', '')}")

    deps = ctx.get("dependents", {})
    parts.append(
        f"Direct importers ({len(deps.get('direct', []))}): "
        + ", ".join(d["path"] for d in deps.get("direct", [])[:15])
        or "(none)"
    )
    fwd = ctx.get("dependencies", {})
    parts.append(
        f"Direct imports ({len(fwd.get('direct', []))}): "
        + ", ".join(
            d["path"] if isinstance(d, dict) else str(d)
            for d in fwd.get("direct", [])[:15]
        )
        or "(none)"
    )

    prs = ctx.get("related_prs") or []
    if prs:
        parts.append("## Related PRs")
        for pr in prs[:6]:
            parts.append(
                f"- #{pr.get('number')} {pr.get('title')} ({pr.get('state')}) "
                f"{pr.get('url', '')}"
            )

    parts.append("## File contents (for Q&A)")
    for f in ctx.get("files", []):
        path = f.get("path", "")
        if f.get("missing"):
            parts.append(f"\n### {path}\n(not fetched — binary, missing, or API limit)\n")
            continue
        content = f.get("content") or ""
        suffix = " [truncated]" if f.get("truncated") else ""
        parts.append(f"\n### {path}{suffix}\n```\n{content}\n```\n")

    meta = {k: v for k, v in ctx.items() if k not in ("files",)}
    blob = json.dumps(meta, indent=2, default=str)
    if len(blob) > 12000:
        blob = blob[:12000] + "\n…"
    parts.append(f"## Impact metadata (JSON)\n```json\n{blob}\n```")

    return "\n".join(parts)
