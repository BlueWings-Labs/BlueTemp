"""
Context Studio export — facts pack, JSON-LD (ICA lab syntax), markdown docs, ZIP bundle.
"""

from __future__ import annotations

import asyncio
import io
import json
import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import quote

import github_services as gh
from intelligence.analyzer import analyze_snapshot
from intelligence.collector import collect_repository_snapshot
from intelligence.project_dependencies import build_project_dependencies
from intelligence.project_structure import build_project_structure

SCHEMA_VERSION = "1.2.0"
SCHEMA_FILENAME = "software-repository-archaeology-schema.jsonld"
SCHEMA_PATH = Path(__file__).resolve().parent.parent / "context_studio" / SCHEMA_FILENAME

SRA_CONTEXT: dict[str, Any] = {
    "sra": "https://bluewings.dev/sra#",
    "schema": "http://schema.org/",
    "id": "@id",
    "type": "@type",
    "name": "schema:name",
    "description": "schema:description",
    "attributes": "sra:attributes",
    "identityKey": "sra:identityKey",
    "humanRef": "sra:humanRef",
    "invariant": "sra:invariant",
    "hasState": {"@id": "sra:hasState", "@type": "@id"},
    "initialState": {"@id": "sra:initialState", "@type": "@id"},
    "terminalStates": {"@id": "sra:terminalStates", "@type": "@id"},
    "relatesTo": {"@id": "sra:relatesTo", "@type": "@id"},
    "emitsEvent": {"@id": "sra:emitsEvent", "@type": "@id"},
    "from": {"@id": "sra:from", "@type": "@id"},
    "to": {"@id": "sra:to", "@type": "@id"},
    "precondition": "sra:precondition",
    "postcondition": "sra:postcondition",
    "Entity": "sra:Entity",
    "Operation": "sra:Operation",
    "State": "sra:State",
}


def _instance_id(owner: str, repo: str, kind: str, key: str) -> str:
    safe = quote(key, safe="")
    return f"sra:instance/{owner}/{repo}/{kind}/{safe}"


def _repo_instance_id(owner: str, repo: str) -> str:
    return f"sra:instance/{owner}/{repo}"


def _risk_state(risk: str) -> str:
    return {
        "high": "sra:FileRiskHigh",
        "medium": "sra:FileRiskMedium",
    }.get(risk, "sra:FileRiskLow")


def extract_graph_hubs(graph: dict[str, Any], top_n: int = 15) -> list[dict[str, Any]]:
    """Top in-degree file nodes from dependency graph."""
    nodes = [n for n in graph.get("nodes", []) if n.get("type") == "file"]
    edges = graph.get("edges", [])
    in_deg: dict[str, int] = {n["id"]: 0 for n in nodes}
    out_deg: dict[str, int] = {n["id"]: 0 for n in nodes}
    for e in edges:
        if e.get("kind") not in ("import", "require", "dynamic"):
            continue
        tgt, src = e.get("target"), e.get("source")
        if tgt in in_deg:
            in_deg[tgt] = in_deg.get(tgt, 0) + 1
        if src in out_deg:
            out_deg[src] = out_deg.get(src, 0) + 1
    ranked = sorted(nodes, key=lambda n: in_deg.get(n["id"], 0), reverse=True)
    hubs: list[dict[str, Any]] = []
    for n in ranked[:top_n]:
        if in_deg.get(n["id"], 0) < 1:
            continue
        hubs.append({
            "path": n["id"],
            "language": n.get("language", "unknown"),
            "in_degree": in_deg.get(n["id"], 0),
            "out_degree": out_deg.get(n["id"], 0),
            "cluster": n.get("cluster"),
        })
    return hubs


def extract_hub_edges(graph: dict[str, Any], hub_paths: set[str], max_edges: int = 40) -> list[dict[str, str]]:
    edges: list[dict[str, str]] = []
    for e in graph.get("edges", []):
        if e.get("kind") not in ("import", "require", "dynamic"):
            continue
        src, tgt = e.get("source"), e.get("target")
        if src in hub_paths and tgt in hub_paths:
            edges.append({"source": src, "target": tgt, "kind": e.get("kind", "import")})
        if len(edges) >= max_edges:
            break
    return edges


def build_facts_pack(
    owner: str,
    repo: str,
    snapshot: dict[str, Any],
    insights: dict[str, Any],
    *,
    graph: dict[str, Any] | None = None,
    readme_max_chars: int = 4000,
) -> dict[str, Any]:
    """Curated facts for JSON-LD and docs — never the full file tree."""
    info = snapshot.get("info", {})
    readme = snapshot.get("readme")
    readme_text = ""
    if readme and readme.get("content"):
        readme_text = readme["content"][:readme_max_chars]
        if len(readme.get("content", "")) > readme_max_chars:
            readme_text += "\n… (truncated)"

    hubs = extract_graph_hubs(graph, top_n=15) if graph else []
    hub_edges: list[dict[str, str]] = []
    if graph and hubs:
        hub_paths = {h["path"] for h in hubs}
        hub_edges = extract_hub_edges(graph, hub_paths)

    arch = insights.get("architecture", {})
    modules = (arch.get("modules") or [])[:15]
    file_tree = snapshot.get("file_tree") or []
    project_structure = build_project_structure(
        file_tree,
        graph=graph,
        modules=modules,
    )
    project_dependencies = build_project_dependencies(
        graph,
        hot_files=insights.get("hot_files") or [],
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "repository": {
            "owner": owner,
            "repo": repo,
            "full_name": f"{owner}/{repo}",
            "url": info.get("url") or f"https://github.com/{owner}/{repo}",
            "default_branch": info.get("default_branch", "main"),
            "collected_at": snapshot.get("collected_at") or insights.get("collected_at"),
        },
        "summary": insights.get("summary", {}),
        "modules": modules,
        "project_structure": project_structure,
        "project_dependencies": project_dependencies,
        "hot_files": (insights.get("hot_files") or [])[:20],
        "architectural_prs": (insights.get("evolution", {}).get("architectural_prs") or [])[:12],
        "contributors": (insights.get("contributors") or [])[:12],
        "onboarding": insights.get("onboarding", {}),
        "migration": insights.get("migration", {}),
        "technical_debt": insights.get("technical_debt") or [],
        "dependency_manifests": (insights.get("dependencies") or [])[:20],
        "entry_candidates": (arch.get("entry_candidates") or [])[:15],
        "standalone_service_candidates": arch.get("standalone_service_candidates") or [],
        "evolution_timeline": (insights.get("evolution", {}).get("timeline") or [])[-12:],
        "graph_hubs": hubs,
        "graph_hub_edges": hub_edges,
        "graph_meta": {
            "truncated": (graph or {}).get("meta", {}).get("truncated", False),
            "node_count": (graph or {}).get("stats", {}).get("node_count"),
            "edge_count": (graph or {}).get("stats", {}).get("edge_count"),
        } if graph else None,
        "readme_excerpt": readme_text,
    }


def _entity_instance(
    iid: str,
    entity_name: str,
    *,
    human_ref: str,
    description: str,
    attributes: dict[str, Any],
    relates_to: list[str] | None = None,
    has_state: list[str] | None = None,
    initial_state: str | None = None,
) -> dict[str, Any]:
    node: dict[str, Any] = {
        "id": iid,
        "type": "Entity",
        "name": entity_name,
        "description": description,
        "humanRef": human_ref,
        "attributes": attributes,
    }
    if relates_to:
        node["relatesTo"] = relates_to
    if has_state:
        node["hasState"] = has_state
    if initial_state:
        node["initialState"] = initial_state
    return node


def _operation_instance(
    iid: str,
    op_name: str,
    from_id: str,
    to_id: str,
    description: str,
) -> dict[str, Any]:
    return {
        "id": iid,
        "type": "Operation",
        "name": op_name,
        "description": description,
        "from": from_id,
        "to": to_id,
        "precondition": ["Instances exist in this repository snapshot"],
        "postcondition": ["Relationship recorded for agent grounding"],
    }


def build_instances_jsonld(facts: dict[str, Any]) -> dict[str, Any]:
    """Per-repo instance graph — ICA Context Studio lab @context + @graph syntax."""
    owner = facts["repository"]["owner"]
    repo = facts["repository"]["repo"]
    full = facts["repository"]["full_name"]
    repo_id = _repo_instance_id(owner, repo)
    graph: list[dict[str, Any]] = []

    summary = facts.get("summary", {})
    stats = summary.get("stats") or {}
    graph.append(
        _entity_instance(
            repo_id,
            "Repository",
            human_ref=full,
            description=summary.get("description") or f"GitHub repository {full}",
            attributes={
                "fullName": full,
                "owner": owner,
                "repo": repo,
                "defaultBranch": facts["repository"].get("default_branch", "main"),
                "primaryLanguage": summary.get("language"),
                "description": summary.get("description"),
                "collectedAt": facts["repository"].get("collected_at"),
                "stars": summary.get("stars"),
                "topics": summary.get("topics") or [],
                "prCount": stats.get("pr_count"),
                "fileCount": stats.get("file_count"),
                "url": facts["repository"].get("url"),
            },
            relates_to=[
                "sra:Module",
                "sra:HotFile",
                "sra:PullRequest",
                "sra:Contributor",
                "sra:MigrationProfile",
                "sra:ProjectStructure",
                "sra:DependencyGraph",
            ],
        )
    )

    mig = facts.get("migration") or {}
    mig_id = _instance_id(owner, repo, "migration", "profile")
    graph.append(
        _entity_instance(
            mig_id,
            "MigrationProfile",
            human_ref=mig.get("difficulty_estimate", "unknown"),
            description="Migration and modernization signals from BlueWings analyzer",
            attributes={
                "detectedStack": mig.get("detected_stack") or [],
                "difficultyEstimate": mig.get("difficulty_estimate", "unknown"),
                "hotFileCount": len([h for h in facts.get("hot_files", []) if h.get("risk") == "high"]),
                "totalFiles": (mig.get("complexity_signals") or {}).get("total_files"),
                "prCount": (mig.get("complexity_signals") or {}).get("pr_count"),
            },
        )
    )
    graph.append(
        _operation_instance(
            f"sra:op/{owner}/{repo}/has-migration",
            "HasMigrationProfile",
            repo_id,
            mig_id,
            "Repository migration profile from intelligence snapshot",
        )
    )

    ps = facts.get("project_structure") or {}
    struct_id = _instance_id(owner, repo, "structure", "root")
    graph.append(
        _entity_instance(
            struct_id,
            "ProjectStructure",
            human_ref=full,
            description="Directory layout and cross-module import connectivity for this repository",
            attributes={
                "totalFiles": ps.get("total_files"),
                "totalDirectories": ps.get("total_directories"),
                "collectedAt": facts["repository"].get("collected_at"),
                "treeDepth": 4,
            },
            relates_to=["sra:Repository", "sra:Directory", "sra:CodeLayer", "sra:Module"],
        )
    )
    graph.append(
        _operation_instance(
            f"sra:op/{owner}/{repo}/has-structure",
            "HasProjectStructure",
            repo_id,
            struct_id,
            "Repository project structure snapshot",
        )
    )

    layer_ids: dict[str, str] = {}
    for layer in ps.get("layers", [])[:12]:
        lname = layer.get("layer", "general")
        lid = _instance_id(owner, repo, "layer", lname)
        layer_ids[lname] = lid
        graph.append(
            _entity_instance(
                lid,
                "CodeLayer",
                human_ref=lname,
                description=layer.get("role", lname),
                attributes={
                    "layer": lname,
                    "role": layer.get("role"),
                    "fileCount": layer.get("file_count"),
                    "topDirectories": layer.get("top_directories") or [],
                },
                relates_to=["sra:ProjectStructure"],
            )
        )

    for d in ps.get("directories", [])[:35]:
        dpath = d.get("path", "")
        if not dpath:
            continue
        did = _instance_id(owner, repo, "directory", dpath)
        graph.append(
            _entity_instance(
                did,
                "Directory",
                human_ref=dpath,
                description=f"Folder `{dpath}/` in repository tree",
                attributes={
                    "path": dpath,
                    "name": d.get("name"),
                    "depth": d.get("depth"),
                    "fileCount": d.get("file_count"),
                    "subdirectoryCount": d.get("subdirectory_count"),
                    "layer": d.get("layer"),
                    "parentPath": d.get("parent_path"),
                },
                relates_to=["sra:ProjectStructure", "sra:Module"],
            )
        )
        graph.append(
            _operation_instance(
                f"sra:op/{owner}/{repo}/dir-{quote(dpath, safe='')}",
                "ContainsDirectory",
                struct_id,
                did,
                f"Structure contains directory {dpath}",
            )
        )
        layer_name = d.get("layer", "general")
        if layer_name in layer_ids:
            graph.append(
                _operation_instance(
                    f"sra:op/{owner}/{repo}/layer-{quote(dpath, safe='')}",
                    "GroupedInLayer",
                    did,
                    layer_ids[layer_name],
                    f"Directory {dpath} grouped in layer {layer_name}",
                )
            )

    module_ids: list[str] = []
    module_id_by_name: dict[str, str] = {}
    for mod in facts.get("modules", []):
        name = mod.get("name", "unknown")
        mid = _instance_id(owner, repo, "module", name)
        module_ids.append(mid)
        module_id_by_name[name] = mid
        graph.append(
            _entity_instance(
                mid,
                "Module",
                human_ref=name,
                description=f"Architectural module folder `{name}/`",
                attributes={
                    "moduleName": name,
                    "fileCount": mod.get("file_count"),
                    "sizeBytes": mod.get("size_bytes"),
                    "importance": mod.get("importance"),
                },
                relates_to=["sra:Repository"],
            )
        )
        graph.append(
            _operation_instance(
                f"sra:op/{owner}/{repo}/contains-{quote(name, safe='')}",
                "ContainsModule",
                repo_id,
                mid,
                f"Repository contains module {name}",
            )
        )

    for i, conn in enumerate((ps.get("cross_module_connections") or [])[:20]):
        fm, tm = conn.get("from_module"), conn.get("to_module")
        if not fm or not tm or fm not in module_id_by_name or tm not in module_id_by_name:
            continue
        graph.append(
            _operation_instance(
                f"sra:op/{owner}/{repo}/import-link-{i}",
                "ImportsFromModule",
                module_id_by_name[fm],
                module_id_by_name[tm],
                conn.get("description", f"{fm} imports from {tm}"),
            )
        )

    pd = facts.get("project_dependencies") or {}
    dep_graph_id = _instance_id(owner, repo, "dependency-graph", "sample")
    dep_summary = pd.get("summary") or {}
    if pd.get("available"):
        graph.append(
            _entity_instance(
                dep_graph_id,
                "DependencyGraph",
                human_ref=full,
                description="Sampled import dependency graph — which files depend on which",
                attributes={
                    "filesAnalyzed": dep_summary.get("files_analyzed"),
                    "fileToFileEdges": dep_summary.get("file_to_file_edges"),
                    "packageImportEdges": dep_summary.get("package_import_edges"),
                    "modeledFileCount": dep_summary.get("modeled_file_count"),
                    "truncated": dep_summary.get("truncated"),
                    "languages": dep_summary.get("languages"),
                },
                relates_to=["sra:Repository", "sra:SourceFile", "sra:ExternalPackage"],
            )
        )
        graph.append(
            _operation_instance(
                f"sra:op/{owner}/{repo}/has-dependency-graph",
                "HasDependencyGraph",
                repo_id,
                dep_graph_id,
                "Repository file-level import dependency snapshot",
            )
        )

    hot_ids: list[str] = []
    for hf in facts.get("hot_files", []):
        path = hf.get("path", "")
        if not path:
            continue
        hid = _instance_id(owner, repo, "hotfile", path)
        hot_ids.append(hid)
        risk = hf.get("risk", "low")
        graph.append(
            _entity_instance(
                hid,
                "HotFile",
                human_ref=path,
                description=f"High-churn file (risk: {risk})",
                attributes={
                    "path": path,
                    "prTouchCount": hf.get("pr_touch_count"),
                    "additions": hf.get("additions"),
                    "deletions": hf.get("deletions"),
                    "risk": risk,
                },
                has_state=["sra:FileRiskLow", "sra:FileRiskMedium", "sra:FileRiskHigh"],
                initial_state=_risk_state(risk),
                relates_to=["sra:Repository", "sra:PullRequest"],
            )
        )
        graph.append(
            _operation_instance(
                f"sra:op/{owner}/{repo}/hot-{quote(path, safe='')}",
                "HasHotFile",
                repo_id,
                hid,
                f"Repository tracks hot file {path}",
            )
        )

    for pr in facts.get("architectural_prs", []):
        num = pr.get("number")
        if num is None:
            continue
        pid = _instance_id(owner, repo, "pr", str(num))
        graph.append(
            _entity_instance(
                pid,
                "PullRequest",
                human_ref=str(num),
                description=pr.get("title", ""),
                attributes={
                    "number": num,
                    "title": pr.get("title"),
                    "mergedAt": pr.get("merged_at"),
                    "url": pr.get("url"),
                    "architectural": True,
                },
                relates_to=["sra:Repository"],
            )
        )

    for c in facts.get("contributors", []):
        login = c.get("login")
        if not login:
            continue
        cid = _instance_id(owner, repo, "contributor", login)
        graph.append(
            _entity_instance(
                cid,
                "Contributor",
                human_ref=login,
                description=f"Contributor @{login}",
                attributes={
                    "login": login,
                    "commits": c.get("commits"),
                    "prsAuthored": c.get("prs_authored"),
                    "profileUrl": c.get("profile"),
                },
                relates_to=["sra:Repository"],
            )
        )

    for dep in facts.get("dependency_manifests", []):
        path = dep.get("path", "")
        if not path:
            continue
        did = _instance_id(owner, repo, "manifest", path)
        graph.append(
            _entity_instance(
                did,
                "DependencyManifest",
                human_ref=path,
                description=f"Dependency manifest: {dep.get('kind', 'unknown')}",
                attributes={"path": path, "kind": dep.get("kind")},
                relates_to=["sra:Repository"],
            )
        )

    file_ids: dict[str, str] = {}
    for hub in facts.get("graph_hubs", []):
        path = hub.get("path", "")
        if not path:
            continue
        fid = _instance_id(owner, repo, "hub", path)
        file_ids[path] = fid
        graph.append(
            _entity_instance(
                fid,
                "DependencyHub",
                human_ref=path,
                description="Highly connected file in import graph sample",
                attributes={
                    "path": path,
                    "inDegree": hub.get("in_degree"),
                    "outDegree": hub.get("out_degree"),
                    "language": hub.get("language"),
                },
                relates_to=["sra:SourceFile", "sra:Repository", "sra:DependencyGraph"],
            )
        )

    for fd in (pd.get("file_dependencies") or [])[:45]:
        path = fd.get("path", "")
        if not path or path in file_ids:
            continue
        sid = _instance_id(owner, repo, "sourcefile", path)
        file_ids[path] = sid
        graph.append(
            _entity_instance(
                sid,
                "SourceFile",
                human_ref=path,
                description="Source file with recorded import relationships",
                attributes={
                    "path": path,
                    "inDegree": fd.get("in_degree_sample"),
                    "outDegree": fd.get("out_degree_sample"),
                    "importCount": len(fd.get("imports") or []),
                    "importedByCount": len(fd.get("imported_by") or []),
                },
                relates_to=["sra:Repository", "sra:DependencyGraph"],
            )
        )
        if pd.get("available"):
            graph.append(
                _operation_instance(
                    f"sra:op/{owner}/{repo}/in-graph-{quote(path, safe='')}",
                    "ContainedInDependencyGraph",
                    dep_graph_id,
                    sid,
                    f"Dependency graph includes file {path}",
                )
            )

    for pkg in (pd.get("external_packages") or [])[:25]:
        name = pkg.get("package", "")
        if not name:
            continue
        pid = _instance_id(owner, repo, "package", name)
        graph.append(
            _entity_instance(
                pid,
                "ExternalPackage",
                human_ref=name,
                description=f"External package imported from sampled files",
                attributes={
                    "packageName": name,
                    "importCount": pkg.get("import_count"),
                },
                relates_to=["sra:DependencyGraph", "sra:Repository"],
            )
        )
        if pd.get("available"):
            graph.append(
                _operation_instance(
                    f"sra:op/{owner}/{repo}/pkg-{quote(name, safe='')}",
                    "DependsOnPackage",
                    dep_graph_id,
                    pid,
                    f"Repository sample imports package {name}",
                )
            )

    seen_edges: set[tuple[str, str]] = set()
    edge_ops = 0

    def _add_import_edge(src: str, tgt: str, desc: str) -> None:
        nonlocal edge_ops
        if not src or not tgt or src == tgt:
            return
        key = (src, tgt)
        if key in seen_edges:
            return
        if src not in file_ids:
            file_ids[src] = _instance_id(owner, repo, "sourcefile", src)
            graph.append(
                _entity_instance(
                    file_ids[src],
                    "SourceFile",
                    human_ref=src,
                    description="Source file in dependency sample",
                    attributes={"path": src},
                    relates_to=["sra:DependencyGraph"],
                )
            )
        if tgt not in file_ids:
            file_ids[tgt] = _instance_id(owner, repo, "sourcefile", tgt)
            graph.append(
                _entity_instance(
                    file_ids[tgt],
                    "SourceFile",
                    human_ref=tgt,
                    description="Source file in dependency sample",
                    attributes={"path": tgt},
                    relates_to=["sra:DependencyGraph"],
                )
            )
        seen_edges.add(key)
        graph.append(
            _operation_instance(
                f"sra:op/{owner}/{repo}/imports-{edge_ops}",
                "ImportsFile",
                file_ids[src],
                file_ids[tgt],
                desc,
            )
        )
        edge_ops += 1

    for edge in facts.get("graph_hub_edges", []):
        if edge_ops >= 120:
            break
        src, tgt = edge.get("source"), edge.get("target")
        _add_import_edge(src, tgt, f"{src} imports {tgt}")

    for edge in (pd.get("file_edges") or []):
        if edge_ops >= 120:
            break
        src, tgt = edge.get("source"), edge.get("target")
        _add_import_edge(src, tgt, f"{src} imports {tgt} ({edge.get('kind', 'import')})")

    return {"@context": SRA_CONTEXT, "@graph": graph}


def validate_jsonld_document(doc: dict[str, Any]) -> list[str]:
    """Basic validation before Context Studio import."""
    errors: list[str] = []
    if "@context" not in doc:
        errors.append("Missing @context")
    if "@graph" not in doc or not isinstance(doc.get("@graph"), list):
        errors.append("Missing or invalid @graph")
    else:
        for i, node in enumerate(doc["@graph"]):
            if "id" not in node:
                errors.append(f"@graph[{i}]: missing id")
            if "type" not in node:
                errors.append(f"@graph[{i}]: missing type")
    try:
        json.dumps(doc)
    except (TypeError, ValueError) as e:
        errors.append(f"Not JSON-serializable: {e}")
    return errors


def load_schema_jsonld() -> dict[str, Any]:
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        return json.load(f)


def build_manifest(facts: dict[str, Any], *, llm_docs: bool, validation_errors: list[str]) -> dict[str, Any]:
    full = facts["repository"]["full_name"]
    safe = re.sub(r"[^\w.-]+", "-", full)
    return {
        "schema_version": SCHEMA_VERSION,
        "bluewings_export": "context-studio",
        "repository": full,
        "collected_at": facts["repository"].get("collected_at"),
        "default_branch": facts["repository"].get("default_branch"),
        "suggested_context_name": f"BlueWings — {full}",
        "suggested_context_description": (
            f"Repository intelligence snapshot for {full}. "
            "Import schema once globally; use this bundle's instance JSON-LD and docs per repo."
        ),
        "files": {
            "schema": f"schema/{SCHEMA_FILENAME}",
            "instances": f"instances/{safe}-instances.jsonld",
            "facts": f"data/{safe}-facts.json",
            "docs": [
                "docs/01-project-overview.md",
                "docs/02-architecture.md",
                "docs/07-project-structure.md",
                "docs/08-file-dependencies.md",
                "docs/03-onboarding.md",
                "docs/04-risks-and-churn.md",
                "docs/05-migration.md",
                "docs/06-agent-instructions.md",
            ],
            "structure": f"structure/{safe}-project-structure.json",
            "dependencies": f"dependencies/{safe}-file-dependencies.json",
        },
        "context_studio_steps": [
            "Import schema/software-repository-archaeology-schema.jsonld once (New Schema → Import json-ld).",
            "Publish the schema.",
            f"Create New Context named '{full}' and link the published schema.",
            "Upload all docs/*.md to Source & Data — especially 07-project-structure.md (layout) and 08-file-dependencies.md (how files import each other).",
            "Optional: upload structure/*, dependencies/*, and data/*-facts.json for extra grounding.",
            "Add business rules: high-risk HotFile changes require architecture review; check ImportsFile edges before editing hub files.",
            "Expose Context Studio MCP; register BlueWings GitHub MCP in Context Forge.",
            "Use ctx ID with Bob/ICA plus get_change_impact for live blast radius.",
        ],
        "llm_generated_docs": llm_docs,
        "validation_errors": validation_errors,
        "graph_truncated": (facts.get("graph_meta") or {}).get("truncated"),
    }


def build_markdown_docs_deterministic(facts: dict[str, Any]) -> dict[str, str]:
    """Grounded markdown — no LLM required."""
    full = facts["repository"]["full_name"]
    summary = facts.get("summary", {})
    onboarding = facts.get("onboarding", {})
    mig = facts.get("migration", {})

    overview = [
        f"# Project overview — {full}",
        "",
        f"**Collected at:** {facts['repository'].get('collected_at', 'unknown')}",
        f"**Default branch:** {facts['repository'].get('default_branch', 'main')}",
        f"**URL:** {facts['repository'].get('url', '')}",
        "",
        "## Summary",
        "",
        summary.get("description") or "_No description in GitHub metadata._",
        "",
        f"- **Primary language:** {summary.get('language', 'unknown')}",
        f"- **Stars:** {summary.get('stars', 'n/a')}",
        f"- **Topics:** {', '.join(summary.get('topics') or []) or 'none'}",
        "",
    ]
    if facts.get("readme_excerpt"):
        overview.extend(["## README excerpt", "", facts["readme_excerpt"], ""])

    arch_lines = [
        f"# Architecture — {full}",
        "",
        "## Modules (top-level)",
        "",
    ]
    for m in facts.get("modules", []):
        arch_lines.append(
            f"- **{m.get('name')}/** — {m.get('file_count')} files, "
            f"importance: {m.get('importance')}"
        )
    arch_lines.extend([
        "",
        "## Entry point candidates",
        "",
    ])
    for p in facts.get("entry_candidates", []):
        arch_lines.append(f"- `{p}`")
    arch_lines.extend([
        "",
        "## Standalone service candidates",
        "",
        ", ".join(facts.get("standalone_service_candidates") or []) or "_None detected._",
        "",
        "## How top-level areas connect (import graph)",
        "",
    ])
    ps = facts.get("project_structure") or {}
    for conn in ps.get("cross_module_connections", [])[:12]:
        arch_lines.append(f"- {conn.get('description', '')}")
    if not ps.get("cross_module_connections"):
        arch_lines.append("_No cross-module import edges in sample._")
    pd = facts.get("project_dependencies") or {}
    if pd.get("available"):
        arch_lines.extend([
            "",
            "## File dependencies (sample)",
            "",
            f"- **{pd.get('summary', {}).get('file_to_file_edges', 0)}** file-to-file import edges in analysis",
            f"- **{pd.get('summary', {}).get('modeled_file_count', 0)}** files with import/imported-by lists in context",
            "",
            "See `08-file-dependencies.md` for hubs, edges, and per-file lists.",
            "",
        ])
    arch_lines.extend([
        "",
        "## Dependency graph hubs (sampled)",
        "",
    ])
    for h in facts.get("graph_hubs", []):
        arch_lines.append(
            f"- `{h.get('path')}` — in-degree {h.get('in_degree')}, "
            f"out-degree {h.get('out_degree')}"
        )
    gm = facts.get("graph_meta") or {}
    if gm.get("truncated"):
        arch_lines.append(
            "\n_Graph was truncated. Use BlueWings MCP `get_repository_dependency_graph` for full analysis._"
        )

    onboard = [
        f"# Onboarding — {full}",
        "",
        "## Start here",
        "",
    ]
    for s in onboarding.get("start_here", []):
        onboard.append(f"- {s}")
    onboard.extend(["", "## Read next", ""])
    for p in onboarding.get("read_next", []):
        onboard.append(f"- `{p}`")
    onboard.extend([
        "",
        "## Suggested questions for agents",
        "",
    ])
    for q in onboarding.get("suggested_questions", []):
        onboard.append(f"- {q}")

    risks = [
        f"# Risks and churn — {full}",
        "",
        "## Hot files (sampled PR history)",
        "",
        "| Path | PR touches | Risk |",
        "|------|------------|------|",
    ]
    for hf in facts.get("hot_files", []):
        risks.append(
            f"| `{hf.get('path')}` | {hf.get('pr_touch_count')} | {hf.get('risk')} |"
        )
    risks.extend(["", "## Technical debt signals", ""])
    for t in facts.get("technical_debt", []):
        risks.append(f"- {t}")
    risks.extend(["", "## Architectural pull requests", ""])
    for pr in facts.get("architectural_prs", []):
        risks.append(f"- #{pr.get('number')} — {pr.get('title')} ({pr.get('url', '')})")

    migration = [
        f"# Migration — {full}",
        "",
        f"**Difficulty estimate:** {mig.get('difficulty_estimate', 'unknown')}",
        "",
        "## Detected stack",
        "",
        ", ".join(mig.get("detected_stack") or []) or "unknown",
        "",
        "## Dependency manifests",
        "",
    ]
    for d in facts.get("dependency_manifests", []):
        migration.append(f"- `{d.get('path')}` ({d.get('kind')})")
    migration.extend(["", "## Rewrite strategy outline", ""])
    for s in mig.get("rewrite_strategy_outline", []):
        migration.append(f"1. {s}")

    structure_doc = _build_project_structure_markdown(full, facts)
    dependencies_doc = _build_file_dependencies_markdown(full, facts)

    agent = [
        f"# Agent instructions — {full}",
        "",
        "This context was generated by **BlueWings** for IBM ICA Context Studio.",
        "",
        "## Grounding rules",
        "",
        "- Prefer facts in `data/*-facts.json`, `structure/*`, `dependencies/*`, and instance JSON-LD.",
        "- Use `07-project-structure.md` for folder layout; `08-file-dependencies.md` for file-to-file imports and blast radius.",
        "- If data is missing, say unknown — do not invent file paths or PR numbers.",
        "- Snapshot date: "
        f"{facts['repository'].get('collected_at')}. For live GitHub data, use BlueWings MCP tools.",
        "",
        "## Recommended MCP tools (BlueWings GitHub MCP)",
        "",
        f"- `get_repo_info` — owner `{facts['repository']['owner']}`, repo `{facts['repository']['repo']}`",
        "- `get_repository_dependency_graph` — full or sampled import graph",
        "- `get_file_dependency_subgraph` — BFS from one file",
        "- `get_change_impact` — blast radius before editing a file",
        "- `list_pull_requests` / `get_pull_request_detail` — verify history",
        "",
        "## Example prompts",
        "",
        f"- What is the blast radius of editing `{(facts.get('hot_files') or [{}])[0].get('path', 'src/...')}`?",
        "- Which architectural PRs changed this codebase?",
        "- Where should a new developer start in this repository?",
        "- Which top-level folder should I change for a feature in the API layer?",
        "- How does `src/` (or the main app folder) connect to other modules?",
        "",
    ]

    return {
        "docs/01-project-overview.md": "\n".join(overview),
        "docs/02-architecture.md": "\n".join(arch_lines),
        "docs/07-project-structure.md": structure_doc,
        "docs/08-file-dependencies.md": dependencies_doc,
        "docs/03-onboarding.md": "\n".join(onboard),
        "docs/04-risks-and-churn.md": "\n".join(risks),
        "docs/05-migration.md": "\n".join(migration),
        "docs/06-agent-instructions.md": "\n".join(agent),
    }


def _build_project_structure_markdown(full: str, facts: dict[str, Any]) -> str:
    """Dedicated Context Studio doc: directory tree + layers + connectivity."""
    ps = facts.get("project_structure") or {}
    lines = [
        f"# Project structure — {full}",
        "",
        "This document describes **where code lives** and **how top-level areas connect** via imports.",
        "Use it with the published **Software Repository Archaeology** schema (`ProjectStructure`, `Directory`, `CodeLayer`, `ModuleConnection`).",
        "",
        f"- **Total files (tree):** {ps.get('total_files', 'unknown')}",
        f"- **Directories modeled:** {ps.get('total_directories', 'unknown')}",
        "",
        "## Directory tree (top levels)",
        "",
    ]
    tree_lines = ps.get("directory_tree_markdown") or []
    if tree_lines:
        lines.extend(tree_lines)
    else:
        lines.append("_Tree unavailable._")
    lines.extend(["", "## Code layers", ""])
    for layer in ps.get("layers", []):
        dirs = ", ".join(f"`{d}/`" for d in (layer.get("top_directories") or [])[:6])
        lines.append(
            f"- **{layer.get('layer')}** ({layer.get('role')}): {layer.get('file_count', 0)} files — {dirs or 'n/a'}"
        )
    lines.extend(["", "## Top-level modules (file counts)", ""])
    for m in ps.get("modules_alignment", []):
        lines.append(
            f"- `{m.get('module')}/` — {m.get('file_count')} files, importance: {m.get('importance')}"
        )
    lines.extend([
        "",
        "## How areas connect (sampled import graph)",
        "",
        "These edges mean one top-level folder imports code from another:",
        "",
    ])
    for conn in ps.get("cross_module_connections", []):
        lines.append(f"- {conn.get('description')}")
    if not ps.get("cross_module_connections"):
        lines.append("_No cross-folder imports in dependency sample._")
    lines.extend(["", "## File types", ""])
    for ext in ps.get("extension_breakdown", [])[:10]:
        lines.append(f"- `{ext.get('extension')}`: {ext.get('count')} files")
    gm = facts.get("graph_meta") or {}
    if gm.get("truncated"):
        lines.append(
            "\n_Dependency graph truncated. Use BlueWings `get_repository_dependency_graph` for full connectivity._"
        )
    lines.extend([
        "",
        "## Schema instances",
        "",
        "The ZIP `instances/*.jsonld` includes `ProjectStructure`, `Directory`, `CodeLayer`, and `ImportsFromModule` operations linking modules.",
        "",
    ])
    return "\n".join(lines)


def _build_file_dependencies_markdown(full: str, facts: dict[str, Any]) -> str:
    """Context Studio doc: file-level import graph for agents."""
    pd = facts.get("project_dependencies") or {}
    lines = [
        f"# File dependencies — {full}",
        "",
        "How **source files depend on each other** via imports (sampled from BlueWings dependency graph).",
        "Use with schema types `DependencyGraph`, `SourceFile`, `ImportsFile`, `DependencyHub`, `ExternalPackage`.",
        "",
    ]
    if not pd.get("available"):
        lines.extend([
            "_Dependency graph not included in this export. Re-export with **Include dependency graph** enabled._",
            "",
        ])
        return "\n".join(lines)

    summary = pd.get("summary") or {}
    lines.extend([
        f"- **Files analyzed:** {summary.get('files_analyzed', 'unknown')}",
        f"- **File-to-file import edges:** {summary.get('file_to_file_edges', 'unknown')}",
        f"- **Files modeled in context:** {summary.get('modeled_file_count', 'unknown')}",
        f"- **External package imports:** {summary.get('package_import_edges', 'unknown')}",
    ])
    if summary.get("truncated"):
        lines.append("- **Note:** Graph was truncated — use BlueWings MCP for full analysis.")
    lines.extend(["", "## Highly connected files (hubs)", ""])
    for h in pd.get("hubs", [])[:12]:
        lines.append(
            f"- `{h.get('path')}` — imported by **{h.get('in_degree')}** files, "
            f"imports **{h.get('out_degree')}** others"
        )
    lines.extend([
        "",
        "## Sample import edges (file → file)",
        "",
        "| Source | Target | Kind |",
        "|--------|--------|------|",
    ])
    for e in (pd.get("file_edges") or [])[:25]:
        lines.append(f"| `{e.get('source')}` | `{e.get('target')}` | {e.get('kind', 'import')} |")
    lines.extend(["", "## Per-file dependency lists (selected files)", ""])
    for fd in (pd.get("file_dependencies") or [])[:15]:
        path = fd.get("path", "")
        imports = fd.get("imports") or []
        imported_by = fd.get("imported_by") or []
        lines.append(f"### `{path}`")
        lines.append("")
        if imports:
            lines.append("**Imports:** " + ", ".join(f"`{x.get('path')}`" for x in imports[:8]))
        else:
            lines.append("**Imports:** _none in sample_")
        lines.append("")
        if imported_by:
            lines.append("**Imported by:** " + ", ".join(f"`{x.get('path')}`" for x in imported_by[:8]))
        else:
            lines.append("**Imported by:** _none in sample_")
        lines.append("")
    lines.extend(["", "## External packages (top)", ""])
    for pkg in (pd.get("external_packages") or [])[:15]:
        lines.append(f"- **{pkg.get('package')}** — {pkg.get('import_count')} import statements")
    lines.extend([
        "",
        "## JSON artifacts",
        "",
        "- `dependencies/*-file-dependencies.json` — machine-readable dependency summary",
        "- Instance JSON-LD includes `ImportsFile` operations between `SourceFile` nodes",
        "",
    ])
    return "\n".join(lines)


CONTEXT_DOCS_SYSTEM = """You write markdown documentation for IBM ICA Context Studio.
Use ONLY the facts JSON provided. Do not invent file paths, PR numbers, contributors, or statistics.
If a fact is missing, write "Unknown" for that section.
Output valid markdown with clear headings. Be concise and actionable."""


async def enhance_markdown_with_llm(
    facts: dict[str, Any],
    base_docs: dict[str, str],
) -> dict[str, str]:
    """Optional LLM polish — one doc at a time, facts-grounded."""
    from grok_agent import run_completion

    blob = json.dumps(facts, indent=2, default=str)
    if len(blob) > 14000:
        blob = blob[:14000] + "\n… (truncated)"

    out = dict(base_docs)
    for path, content in base_docs.items():
        prompt = (
            f"Improve this Context Studio document for `{path}`.\n"
            f"Keep all factual claims aligned with the facts JSON.\n"
            f"Do not add new file paths or PRs not in facts.\n\n"
            f"## Facts JSON\n```json\n{blob}\n```\n\n"
            f"## Current document\n{content}"
        )
        try:
            enhanced = await run_completion(
                [
                    {"role": "system", "content": CONTEXT_DOCS_SYSTEM},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
            )
            if enhanced and len(enhanced.strip()) > 200:
                out[path] = enhanced.strip()
        except Exception:
            pass
    return out


@dataclass
class ContextExportOptions:
    ref: str = ""
    include_graph: bool = True
    graph_max_files: int = 300
    llm_enhance_docs: bool = False
    pr_file_sample: int = 25
    cached_insights: dict[str, Any] | None = None
    build_zip: bool = True


def build_facts_summary(facts: dict[str, Any]) -> dict[str, Any]:
    """Lightweight summary for preview UI."""
    mig = facts.get("migration") or {}
    ps = facts.get("project_structure") or {}
    pd = facts.get("project_dependencies") or {}
    dep_summary = pd.get("summary") or {}
    return {
        "repository": facts["repository"]["full_name"],
        "collected_at": facts["repository"].get("collected_at"),
        "default_branch": facts["repository"].get("default_branch"),
        "language": (facts.get("summary") or {}).get("language"),
        "module_count": len(facts.get("modules") or []),
        "hot_file_count": len(facts.get("hot_files") or []),
        "arch_pr_count": len(facts.get("architectural_prs") or []),
        "graph_hub_count": len(facts.get("graph_hubs") or []),
        "migration_difficulty": mig.get("difficulty_estimate"),
        "detected_stack": mig.get("detected_stack") or [],
        "graph_truncated": (facts.get("graph_meta") or {}).get("truncated"),
        "total_files": ps.get("total_files"),
        "total_directories": ps.get("total_directories"),
        "cross_module_links": len(ps.get("cross_module_connections") or []),
        "code_layers": len(ps.get("layers") or []),
        "dependencies_available": pd.get("available", False),
        "file_dependency_edges": dep_summary.get("file_to_file_edges"),
        "modeled_source_files": dep_summary.get("modeled_file_count"),
        "sampled_import_edges": len(pd.get("file_edges") or []),
        "external_package_count": len(pd.get("external_packages") or []),
    }


def build_preview_response(
    *,
    manifest: dict[str, Any],
    facts: dict[str, Any],
    instances: dict[str, Any],
    validation_errors: list[str],
) -> dict[str, Any]:
    """JSON preview for Context Studio UI before ZIP download."""
    return {
        "manifest": manifest,
        "facts_summary": build_facts_summary(facts),
        "instance_count": len(instances.get("@graph", [])),
        "documents": [
            {"path": p, "title": p.replace("docs/", "").replace(".md", "").replace("-", " ")}
            for p in manifest.get("files", {}).get("docs", [])
        ],
        "import_checklist": manifest.get("context_studio_steps", []),
        "suggested_context_name": manifest.get("suggested_context_name"),
        "validation_errors": validation_errors,
        "bundle_files": list(manifest.get("files", {}).values())
        if isinstance(manifest.get("files"), dict)
        else [],
    }


@dataclass
class ContextExportResult:
    zip_bytes: bytes
    manifest: dict[str, Any]
    facts: dict[str, Any]
    instances: dict[str, Any] = field(default_factory=dict)
    validation_errors: list[str] = field(default_factory=list)


async def _load_snapshot_and_insights(
    owner: str,
    repo: str,
    opts: ContextExportOptions,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if opts.cached_insights:
        insights = opts.cached_insights
        summary = insights.get("summary") or {}
        readme, tree = await asyncio.gather(
            gh.get_readme(owner, repo),
            gh.get_repo_file_tree(owner, repo, max_files=2000),
        )
        snapshot = {
            "owner": owner,
            "repo": repo,
            "collected_at": insights.get("collected_at"),
            "file_tree": tree,
            "info": {
                "default_branch": "main",
                "description": summary.get("description"),
                "language": summary.get("language"),
                "name": summary.get("name"),
                "stars": summary.get("stars"),
                "topics": summary.get("topics", []),
                "url": f"https://github.com/{owner}/{repo}",
            },
            "readme": readme,
        }
        return snapshot, insights

    snapshot = await collect_repository_snapshot(owner, repo, pr_file_sample=opts.pr_file_sample)
    return snapshot, analyze_snapshot(snapshot)


async def build_context_studio_payload(
    owner: str,
    repo: str,
    options: ContextExportOptions | None = None,
) -> ContextExportResult:
    """Collect/analyze → JSON-LD + docs; optionally build ZIP."""
    opts = options or ContextExportOptions()
    snapshot, insights = await _load_snapshot_and_insights(owner, repo, opts)

    graph: dict[str, Any] | None = None
    if opts.include_graph:
        from dependency_graph.builder import build_dependency_graph

        graph = await build_dependency_graph(
            owner,
            repo,
            ref=opts.ref or None,
            max_files=max(50, min(opts.graph_max_files, 600)),
            include_packages=True,
        )

    facts = build_facts_pack(owner, repo, snapshot, insights, graph=graph)
    instances = build_instances_jsonld(facts)
    errors = validate_jsonld_document(instances)
    schema = load_schema_jsonld()
    errors.extend(validate_jsonld_document(schema))

    docs = build_markdown_docs_deterministic(facts)
    if opts.llm_enhance_docs:
        docs = await enhance_markdown_with_llm(facts, docs)

    manifest = build_manifest(facts, llm_docs=opts.llm_enhance_docs, validation_errors=errors)
    zip_bytes = b""
    if opts.build_zip:
        zip_bytes = build_zip_archive(
            schema=schema,
            instances=instances,
            facts=facts,
            docs=docs,
            manifest=manifest,
            owner=owner,
            repo=repo,
        )

    return ContextExportResult(
        zip_bytes=zip_bytes,
        manifest=manifest,
        facts=facts,
        instances=instances,
        validation_errors=errors,
    )


async def export_context_studio_bundle(
    owner: str,
    repo: str,
    options: ContextExportOptions | None = None,
) -> ContextExportResult:
    """Full pipeline with ZIP artifact."""
    opts = options or ContextExportOptions()
    opts.build_zip = True
    return await build_context_studio_payload(owner, repo, opts)


async def export_context_studio_preview(
    owner: str,
    repo: str,
    options: ContextExportOptions | None = None,
) -> dict[str, Any]:
    """Same pipeline without ZIP — returns preview JSON for UI."""
    opts = options or ContextExportOptions(build_zip=False)
    opts.build_zip = False
    result = await build_context_studio_payload(owner, repo, opts)
    return build_preview_response(
        manifest=result.manifest,
        facts=result.facts,
        instances=result.instances,
        validation_errors=result.validation_errors,
    )


def build_zip_archive(
    *,
    schema: dict[str, Any],
    instances: dict[str, Any],
    facts: dict[str, Any],
    docs: dict[str, str],
    manifest: dict[str, Any],
    owner: str,
    repo: str,
) -> bytes:
    full = f"{owner}/{repo}"
    safe = re.sub(r"[^\w.-]+", "-", full)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"schema/{SCHEMA_FILENAME}", json.dumps(schema, indent=2))
        zf.writestr(
            f"instances/{safe}-instances.jsonld",
            json.dumps(instances, indent=2),
        )
        zf.writestr(f"data/{safe}-facts.json", json.dumps(facts, indent=2))
        zf.writestr(
            f"structure/{safe}-project-structure.json",
            json.dumps(facts.get("project_structure") or {}, indent=2),
        )
        zf.writestr(
            f"dependencies/{safe}-file-dependencies.json",
            json.dumps(facts.get("project_dependencies") or {}, indent=2),
        )
        zf.writestr("manifest.json", json.dumps(manifest, indent=2))
        zf.writestr("README.txt", _bundle_readme(full, manifest))
        for path, content in docs.items():
            zf.writestr(path, content)
    return buf.getvalue()


def _bundle_readme(full: str, manifest: dict[str, Any]) -> str:
    lines = [
        f"BlueWings Context Studio Export — {full}",
        f"Schema version: {SCHEMA_VERSION}",
        "",
        "Import order:",
    ]
    for step in manifest.get("context_studio_steps", []):
        lines.append(f"  - {step}")
    lines.extend(["", "See manifest.json for file paths and metadata.", ""])
    return "\n".join(lines)
