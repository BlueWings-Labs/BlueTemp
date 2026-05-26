"""
Build repository project structure + connectivity summaries for Context Studio export.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

# Heuristic layer labels from top-level / second-level folder names
_LAYER_HINTS: dict[str, str] = {
    "frontend": "presentation",
    "client": "presentation",
    "web": "presentation",
    "ui": "presentation",
    "app": "application",
    "src": "application",
    "lib": "shared-library",
    "pkg": "packages",
    "packages": "packages",
    "api": "api-boundary",
    "server": "runtime",
    "backend": "runtime",
    "services": "services",
    "service": "services",
    "worker": "background",
    "jobs": "background",
    "cmd": "cli-entry",
    "scripts": "tooling",
    "docs": "documentation",
    "test": "tests",
    "tests": "tests",
    "__tests__": "tests",
    "intelligence": "domain",
    "dependency_graph": "domain",
}


def _top_segment(path: str) -> str:
    parts = path.replace("\\", "/").split("/")
    return parts[0] if parts else "(root)"


def _layer_for_path(path: str) -> str:
    parts = path.replace("\\", "/").split("/")
    for seg in parts[:2]:
        key = seg.lower()
        if key in _LAYER_HINTS:
            return _LAYER_HINTS[key]
    return "general"


def _insert_path(tree: dict[str, Any], parts: list[str], file_meta: dict[str, Any] | None) -> None:
    node = tree
    for i, part in enumerate(parts):
        is_leaf = i == len(parts) - 1
        if part not in node:
            node[part] = {"_files": 0, "_children": {}}
        if is_leaf and file_meta:
            node[part]["_files"] += 1
        elif not is_leaf:
            node = node[part]["_children"]
    if not parts and file_meta:
        tree.setdefault("(root)", {"_files": 0, "_children": {}})
        tree["(root)"]["_files"] += 1


def _tree_to_markdown(tree: dict[str, Any], prefix: str = "", depth: int = 0, max_depth: int = 4) -> list[str]:
    lines: list[str] = []
    if depth > max_depth:
        return lines
    for name in sorted(tree.keys()):
        if name.startswith("_"):
            continue
        entry = tree[name]
        indent = "  " * depth
        fc = entry.get("_files", 0)
        child_count = len([k for k in entry.get("_children", {}) if not k.startswith("_")])
        label = f"{name}/" if child_count or fc else name
        extra = f" ({fc} files)" if fc else ""
        if child_count:
            extra += f", {child_count} subfolders"
        lines.append(f"{indent}- {label}{extra}")
        lines.extend(
            _tree_to_markdown(entry.get("_children", {}), prefix, depth + 1, max_depth)
        )
    return lines


def _collect_directories(
    tree: dict[str, Any],
    parent_path: str = "",
    depth: int = 0,
    max_depth: int = 3,
    out: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    if out is None:
        out = []
    if depth > max_depth:
        return out
    for name, entry in sorted(tree.items()):
        if name.startswith("_"):
            continue
        path = f"{parent_path}/{name}".strip("/") if parent_path else name
        children = entry.get("_children", {})
        sub_names = [k for k in children if not k.startswith("_")]
        out.append({
            "path": path,
            "name": name,
            "depth": depth,
            "file_count": entry.get("_files", 0),
            "subdirectory_count": len(sub_names),
            "layer": _layer_for_path(path),
            "parent_path": parent_path or None,
        })
        _collect_directories(children, path, depth + 1, max_depth, out)
    return out


def build_cross_module_connections(
    graph: dict[str, Any] | None,
    *,
    max_edges: int = 25,
) -> list[dict[str, Any]]:
    """Aggregate import edges by top-level module pair (how code areas connect)."""
    if not graph:
        return []
    pair_count: Counter[tuple[str, str]] = Counter()
    for e in graph.get("edges", []):
        if e.get("kind") not in ("import", "require", "dynamic"):
            continue
        src, tgt = e.get("source"), e.get("target")
        if not src or not tgt or tgt.startswith("pkg:"):
            continue
        a, b = _top_segment(src), _top_segment(tgt)
        if a != b:
            pair_count[(a, b)] += 1
    return [
        {
            "from_module": a,
            "to_module": b,
            "import_count": c,
            "description": f"`{a}/` imports from `{b}/` ({c} sampled edges)",
        }
        for (a, b), c in pair_count.most_common(max_edges)
    ]


def build_project_structure(
    file_tree: list[dict[str, Any]],
    *,
    graph: dict[str, Any] | None = None,
    modules: list[dict[str, Any]] | None = None,
    max_tree_depth: int = 4,
    max_directories: int = 50,
) -> dict[str, Any]:
    """
    Full project layout for Context Studio schema/context:
    directory tree, layers, extension mix, cross-module import links.
    """
    paths = [f.get("path", "") for f in file_tree if f.get("path")]
    ext_counter: Counter[str] = Counter()
    nested: dict[str, Any] = {}

    for f in file_tree:
        path = f.get("path", "")
        if not path:
            continue
        ext = f.get("extension") or ""
        if ext:
            ext_counter[ext] += 1
        parts = path.replace("\\", "/").split("/")
        if len(parts) == 1:
            _insert_path(nested, [], f)
        else:
            _insert_path(nested, parts[:-1], f)
            # count file in leaf folder's parent chain already; file itself at leaf dir
            dir_parts = parts[:-1]
            node = nested
            for p in dir_parts:
                node = node[p]["_children"]

    directories = _collect_directories(nested, max_depth=max_tree_depth)[:max_directories]
    tree_md = _tree_to_markdown(nested, max_depth=max_tree_depth)

    layer_agg: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"file_count": 0, "directories": [], "sample_paths": []}
    )
    for d in directories:
        if d["depth"] > 1:
            continue
        layer = d["layer"]
        layer_agg[layer]["file_count"] += d["file_count"]
        if len(layer_agg[layer]["directories"]) < 8:
            layer_agg[layer]["directories"].append(d["path"])
    for f in file_tree[:500]:
        path = f.get("path", "")
        if not path:
            continue
        layer = _layer_for_path(path)
        samples = layer_agg[layer]["sample_paths"]
        if len(samples) < 5 and path not in samples:
            samples.append(path)

    layers = [
        {
            "layer": name,
            "role": name.replace("-", " "),
            "file_count": data["file_count"],
            "top_directories": data["directories"],
            "sample_paths": data["sample_paths"][:5],
        }
        for name, data in sorted(layer_agg.items(), key=lambda x: -x[1]["file_count"])
    ]

    clusters = []
    if graph:
        for c in (graph.get("clusters") or [])[:20]:
            if isinstance(c, dict):
                clusters.append({
                    "name": c.get("name") or c.get("id"),
                    "file_count": c.get("file_count"),
                })
            elif isinstance(c, str):
                clusters.append({"name": c})

    return {
        "total_files": len(paths),
        "total_directories": len(directories),
        "extension_breakdown": [
            {"extension": e, "count": n} for e, n in ext_counter.most_common(12)
        ],
        "directory_tree_markdown": tree_md,
        "directories": directories,
        "layers": layers,
        "graph_clusters": clusters,
        "cross_module_connections": build_cross_module_connections(graph),
        "modules_alignment": [
            {"module": m.get("name"), "importance": m.get("importance"), "file_count": m.get("file_count")}
            for m in (modules or [])[:15]
        ],
    }
