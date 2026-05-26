"""
Build file-level dependency summaries for Context Studio export.

Complements project_structure (folders/layers) with how source files import each other.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any


def _file_edges(graph: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for e in graph.get("edges", []):
        if e.get("kind") not in ("import", "require", "dynamic"):
            continue
        src, tgt = e.get("source"), e.get("target")
        if not src or not tgt or tgt.startswith("pkg:"):
            continue
        out.append({
            "source": src,
            "target": tgt,
            "kind": e.get("kind", "import"),
            "specifier": e.get("specifier"),
        })
    return out


def _package_imports(graph: dict[str, Any], *, max_packages: int) -> list[dict[str, Any]]:
    counts: Counter[str] = Counter()
    for e in graph.get("edges", []):
        tgt = e.get("target", "")
        if not tgt.startswith("pkg:"):
            continue
        name = tgt.removeprefix("pkg:")
        counts[name] += 1
    return [
        {"package": name, "import_count": c}
        for name, c in counts.most_common(max_packages)
    ]


def _prioritize_paths(
    graph: dict[str, Any],
    *,
    hot_paths: set[str],
    max_files: int,
) -> list[str]:
    """Files to model as SourceFile + dependency lists (hubs, hot files, high degree)."""
    nodes = [n for n in graph.get("nodes", []) if n.get("type") == "file"]
    scored: list[tuple[int, str]] = []
    for n in nodes:
        path = n.get("id") or n.get("path", "")
        if not path:
            continue
        score = n.get("in_degree", 0) * 3 + n.get("out_degree", 0)
        if path in hot_paths:
            score += 50
        if score > 0 or path in hot_paths:
            scored.append((score, path))
    scored.sort(reverse=True)
    seen: set[str] = set()
    ordered: list[str] = []
    for _, path in scored:
        if path in seen:
            continue
        seen.add(path)
        ordered.append(path)
        if len(ordered) >= max_files:
            break
    return ordered


def _file_dependency_records(
    edges: list[dict[str, Any]],
    paths: list[str],
    *,
    max_per_direction: int,
) -> list[dict[str, Any]]:
    imports_from: dict[str, list[dict[str, str]]] = defaultdict(list)
    imported_by: dict[str, list[dict[str, str]]] = defaultdict(list)
    path_set = set(paths)

    for e in edges:
        src, tgt = e["source"], e["target"]
        if src not in path_set and tgt not in path_set:
            continue
        if src in path_set:
            lst = imports_from[src]
            if len(lst) < max_per_direction:
                lst.append({"path": tgt, "kind": e.get("kind", "import")})
        if tgt in path_set:
            lst = imported_by[tgt]
            if len(lst) < max_per_direction:
                lst.append({"path": src, "kind": e.get("kind", "import")})

    records: list[dict[str, Any]] = []
    for path in paths:
        records.append({
            "path": path,
            "imports": imports_from.get(path, []),
            "imported_by": imported_by.get(path, []),
            "out_degree_sample": len(imports_from.get(path, [])),
            "in_degree_sample": len(imported_by.get(path, [])),
        })
    return records


def _sample_file_edges(
    edges: list[dict[str, Any]],
    priority_paths: set[str],
    *,
    max_edges: int,
) -> list[dict[str, Any]]:
    """Prefer edges touching hubs/hot files, then fill by frequency."""
    primary: list[dict[str, Any]] = []
    secondary: list[dict[str, Any]] = []
    for e in edges:
        if e["source"] in priority_paths or e["target"] in priority_paths:
            primary.append(e)
        else:
            secondary.append(e)
    out = primary[:max_edges]
    if len(out) < max_edges:
        out.extend(secondary[: max_edges - len(out)])
    return out


def build_project_dependencies(
    graph: dict[str, Any] | None,
    *,
    hot_files: list[dict[str, Any]] | None = None,
    max_file_edges: int = 100,
    max_files_modeled: int = 45,
    max_packages: int = 30,
    max_per_file_deps: int = 10,
) -> dict[str, Any]:
    """
    Curated dependency snapshot for Context Studio: file import edges, per-file lists,
    external packages, and graph stats. Safe for large repos (sampled, not full graph).
    """
    if not graph:
        return {
            "available": False,
            "summary": None,
            "hubs": [],
            "file_edges": [],
            "file_dependencies": [],
            "external_packages": [],
            "clusters": [],
        }

    hot_paths = {h.get("path", "") for h in (hot_files or []) if h.get("path")}
    file_edges_all = _file_edges(graph)
    priority_paths = set(_prioritize_paths(graph, hot_paths=hot_paths, max_files=max_files_modeled))
    priority_paths |= hot_paths

    hubs: list[dict[str, Any]] = []
    for n in sorted(
        [x for x in graph.get("nodes", []) if x.get("type") == "file"],
        key=lambda x: x.get("in_degree", 0),
        reverse=True,
    )[:20]:
        path = n.get("id") or n.get("path", "")
        if n.get("in_degree", 0) < 1:
            continue
        hubs.append({
            "path": path,
            "language": n.get("language", "unknown"),
            "in_degree": n.get("in_degree", 0),
            "out_degree": n.get("out_degree", 0),
        })

    modeled_paths = _prioritize_paths(
        graph, hot_paths=hot_paths, max_files=max_files_modeled
    )
    file_deps = _file_dependency_records(
        file_edges_all,
        modeled_paths,
        max_per_direction=max_per_file_deps,
    )

    stats = graph.get("stats") or {}
    meta = graph.get("meta") or {}
    file_edge_count = len(file_edges_all)
    pkg_edge_count = sum(
        1 for e in graph.get("edges", [])
        if (e.get("target") or "").startswith("pkg:")
    )

    clusters_out: list[dict[str, Any]] = []
    for c in (graph.get("clusters") or [])[:15]:
        if not isinstance(c, dict):
            continue
        cid = c.get("id") or c.get("label") or c.get("name")
        paths = c.get("paths") or []
        internal = 0
        for e in file_edges_all:
            if e["source"] in paths and e["target"] in paths:
                internal += 1
        clusters_out.append({
            "id": cid,
            "file_count": c.get("file_count") or len(paths),
            "internal_import_edges": internal,
        })

    return {
        "available": True,
        "summary": {
            "files_analyzed": meta.get("files_analyzed"),
            "node_count": stats.get("node_count"),
            "edge_count": stats.get("edge_count"),
            "file_to_file_edges": file_edge_count,
            "package_import_edges": pkg_edge_count,
            "package_count": stats.get("package_count"),
            "truncated": meta.get("truncated", False),
            "languages": stats.get("languages") or {},
            "modeled_file_count": len(modeled_paths),
            "sampled_file_edge_count": min(max_file_edges, file_edge_count),
        },
        "hubs": hubs[:15],
        "file_edges": _sample_file_edges(
            file_edges_all, priority_paths, max_edges=max_file_edges
        ),
        "file_dependencies": file_deps,
        "external_packages": _package_imports(graph, max_packages=max_packages),
        "clusters": clusters_out,
    }
