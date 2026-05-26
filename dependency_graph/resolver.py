"""
Resolve import specifiers to repository file paths or external package nodes.
"""

from __future__ import annotations

from pathlib import PurePosixPath

from dependency_graph.constants import ANALYZABLE_EXTENSIONS

INDEX_FILES = ("index.ts", "index.tsx", "index.js", "index.jsx", "mod.rs", "__init__.py")


def should_skip_path(path: str, skip_dirs: frozenset[str]) -> bool:
    parts = path.replace("\\", "/").split("/")
    return any(p in skip_dirs for p in parts)


def is_analyzable_path(path: str) -> bool:
    return PurePosixPath(path).suffix.lower() in ANALYZABLE_EXTENSIONS


def build_path_index(file_paths: list[str]) -> dict[str, str]:
    """Map normalized keys (path, stem, posix path) to canonical repo path."""
    index: dict[str, str] = {}
    for path in file_paths:
        p = PurePosixPath(path)
        index[path] = path
        index[path.lower()] = path
        stem = p.stem
        if stem:
            index[stem] = path
            index[stem.lower()] = path
        parent = str(p.parent)
        if parent and parent != ".":
            index[f"{parent}/{stem}"] = path
            index[f"{parent}/{stem}".lower()] = path
    return index


def _try_resolve_file(
    candidate: str,
    file_set: frozenset[str],
    path_index: dict[str, str],
) -> str | None:
    if candidate in file_set:
        return candidate
    low = candidate.lower()
    if low in path_index:
        return path_index[low]
    base = PurePosixPath(candidate)
    for ext in ANALYZABLE_EXTENSIONS:
        with_ext = f"{candidate}{ext}" if not str(base).endswith(ext) else candidate
        if with_ext in file_set:
            return with_ext
        if with_ext.lower() in path_index:
            return path_index[with_ext.lower()]
    parent = str(base.parent)
    stem = base.stem or base.name
    if parent and parent != ".":
        for name in INDEX_FILES:
            idx = f"{parent}/{name}"
            if idx in file_set:
                return idx
    return None


def resolve_specifier(
    source_path: str,
    specifier: str,
    *,
    file_set: frozenset[str],
    path_index: dict[str, str],
    path_aliases: dict[str, str] | None = None,
) -> tuple[str | None, str]:
    """
    Returns (resolved_path_or_package_id, edge_kind).
    edge_kind is 'internal' or 'package'.
    """
    spec = specifier.strip()
    if not spec or spec.startswith("http://") or spec.startswith("https://"):
        return None, "package"

    aliases = path_aliases or {}

    # Path alias (@/, ~/, etc.)
    for prefix, base in aliases.items():
        if spec == prefix or spec.startswith(prefix):
            rest = spec[len(prefix) :].lstrip("/")
            target = f"{base}/{rest}" if rest else base
            hit = _try_resolve_file(target, file_set, path_index)
            if hit:
                return hit, "internal"
            break

    # Relative import
    if spec.startswith("./") or spec.startswith("../"):
        source_dir = PurePosixPath(source_path).parent
        joined = str((source_dir / spec).as_posix())
        normalized = PurePosixPath(joined).as_posix()
        hit = _try_resolve_file(normalized, file_set, path_index)
        if hit:
            return hit, "internal"
        # Try without extension variations
        for ext in ANALYZABLE_EXTENSIONS:
            hit = _try_resolve_file(f"{normalized}{ext}", file_set, path_index)
            if hit:
                return hit, "internal"
        return None, "package"

    # Absolute path from repo root (/src/...)
    if spec.startswith("/"):
        hit = _try_resolve_file(spec.lstrip("/"), file_set, path_index)
        if hit:
            return hit, "internal"

    # Python: module.path -> path/to/module.py or package/__init__.py
    if "." in spec and "/" not in spec and not spec.startswith("@") and not spec.startswith("."):
        py_path = spec.replace(".", "/")
        for candidate in (f"{py_path}.py", f"{py_path}/__init__.py"):
            hit = _try_resolve_file(candidate, file_set, path_index)
            if hit:
                return hit, "internal"

    # Bare specifier: try as repo-relative path
    hit = _try_resolve_file(spec, file_set, path_index)
    if hit:
        return hit, "internal"

    # Same-folder / src-relative heuristics
    stem = PurePosixPath(spec).stem
    parent = str(PurePosixPath(source_path).parent)
    for candidate in (
        f"{parent}/{spec}",
        f"src/{spec}",
        f"lib/{spec}",
        f"app/{spec}",
    ):
        hit = _try_resolve_file(candidate, file_set, path_index)
        if hit:
            return hit, "internal"
    if stem in path_index:
        return path_index[stem], "internal"

    return f"pkg:{spec.split('/')[0]}", "package"


def detect_path_aliases(file_paths: list[str]) -> dict[str, str]:
    """Infer common TS/JS path aliases from tsconfig/jsconfig if present in tree."""
    aliases: dict[str, str] = {}
    for path in file_paths:
        name = PurePosixPath(path).name
        if name not in ("tsconfig.json", "jsconfig.json"):
            continue
        # Heuristic defaults when configs aren't fetched
        if "src/" in "/".join(file_paths[:50]):
            aliases["@/"] = "src"
            aliases["~/"] = "src"
    if any(p.startswith("frontend/src/") for p in file_paths):
        aliases["@/"] = aliases.get("@/", "frontend/src")
    return aliases


def build_file_tree(paths: list[str]) -> dict:
    """Nested directory tree for JSON export."""
    root: dict = {"type": "directory", "name": "", "path": "", "children": []}
    dir_map: dict[str, dict] = {"": root}

    for path in sorted(paths):
        parts = path.split("/")
        acc = ""
        for i, part in enumerate(parts):
            is_file = i == len(parts) - 1
            parent_path = acc
            acc = f"{acc}/{part}" if acc else part
            if is_file:
                parent = dir_map[parent_path]
                parent.setdefault("children", []).append({
                    "type": "file",
                    "name": part,
                    "path": path,
                })
            else:
                if acc not in dir_map:
                    node = {"type": "directory", "name": part, "path": acc, "children": []}
                    dir_map[acc] = node
                    dir_map[parent_path].setdefault("children", []).append(node)

    def sort_children(node: dict) -> None:
        children = node.get("children")
        if not children:
            return
        children.sort(key=lambda c: (c["type"] != "directory", c["name"].lower()))
        for ch in children:
            if ch["type"] == "directory":
                sort_children(ch)

    sort_children(root)
    return root
