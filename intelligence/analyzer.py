"""
Derive structured insights from a repository snapshot (deterministic analysis).
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from typing import Any


def _month_key(iso: str | None) -> str | None:
    if not iso:
        return None
    try:
        return iso[:7]
    except Exception:
        return None


def _top_level_module(path: str) -> str:
    parts = path.split("/")
    if len(parts) == 1:
        return "(root)"
    return parts[0]


def analyze_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Produce intelligence insights from a collected snapshot."""
    info = snapshot.get("info", {})
    pulls = snapshot.get("pull_requests", [])
    issues = snapshot.get("issues", [])
    tree = snapshot.get("file_tree", [])
    commits = snapshot.get("commits", [])
    contributors = snapshot.get("contributors", [])
    pr_changes = snapshot.get("pr_file_changes", [])
    deps = snapshot.get("dependencies", [])
    readme = snapshot.get("readme")

    # ── Evolution timeline ─────────────────────────────────────────────────
    pr_by_month: Counter[str] = Counter()
    issue_by_month: Counter[str] = Counter()
    for pr in pulls:
        key = _month_key(pr.get("merged_at") or pr.get("created_at"))
        if key:
            pr_by_month[key] += 1
    for issue in issues:
        key = _month_key(issue.get("created_at"))
        if key:
            issue_by_month[key] += 1

    months = sorted(set(pr_by_month) | set(issue_by_month))
    evolution = [
        {
            "month": m,
            "pull_requests": pr_by_month.get(m, 0),
            "issues": issue_by_month.get(m, 0),
        }
        for m in months[-24:]
    ]

    # Architectural / large PRs (by title heuristics + file count proxy)
    arch_keywords = ("refactor", "migrate", "architecture", "rewrite", "monorepo", "split", "extract", "restructure")
    architectural_prs = [
        {
            "number": p["number"],
            "title": p["title"],
            "merged_at": p.get("merged_at"),
            "url": p.get("url"),
        }
        for p in pulls
        if any(kw in (p.get("title") or "").lower() for kw in arch_keywords)
    ][:15]

    # ── Hot / risky files (churn from sampled PRs) ───────────────────────
    file_churn: Counter[str] = Counter()
    file_additions: Counter[str] = Counter()
    file_deletions: Counter[str] = Counter()
    for ch in pr_changes:
        fn = ch.get("filename", "")
        file_churn[fn] += 1
        file_additions[fn] += ch.get("additions", 0)
        file_deletions[fn] += ch.get("deletions", 0)

    hot_files = [
        {
            "path": path,
            "pr_touch_count": count,
            "additions": file_additions[path],
            "deletions": file_deletions[path],
            "risk": "high" if count >= 5 else "medium" if count >= 2 else "low",
        }
        for path, count in file_churn.most_common(30)
    ]

    # ── Module map (top-level directories) ───────────────────────────────
    module_files: Counter[str] = Counter()
    module_loc_proxy: Counter[str] = Counter()
    extensions: Counter[str] = Counter()
    for f in tree:
        path = f.get("path", "")
        module_files[_top_level_module(path)] += 1
        module_loc_proxy[_top_level_module(path)] += f.get("size", 0)
        ext = f.get("extension", "")
        if ext:
            extensions[ext] += 1

    modules = [
        {
            "name": name,
            "file_count": module_files[name],
            "size_bytes": module_loc_proxy[name],
            "importance": "core" if module_files[name] >= max(module_files.values()) * 0.2 else "supporting",
        }
        for name, _ in module_files.most_common(20)
        if name != "(root)" and module_files[name] > 0
    ]

    # Entry points / config heuristics
    entry_candidates = [
        f["path"] for f in tree
        if any(
            x in f["path"].lower()
            for x in ("main.", "index.", "app.", "__init__", "server.", "manage.py", "routes.")
        )
    ][:20]

    # ── Contributors ─────────────────────────────────────────────────────
    pr_authors: Counter[str] = Counter()
    for pr in pulls:
        if pr.get("author"):
            pr_authors[pr["author"]] += 1

    top_contributors = [
        {
            "login": c["login"],
            "commits": c["contributions"],
            "prs_authored": pr_authors.get(c["login"], 0),
            "profile": c.get("url"),
        }
        for c in sorted(contributors, key=lambda x: x["contributions"], reverse=True)[:15]
    ]

    # ── Onboarding guide (deterministic) ─────────────────────────────────
    lang = info.get("language") or "unknown"
    default_branch = info.get("default_branch", "main")
    top_module = modules[0]["name"] if modules else "repository root"
    onboarding = {
        "start_here": [
            readme["path"] if readme else "README (not found — check default branch)",
            f"Largest module by file count: `{top_module}/`",
            f"Primary language: {lang}",
            f"Default branch: `{default_branch}`",
        ],
        "read_next": entry_candidates[:5],
        "recent_activity": f"{len(commits)} commits sampled; {snapshot['stats']['pr_count']} PRs total",
        "suggested_questions": [
            "How did this project evolve?",
            "Which PR changed the architecture?",
            "What modules are reusable?",
            "Which files are risky or unstable?",
            "How difficult is migration to another stack?",
        ],
    }

    # ── Migration / modernization hints ──────────────────────────────────
    dep_kinds = [d["kind"] for d in deps]
    stack = []
    if "package.json" in dep_kinds:
        stack.append("Node.js / JavaScript")
    if any(k in dep_kinds for k in ("requirements.txt", "pyproject.toml", "Pipfile")):
        stack.append("Python")
    if "go.mod" in dep_kinds:
        stack.append("Go")
    if "Cargo.toml" in dep_kinds:
        stack.append("Rust")
    if "pom.xml" in dep_kinds or "build.gradle" in dep_kinds:
        stack.append("JVM")

    migration = {
        "detected_stack": stack or [lang],
        "dependency_files": deps,
        "complexity_signals": {
            "total_files": len(tree),
            "pr_count": len(pulls),
            "hot_file_count": len([h for h in hot_files if h["risk"] == "high"]),
            "branch_count": snapshot["stats"]["branch_count"],
        },
        "difficulty_estimate": (
            "high" if len(tree) > 1500 or len(pulls) > 500
            else "medium" if len(tree) > 400 or len(pulls) > 100
            else "low"
        ),
        "rewrite_strategy_outline": [
            "Map modules to target architecture (see `modules` insight).",
            "Migrate dependency manifests first; run parallel CI on both stacks.",
            "Replace high-churn files last — they encode the most tacit knowledge.",
            "Extract standalone services starting from modules with clear boundaries.",
        ],
    }

    # ── Technical debt signals ───────────────────────────────────────────
    debt_signals = []
    if len(hot_files) >= 10:
        debt_signals.append(f"{len(hot_files)} files show repeated PR churn (possible instability).")
    if not readme:
        debt_signals.append("No README detected — onboarding risk.")
    if len(architectural_prs) == 0 and len(pulls) > 50:
        debt_signals.append("No obvious architecture PRs in titles — evolution may be implicit in small changes.")
    open_issues = [i for i in issues if i.get("state") == "open"]
    if len(open_issues) > 100:
        debt_signals.append(f"{len(open_issues)} open issues — backlog may hide debt.")

    return {
        "repository": f"{snapshot['owner']}/{snapshot['repo']}",
        "collected_at": snapshot.get("collected_at"),
        "summary": {
            "name": info.get("name"),
            "description": info.get("description"),
            "language": info.get("language"),
            "stars": info.get("stars"),
            "topics": info.get("topics", []),
            "stats": snapshot.get("stats"),
        },
        "evolution": {
            "timeline": evolution,
            "architectural_prs": architectural_prs,
        },
        "architecture": {
            "modules": modules,
            "top_extensions": [{"ext": e, "count": c} for e, c in extensions.most_common(10)],
            "entry_candidates": entry_candidates,
            "standalone_service_candidates": [
                m["name"] for m in modules
                if m["file_count"] >= 10 and m["name"] in ("api", "server", "services", "worker", "frontend", "backend", "pkg", "packages")
            ] or [m["name"] for m in modules[:3]],
        },
        "hot_files": hot_files,
        "contributors": top_contributors,
        "onboarding": onboarding,
        "migration": migration,
        "technical_debt": debt_signals,
        "dependencies": deps,
    }
