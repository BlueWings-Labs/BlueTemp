"""
Build insight graphs for blast-radius quick actions (visual Q&A context).
"""

from __future__ import annotations

import json
import re
from typing import Any

INSIGHT_GRAPH_BLOCK = re.compile(
    r"```(?:insight_graph|json)\s*\n([\s\S]*?)\n```",
    re.IGNORECASE,
)

NODE_COLORS: dict[str, str] = {
    "target": "#dc2626",
    "file": "#2563eb",
    "dependent": "#d97706",
    "import": "#7c3aed",
    "package": "#8b5cf6",
    "pr": "#059669",
    "test": "#0891b2",
    "layer": "#64748b",
    "concept": "#0ea5e9",
    "risk": "#b45309",
}


def _node(
    nid: str,
    label: str,
    *,
    ntype: str = "file",
    group: str | None = None,
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "id": nid,
        "label": label,
        "type": ntype,
        "group": group or ntype,
        "color": NODE_COLORS.get(ntype, "#64748b"),
        **(meta or {}),
    }


def _edge(
    source: str,
    target: str,
    *,
    eid: str | None = None,
    label: str | None = None,
    kind: str = "relates",
) -> dict[str, Any]:
    return {
        "id": eid or f"{source}->{target}",
        "source": source,
        "target": target,
        "label": label,
        "kind": kind,
    }


def build_insight_graph(impact: dict[str, Any], action_id: str) -> dict[str, Any]:
    """Deterministic graph from blast-radius data for a quick action."""
    target = impact.get("target") or {}
    path = target.get("path", "?")
    if not target.get("resolved"):
        return {"kind": action_id, "title": "Unresolved target", "nodes": [], "edges": []}

    if action_id == "blast_map":
        return _blast_map_graph(impact, path)
    if action_id == "dependents_layers":
        return _dependents_layers_graph(impact, path)
    if action_id == "imports_chain":
        return _imports_chain_graph(impact, path)
    if action_id == "pr_activity":
        return _pr_activity_graph(impact, path)
    if action_id == "test_matrix":
        return _test_matrix_graph(impact, path)
    if action_id == "refactor_risk":
        return _refactor_risk_graph(impact, path)
    return _blast_map_graph(impact, path)


def _blast_map_graph(impact: dict[str, Any], path: str) -> dict[str, Any]:
    sub = impact.get("subgraph") or {}
    nodes = [
        _node(
            n["id"],
            n.get("label", n["id"]),
            ntype="package" if n.get("type") == "package" else "file",
            meta={"path": n.get("path", n["id"])},
        )
        for n in sub.get("nodes", [])
    ]
    edges = [
        _edge(
            e["source"],
            e["target"],
            eid=e.get("id"),
            label=e.get("kind"),
            kind=e.get("kind", "import"),
        )
        for e in sub.get("edges", [])
    ]
    for n in nodes:
        if n["id"] == path:
            n["type"] = "target"
            n["group"] = "target"
            n["color"] = NODE_COLORS["target"]
    return {
        "kind": "blast_map",
        "title": "Blast radius map",
        "description": "Files and imports in the impact neighborhood",
        "nodes": nodes,
        "edges": edges,
    }


def _dependents_layers_graph(impact: dict[str, Any], path: str) -> dict[str, Any]:
    nodes = [_node(path, path.split("/")[-1], ntype="target", meta={"path": path})]
    edges: list[dict[str, Any]] = []
    by_depth = impact.get("dependents", {}).get("by_depth") or {}

    for depth_str, files in sorted(by_depth.items(), key=lambda x: int(x[0])):
        depth = int(depth_str)
        layer_id = f"layer:{depth}"
        nodes.append(
            _node(layer_id, f"Depth {depth}", ntype="layer", meta={"depth": depth})
        )
        for fpath in files:
            if fpath == path or fpath.startswith("pkg:"):
                continue
            nodes.append(
                _node(
                    fpath,
                    fpath.split("/")[-1],
                    ntype="dependent",
                    meta={"path": fpath, "depth": depth},
                )
            )
            edges.append(_edge(fpath, path if depth == 1 else layer_id, label="imports"))
            if depth > 1:
                prev = f"layer:{depth - 1}"
                edges.append(_edge(layer_id, prev, label="upstream", kind="layer"))

    for item in impact.get("dependents", {}).get("direct", []):
        fp = item.get("path", "")
        if fp and fp != path:
            if not any(n["id"] == fp for n in nodes):
                nodes.append(
                    _node(fp, item.get("label", fp.split("/")[-1]), ntype="dependent", meta={"path": fp})
                )
            if not any(e["source"] == fp and e["target"] == path for e in edges):
                edges.append(_edge(fp, path, label="direct import"))

    return {
        "kind": "dependents_layers",
        "title": "Who depends on this file",
        "description": "Layers of importers (closer = higher risk)",
        "nodes": nodes,
        "edges": edges,
    }


def _imports_chain_graph(impact: dict[str, Any], path: str) -> dict[str, Any]:
    nodes = [_node(path, path.split("/")[-1], ntype="target", meta={"path": path})]
    edges: list[dict[str, Any]] = []

    for item in impact.get("dependencies", {}).get("direct", []):
        fp = item.get("path", "")
        if not fp:
            continue
        ntype = "package" if fp.startswith("pkg:") else "import"
        nodes.append(_node(fp, item.get("label", fp), ntype=ntype, meta={"path": fp}))
        edges.append(_edge(path, fp, label="imports"))

    for item in impact.get("dependencies", {}).get("transitive", [])[:12]:
        fp = item.get("path", "")
        if fp and not any(n["id"] == fp for n in nodes):
            nodes.append(
                _node(fp, item.get("label", fp.split("/")[-1]), ntype="import", meta={"path": fp})
            )

    return {
        "kind": "imports_chain",
        "title": "What this file pulls in",
        "description": "Direct and transitive imports from the target",
        "nodes": nodes,
        "edges": edges,
    }


def _pr_activity_graph(impact: dict[str, Any], path: str) -> dict[str, Any]:
    nodes = [_node(path, path.split("/")[-1], ntype="target", meta={"path": path})]
    edges: list[dict[str, Any]] = []

    for pr in (impact.get("related_prs") or [])[:10]:
        pid = f"pr:{pr.get('number')}"
        label = f"#{pr.get('number')}"
        nodes.append(
            _node(
                pid,
                label,
                ntype="pr",
                meta={"title": pr.get("title"), "url": pr.get("url"), "state": pr.get("state")},
            )
        )
        edges.append(_edge(pid, path, label=pr.get("state", "pr")))

    return {
        "kind": "pr_activity",
        "title": "Related pull requests",
        "description": "PRs that touched this file recently",
        "nodes": nodes,
        "edges": edges,
    }


def _test_matrix_graph(impact: dict[str, Any], path: str) -> dict[str, Any]:
    nodes = [_node(path, path.split("/")[-1], ntype="target", meta={"path": path})]
    edges: list[dict[str, Any]] = []
    root_test = _node("test:root", "Regression suite", ntype="test")
    nodes.append(root_test)
    edges.append(_edge(path, "test:root", label="change here"))

    for item in impact.get("dependents", {}).get("direct", [])[:10]:
        fp = item.get("path", "")
        if not fp:
            continue
        nodes.append(
            _node(fp, item.get("label", fp.split("/")[-1]), ntype="dependent", meta={"path": fp})
        )
        tid = f"test:{fp}"
        nodes.append(_node(tid, f"Test {fp.split('/')[-1]}", ntype="test"))
        edges.append(_edge(fp, path, label="imports"))
        edges.append(_edge(tid, fp, label="verify"))

    return {
        "kind": "test_matrix",
        "title": "Suggested test coverage",
        "description": "Target → importers → areas to verify before merge",
        "nodes": nodes,
        "edges": edges,
    }


def _refactor_risk_graph(impact: dict[str, Any], path: str) -> dict[str, Any]:
    summary = impact.get("summary") or {}
    risk = summary.get("risk_level", "low")
    nodes = [
        _node(path, path.split("/")[-1], ntype="target", meta={"path": path}),
        _node(
            f"risk:{risk}",
            f"Risk: {risk}",
            ntype="risk",
            meta={"direct_deps": summary.get("direct_dependent_count")},
        ),
    ]
    edges = [_edge(f"risk:{risk}", path, label="assessment")]

    for item in impact.get("dependents", {}).get("direct", [])[:15]:
        fp = item.get("path", "")
        if not fp:
            continue
        in_deg = item.get("in_degree", 0)
        nodes.append(
            _node(
                fp,
                f"{item.get('label', fp)} ({in_deg} in)",
                ntype="dependent",
                meta={"path": fp, "in_degree": in_deg},
            )
        )
        edges.append(_edge(fp, path, label="breaks if refactored"))

    return {
        "kind": "refactor_risk",
        "title": "Refactor risk map",
        "description": "Direct importers that would need updates",
        "nodes": nodes,
        "edges": edges,
    }


def merge_ai_insight_graph(
    base: dict[str, Any],
    ai_graph: dict[str, Any] | None,
) -> dict[str, Any]:
    """Overlay AI-provided concept nodes onto the base graph."""
    if not ai_graph:
        return base
    ai_nodes = ai_graph.get("nodes") or []
    ai_edges = ai_graph.get("edges") or []
    if not ai_nodes:
        return base

    seen_ids = {n["id"] for n in base.get("nodes", [])}
    nodes = list(base.get("nodes", []))
    edges = list(base.get("edges", []))

    for n in ai_nodes:
        nid = n.get("id") or n.get("label")
        if not nid or nid in seen_ids:
            continue
        seen_ids.add(nid)
        nodes.append(
            _node(
                nid,
                n.get("label", nid),
                ntype=n.get("type", "concept"),
                group=n.get("group"),
            )
        )
    for e in ai_edges:
        src, tgt = e.get("source"), e.get("target")
        if src and tgt:
            edges.append(
                _edge(src, tgt, eid=e.get("id"), label=e.get("label"), kind=e.get("kind", "concept"))
            )

    out = dict(base)
    out["nodes"] = nodes
    out["edges"] = edges
    if ai_graph.get("title"):
        out["ai_title"] = ai_graph["title"]
    return out


def parse_insight_graph_from_message(text: str) -> tuple[str, dict[str, Any] | None]:
    """Strip ```insight_graph``` block from assistant message; return clean text + graph."""
    match = INSIGHT_GRAPH_BLOCK.search(text)
    if not match:
        return text, None
    raw = match.group(1).strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return text, None
    clean = INSIGHT_GRAPH_BLOCK.sub("", text).strip()
    clean = re.sub(r"\n{3,}", "\n\n", clean)
    return clean, data


def get_quick_actions(impact: dict[str, Any]) -> list[dict[str, Any]]:
    """Context-aware quick actions for the blast-radius chat UI."""
    summary = impact.get("summary") or {}
    deps = impact.get("dependents", {}) or {}
    prs = impact.get("related_prs") or []
    direct_count = len(deps.get("direct") or [])
    pr_count = len(prs)
    risk = summary.get("risk_level", "low")

    actions: list[dict[str, Any]] = [
        {
            "id": "blast_map",
            "label": "Impact map",
            "short_label": "Map",
            "prompt": "Walk me through the blast radius map: who imports this file, what it imports, and where the highest-risk edges are.",
            "graph_kind": "blast_map",
        },
        {
            "id": "explain_file",
            "label": "Explain file",
            "short_label": "Explain",
            "prompt": "What are the main functions, exports, and responsibilities of this file? Which symbols would a refactor touch?",
            "graph_kind": "blast_map",
            "request_ai_graph": True,
        },
        {
            "id": "refactor_risk",
            "label": "Refactor risk",
            "short_label": "Risk",
            "prompt": "If I refactor this file, which dependent files break first and what should I change in each?",
            "graph_kind": "refactor_risk",
        },
    ]

    if direct_count > 0:
        actions.append(
            {
                "id": "dependents_layers",
                "label": "Who breaks?",
                "short_label": "Dependents",
                "prompt": "List dependent files by blast-radius depth and explain what each one uses from the target file.",
                "graph_kind": "dependents_layers",
            }
        )
        actions.append(
            {
                "id": "test_matrix",
                "label": "Test plan",
                "short_label": "Tests",
                "prompt": "What should I test before merging a change to this file? Map tests to each direct dependent.",
                "graph_kind": "test_matrix",
                "request_ai_graph": True,
            }
        )

    actions.append(
        {
            "id": "imports_chain",
            "label": "Imports",
            "short_label": "Imports",
            "prompt": "Explain the import chain: what does this file depend on and could upstream changes affect it?",
            "graph_kind": "imports_chain",
        }
    )

    if pr_count > 0:
        actions.append(
            {
                "id": "pr_activity",
                "label": "PR history",
                "short_label": "PRs",
                "prompt": "Summarize what the related PRs changed in this file and what patterns I should watch for.",
                "graph_kind": "pr_activity",
            }
        )

    if risk in ("high", "medium"):
        actions.append(
            {
                "id": "review_checklist",
                "label": "Review checklist",
                "short_label": "Review",
                "prompt": "Give a concise pre-merge review checklist for this high-impact file: owners, tests, docs, and rollout steps.",
                "graph_kind": "refactor_risk",
                "request_ai_graph": True,
            }
        )

    return actions


GRAPH_APPEND_INSTRUCTION = """
After your answer, append a JSON insight graph for visualization:

```insight_graph
{
  "title": "short title",
  "nodes": [{"id": "unique", "label": "display", "type": "concept|file|test|risk"}],
  "edges": [{"source": "id", "target": "id", "label": "optional"}]
}
```

Use 4–12 nodes max. Reuse file paths from the blast radius data as node ids when possible.
"""
