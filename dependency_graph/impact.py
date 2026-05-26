"""
Blast radius / change impact — reverse dependents, forward deps, PR history.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import PurePosixPath
from typing import Any

import github_services as gh
from github_services import GitHubClient
from dependency_graph.builder import build_dependency_graph, _cluster_key, _language_for
from dependency_graph.resolver import build_path_index, resolve_specifier

IMPACT_VERSION = "1.0"


def _risk_level(direct_dep: int, transitive_dep: int, pr_count: int) -> str:
    if direct_dep >= 8 or transitive_dep >= 20 or pr_count >= 6:
        return "high"
    if direct_dep >= 3 or transitive_dep >= 8 or pr_count >= 2:
        return "medium"
    return "low"


def _reverse_reachable(
    edges: list[dict[str, Any]],
    start: str,
    max_depth: int,
) -> tuple[set[str], list[dict[str, Any]], dict[int, list[str]]]:
    by_target: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for e in edges:
        t = e["target"]
        if t.startswith("pkg:"):
            continue
        by_target[t].append(e)

    visited: set[str] = {start}
    by_depth: dict[int, list[str]] = {0: [start]}
    collected: list[dict[str, Any]] = []
    frontier = [start]
    depth = 0

    while frontier and depth < max_depth:
        depth += 1
        next_frontier: list[str] = []
        depth_paths: list[str] = []
        for node in frontier:
            for e in by_target.get(node, []):
                collected.append(e)
                src = e["source"]
                if src not in visited:
                    visited.add(src)
                    next_frontier.append(src)
                    depth_paths.append(src)
        if depth_paths:
            by_depth[depth] = depth_paths
        frontier = next_frontier

    return visited, collected, by_depth


def _forward_reachable(
    edges: list[dict[str, Any]],
    start: str,
    max_depth: int,
) -> tuple[set[str], list[dict[str, Any]]]:
    by_source: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for e in edges:
        by_source[e["source"]].append(e)

    visited: set[str] = {start}
    collected: list[dict[str, Any]] = []
    frontier = [start]
    depth = 0

    while frontier and depth < max_depth:
        next_frontier: list[str] = []
        for node in frontier:
            for e in by_source.get(node, []):
                collected.append(e)
                t = e["target"]
                if t.startswith("pkg:"):
                    continue
                if t not in visited:
                    visited.add(t)
                    next_frontier.append(t)
        frontier = next_frontier
        depth += 1

    return visited, collected


def _file_summary(path: str, in_degree: int, out_degree: int) -> dict[str, Any]:
    return {
        "path":       path,
        "label":      PurePosixPath(path).name,
        "language":   _language_for(path),
        "cluster":    _cluster_key(path),
        "in_degree":  in_degree,
        "out_degree": out_degree,
    }


async def _related_pull_requests(
    owner: str,
    repo: str,
    file_path: str,
    *,
    sample_size: int = 40,
    client: GitHubClient | None = None,
) -> list[dict[str, Any]]:
    pulls = await gh.list_pull_requests(owner, repo, state="all", client=client)
    candidates = sorted(
        pulls,
        key=lambda p: p.get("merged_at") or p.get("updated_at") or "",
        reverse=True,
    )[:sample_size]

    sem = asyncio.Semaphore(6)
    matches: list[dict[str, Any]] = []

    async def _check(pr: dict) -> None:
        async with sem:
            try:
                files = await gh.list_pr_files(owner, repo, pr["number"], client=client)
            except Exception:
                return
            for f in files:
                fn = f.get("filename") or ""
                if fn == file_path or fn.endswith(f"/{file_path}") or file_path.endswith(fn):
                    matches.append({
                        "number":      pr["number"],
                        "title":       pr["title"],
                        "state":       pr["state"],
                        "author":      pr.get("author"),
                        "merged_at":   pr.get("merged_at"),
                        "updated_at":  pr.get("updated_at"),
                        "url":         pr.get("url"),
                        "file_status": f.get("status"),
                        "additions":   f.get("additions", 0),
                        "deletions":   f.get("deletions", 0),
                    })
                    return

    if candidates:
        await asyncio.gather(*[_check(pr) for pr in candidates])

    matches.sort(
        key=lambda m: m.get("merged_at") or m.get("updated_at") or "",
        reverse=True,
    )
    return matches[:15]


async def build_change_impact(
    owner: str,
    repo: str,
    file_path: str,
    *,
    ref: str | None = None,
    max_files: int = 400,
    include_packages: bool = True,
    max_depth_dependents: int = 4,
    max_depth_dependencies: int = 3,
    pr_sample_size: int = 40,
    client: GitHubClient | None = None,
) -> dict[str, Any]:
    """
    Analyze blast radius for changing a single file.

    Pass `client=GitHubClient(host='ibm')` to target GitHub Enterprise.
    """
    focus = file_path.strip().lstrip("/")
    graph = await build_dependency_graph(
        owner, repo,
        ref=ref,
        max_files=max_files,
        include_packages=include_packages,
        client=client,
    )

    file_nodes = {n["id"]: n for n in graph["nodes"] if n["type"] == "file"}
    all_edges = [
        {"source": e["source"], "target": e["target"], "kind": e["kind"], "id": e["id"]}
        for e in graph["edges"]
    ]

    candidate_paths = list(file_nodes.keys())
    file_set = frozenset(candidate_paths)
    path_index = build_path_index(candidate_paths)

    resolved = focus if focus in file_nodes else None
    if not resolved:
        hit, _ = resolve_specifier(
            focus, focus,
            file_set=file_set, path_index=path_index, path_aliases={},
        )
        if hit and hit in file_nodes:
            resolved = hit
        else:
            for p in candidate_paths:
                if p == focus or p.endswith(f"/{focus}") or focus.endswith(p):
                    resolved = p
                    break

    if not resolved:
        return {
            "version": IMPACT_VERSION,
            "target": {"path": focus, "resolved": False},
            "repository": graph["repository"],
            "meta": {
                "analyzed_at": datetime.now(timezone.utc).isoformat(),
                "error": "File not found in analyzed graph (increase max_files or check path).",
            },
            "summary": {
                "risk_level": "unknown",
                "message": f"Could not resolve '{focus}' in the dependency graph.",
            },
            "dependents":    {"direct": [], "transitive": [], "by_depth": {}},
            "dependencies":  {"direct": [], "transitive": []},
            "related_prs":   [],
            "highlight":     {"node_ids": [], "edge_ids": [], "paths": []},
            "subgraph":      {"nodes": [], "edges": []},
        }

    in_deg  = {n["id"]: n.get("in_degree", 0)  for n in graph["nodes"]}
    out_deg = {n["id"]: n.get("out_degree", 0) for n in graph["nodes"]}

    dep_visited, dep_edges, dep_by_depth = _reverse_reachable(
        all_edges, resolved, max(1, min(max_depth_dependents, 8))
    )
    fwd_visited, fwd_edges = _forward_reachable(
        all_edges, resolved, max(1, min(max_depth_dependencies, 8))
    )

    direct_dependents = [
        e["source"]
        for e in all_edges
        if e["target"] == resolved and not e["source"].startswith("pkg:")
    ]
    direct_deps = [e["target"] for e in all_edges if e["source"] == resolved]

    transitive_dependents = sorted(dep_visited - {resolved} - set(direct_dependents))
    transitive_fwd        = sorted(fwd_visited - {resolved} - set(direct_deps))

    related_prs = await _related_pull_requests(
        owner, repo, resolved, sample_size=pr_sample_size, client=client
    )

    risk = _risk_level(len(direct_dependents), len(transitive_dependents), len(related_prs))

    impact_paths = dep_visited | fwd_visited
    impact_edge_ids: list[str] = []
    subgraph_edges: list[dict[str, Any]] = []
    seen_e: set[tuple[str, str]] = set()

    for e in dep_edges + fwd_edges:
        key = (e["source"], e["target"])
        if key in seen_e:
            continue
        seen_e.add(key)
        subgraph_edges.append(e)
        if e.get("id"):
            impact_edge_ids.append(e["id"])

    node_by_id    = {n["id"]: n for n in graph["nodes"]}
    subgraph_nodes = [node_by_id[nid] for nid in impact_paths if nid in node_by_id]

    messages = {
        "high":   "Wide blast radius — many files depend on this path. Coordinate changes and run full regression.",
        "medium": "Moderate impact — review direct dependents and recent PRs before merging.",
        "low":    "Limited impact — few importers detected in the analyzed graph sample.",
    }

    return {
        "version": IMPACT_VERSION,
        "target": {
            "path":           resolved,
            "requested_path": focus,
            "resolved":       True,
            "cluster":        _cluster_key(resolved),
            "language":       _language_for(resolved),
        },
        "repository": graph["repository"],
        "meta": {
            "analyzed_at":           datetime.now(timezone.utc).isoformat(),
            "graph_truncated":       graph["meta"].get("truncated", False),
            "files_analyzed":        graph["meta"].get("files_analyzed"),
            "max_depth_dependents":  max_depth_dependents,
            "max_depth_dependencies": max_depth_dependencies,
            "pr_sample_size":        pr_sample_size,
            "github_host":           (client.host.value if client else "github.com"),
        },
        "summary": {
            "risk_level":                risk,
            "direct_dependent_count":    len(direct_dependents),
            "transitive_dependent_count": len(transitive_dependents),
            "direct_dependency_count":   len([t for t in direct_deps if not t.startswith("pkg:")]),
            "package_dependency_count":  len([t for t in direct_deps if t.startswith("pkg:")]),
            "related_pr_count":          len(related_prs),
            "total_affected_files":      len(impact_paths),
            "message":                   messages[risk],
        },
        "dependents": {
            "direct": [
                _file_summary(p, in_deg.get(p, 0), out_deg.get(p, 0))
                for p in sorted(set(direct_dependents))
            ],
            "transitive": [
                _file_summary(p, in_deg.get(p, 0), out_deg.get(p, 0))
                for p in transitive_dependents
            ],
            "by_depth": {str(k): v for k, v in dep_by_depth.items() if k > 0},
        },
        "dependencies": {
            "direct": [
                {
                    "path":  t,
                    "label": t.removeprefix("pkg:") if t.startswith("pkg:") else PurePosixPath(t).name,
                    "type":  "package" if t.startswith("pkg:") else "file",
                }
                for t in sorted(set(direct_deps))
            ],
            "transitive": [
                _file_summary(p, in_deg.get(p, 0), out_deg.get(p, 0))
                for p in transitive_fwd
            ],
        },
        "related_prs": related_prs,
        "highlight": {
            "target":            resolved,
            "dependent_paths":   sorted(dep_visited),
            "dependency_paths":  sorted(fwd_visited),
            "node_ids":          sorted(impact_paths),
            "edge_ids":          impact_edge_ids,
            "paths":             sorted(impact_paths),
        },
        "subgraph": {
            "nodes": subgraph_nodes,
            "edges": [
                {
                    "id":     e.get("id", f"{e['source']}->{e['target']}"),
                    "source": e["source"],
                    "target": e["target"],
                    "kind":   e.get("kind", "import"),
                }
                for e in subgraph_edges
            ],
        },
    }