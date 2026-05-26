"""
Build a dependency graph JSON document from a GitHub repository.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import PurePosixPath
from typing import Any

import github_services as gh
from github_services import GitHubClient
from dependency_graph.constants import (
    ANALYZABLE_EXTENSIONS,
    GRAPH_VERSION,
    LANGUAGE_BY_EXT,
    SKIP_DIR_NAMES,
)
from dependency_graph.parser import parse_imports
from dependency_graph.resolver import (
    build_file_tree,
    build_path_index,
    detect_path_aliases,
    is_analyzable_path,
    resolve_specifier,
    should_skip_path,
)


def _language_for(path: str) -> str:
    ext = PurePosixPath(path).suffix.lower()
    return LANGUAGE_BY_EXT.get(ext, "unknown")


def _cluster_key(path: str) -> str:
    parts = path.split("/")
    if len(parts) >= 2:
        return f"{parts[0]}/{parts[1]}"
    return parts[0] if parts else "root"


async def build_dependency_graph(
    owner: str,
    repo: str,
    *,
    ref: str | None = None,
    max_files: int = 400,
    include_packages: bool = True,
    focus_path: str | None = None,
    max_depth: int | None = None,
    client: GitHubClient | None = None,
) -> dict[str, Any]:
    """
    Analyze import relationships and return a graph-ready JSON structure.

    focus_path + max_depth: return subgraph reachable from one file (BFS).
    Pass `client=GitHubClient(host='ibm')` to target GitHub Enterprise.
    """
    info, tree = await asyncio.gather(
        gh.get_repo_info(owner, repo, client=client),
        gh.get_repo_file_tree(owner, repo, max_files=5000, client=client),
    )
    branch = ref or info.get("default_branch") or "main"

    all_paths = [t["path"] for t in tree]
    candidates = [
        p for p in all_paths
        if is_analyzable_path(p) and not should_skip_path(p, SKIP_DIR_NAMES)
    ]
    candidates.sort(key=lambda p: (p.count("/"), p))
    if len(candidates) > max_files:
        candidates = candidates[:max_files]
        truncated = True
    else:
        truncated = len(all_paths) >= 5000

    contents, fetch_stats = await gh.get_file_contents_batch(
        owner, repo, candidates, ref=branch, client=client
    )
    file_set = frozenset(candidates)
    path_index = build_path_index(candidates)
    aliases = detect_path_aliases(all_paths)

    edges_raw: list[dict[str, Any]] = []
    out_degree: dict[str, int] = defaultdict(int)
    in_degree: dict[str, int] = defaultdict(int)
    package_nodes: set[str] = set()

    for path, content in contents.items():
        if not content:
            continue
        for imp in parse_imports(path, content):
            target, kind = resolve_specifier(
                path,
                imp.specifier,
                file_set=file_set,
                path_index=path_index,
                path_aliases=aliases,
            )
            if not target:
                continue
            if kind == "package":
                if not include_packages:
                    continue
                package_nodes.add(target)
                edge_kind = imp.kind if imp.kind != "import" else "package"
            else:
                edge_kind = imp.kind

            edges_raw.append({
                "source": path,
                "target": target,
                "kind": edge_kind,
                "specifier": imp.specifier,
            })
            out_degree[path] += 1
            in_degree[target] += 1

    # Subgraph filter
    if focus_path:
        focus = focus_path.lstrip("/")
        if focus not in file_set:
            hit, _ = resolve_specifier(
                focus, focus,
                file_set=file_set,
                path_index=path_index,
                path_aliases=aliases,
            )
            focus = hit or focus
        edges_filtered = _subgraph_edges(edges_raw, focus, max_depth)
        active_files = {focus}
        for e in edges_filtered:
            if not e["target"].startswith("pkg:"):
                active_files.add(e["source"])
                active_files.add(e["target"])
        candidates = [p for p in candidates if p in active_files]
        edges_raw = edges_filtered
        package_nodes = {e["target"] for e in edges_raw if e["target"].startswith("pkg:")}

    nodes: list[dict[str, Any]] = []
    for path in candidates:
        nodes.append({
            "id":        path,
            "path":      path,
            "label":     PurePosixPath(path).name,
            "type":      "file",
            "language":  _language_for(path),
            "extension": PurePosixPath(path).suffix.lower(),
            "in_degree":  in_degree.get(path, 0),
            "out_degree": out_degree.get(path, 0),
        })

    for pkg_id in sorted(package_nodes):
        name = pkg_id.removeprefix("pkg:")
        nodes.append({
            "id":        pkg_id,
            "path":      pkg_id,
            "label":     name,
            "type":      "package",
            "language":  "external",
            "extension": "",
            "in_degree":  in_degree.get(pkg_id, 0),
            "out_degree": 0,
        })

    node_ids = {n["id"] for n in nodes}
    edges: list[dict[str, Any]] = []
    for i, e in enumerate(edges_raw):
        if e["source"] not in node_ids or e["target"] not in node_ids:
            continue
        edges.append({
            "id":        f"e{i}",
            "source":    e["source"],
            "target":    e["target"],
            "kind":      e["kind"],
            "specifier": e.get("specifier"),
        })

    clusters: dict[str, list[str]] = defaultdict(list)
    for path in candidates:
        clusters[_cluster_key(path)].append(path)

    cluster_list = [
        {"id": k, "label": k, "file_count": len(v), "paths": v[:20]}
        for k, v in sorted(clusters.items(), key=lambda x: -len(x[1]))
    ]

    languages: dict[str, int] = defaultdict(int)
    for n in nodes:
        if n["type"] == "file":
            languages[n["language"]] += 1

    return {
        "version": GRAPH_VERSION,
        "repository": {
            "owner":           owner,
            "repo":            repo,
            "full_name":       info.get("name") or f"{owner}/{repo}",
            "default_branch":  branch,
            "primary_language": info.get("language"),
            "url":             info.get("url"),
        },
        "meta": {
            "analyzed_at":   datetime.now(timezone.utc).isoformat(),
            "files_analyzed": len(candidates),
            "files_in_tree": len(all_paths),
            "truncated":     truncated,
            "include_packages": include_packages,
            "focus_path":    focus_path,
            "max_depth":     max_depth,
            "fetch":         fetch_stats,
            "github_host":   (client.host.value if client else "github.com"),
        },
        "stats": {
            "node_count":    len(nodes),
            "edge_count":    len(edges),
            "file_count":    len(candidates),
            "package_count": len(package_nodes),
            "languages":     dict(languages),
        },
        "file_tree": build_file_tree(candidates),
        "nodes":     nodes,
        "edges":     edges,
        "clusters":  cluster_list,
    }


def _subgraph_edges(
    edges: list[dict[str, Any]],
    start: str,
    max_depth: int | None,
) -> list[dict[str, Any]]:
    """BFS from start following source -> target edges (outgoing deps)."""
    by_source: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for e in edges:
        by_source[e["source"]].append(e)

    visited: set[str] = {start}
    frontier = [start]
    depth = 0
    collected: list[dict[str, Any]] = []

    while frontier and (max_depth is None or depth < max_depth):
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

    return collected