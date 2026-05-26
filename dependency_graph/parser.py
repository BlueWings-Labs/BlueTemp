"""
Extract import edges from source file contents (regex-based, language-aware).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import PurePosixPath

from dependency_graph.constants import LANGUAGE_BY_EXT


@dataclass(frozen=True)
class ImportRef:
    specifier: str
    kind: str  # import | require | dynamic | package


# ── JavaScript / TypeScript ───────────────────────────────────────────────────

_RE_ESM_FROM = re.compile(
    r"""(?:^|\n)\s*import\s+(?:type\s+)?(?:[\w*{}\s,]+\s+from\s+)?['"]([^'"]+)['"]""",
    re.MULTILINE,
)
_RE_ESM_SIDE = re.compile(r"""(?:^|\n)\s*import\s+['"]([^'"]+)['"]""", re.MULTILINE)
_RE_EXPORT_FROM = re.compile(
    r"""(?:^|\n)\s*export\s+(?:type\s+)?(?:\*|\{[^}]*\})\s+from\s+['"]([^'"]+)['"]""",
    re.MULTILINE,
)
_RE_REQUIRE = re.compile(r"""require\s*\(\s*['"]([^'"]+)['"]\s*\)""")
_RE_DYNAMIC = re.compile(r"""import\s*\(\s*['"]([^'"]+)['"]\s*\)""")


def _parse_js(content: str) -> list[ImportRef]:
    refs: list[ImportRef] = []
    seen: set[tuple[str, str]] = set()

    def add(spec: str, kind: str) -> None:
        spec = spec.strip()
        if not spec or spec.startswith("node:"):
            return
        key = (spec, kind)
        if key in seen:
            return
        seen.add(key)
        refs.append(ImportRef(spec, kind))

    for m in _RE_ESM_FROM.finditer(content):
        add(m.group(1), "import")
    for m in _RE_ESM_SIDE.finditer(content):
        add(m.group(1), "import")
    for m in _RE_EXPORT_FROM.finditer(content):
        add(m.group(1), "import")
    for m in _RE_REQUIRE.finditer(content):
        add(m.group(1), "require")
    for m in _RE_DYNAMIC.finditer(content):
        add(m.group(1), "dynamic")
    return refs


# ── Python ────────────────────────────────────────────────────────────────────

_RE_PY_IMPORT = re.compile(r"""^\s*import\s+([\w.]+)""", re.MULTILINE)
_RE_PY_FROM = re.compile(r"""^\s*from\s+([\w.]+)\s+import""", re.MULTILINE)


def _parse_python(content: str) -> list[ImportRef]:
    refs: list[ImportRef] = []
    seen: set[str] = set()
    for pat in (_RE_PY_IMPORT, _RE_PY_FROM):
        for m in pat.finditer(content):
            spec = m.group(1).strip()
            if spec in seen:
                continue
            seen.add(spec)
            refs.append(ImportRef(spec, "import"))
    return refs


# ── Go ────────────────────────────────────────────────────────────────────────

_RE_GO_IMPORT = re.compile(r'''import\s+(?:\(\s*([\s\S]*?)\s*\)|"([^"]+)")''')


def _parse_go(content: str) -> list[ImportRef]:
    refs: list[ImportRef] = []
    seen: set[str] = set()
    for m in _RE_GO_IMPORT.finditer(content):
        block = m.group(1)
        single = m.group(2)
        specs: list[str] = []
        if single:
            specs.append(single)
        elif block:
            specs.extend(re.findall(r'"([^"]+)"', block))
        for spec in specs:
            if spec in seen:
                continue
            seen.add(spec)
            refs.append(ImportRef(spec, "import"))
    return refs


# ── Rust ──────────────────────────────────────────────────────────────────────

_RE_RUST_USE = re.compile(r"""^\s*use\s+([\w:]+)""", re.MULTILINE)
_RE_RUST_MOD = re.compile(r"""^\s*mod\s+([\w_]+)""", re.MULTILINE)


def _parse_rust(content: str) -> list[ImportRef]:
    refs: list[ImportRef] = []
    seen: set[str] = set()
    for pat in (_RE_RUST_USE, _RE_RUST_MOD):
        for m in pat.finditer(content):
            spec = m.group(1).strip()
            if spec in seen:
                continue
            seen.add(spec)
            refs.append(ImportRef(spec, "import"))
    return refs


# ── Vue / Svelte (script blocks) ──────────────────────────────────────────────

_RE_SCRIPT = re.compile(r"<script[^>]*>([\s\S]*?)</script>", re.IGNORECASE)


def _parse_vue_svelte(content: str) -> list[ImportRef]:
    refs: list[ImportRef] = []
    for m in _RE_SCRIPT.finditer(content):
        refs.extend(_parse_js(m.group(1)))
    return refs


def parse_imports(path: str, content: str) -> list[ImportRef]:
    """Return import specifiers found in a file."""
    ext = PurePosixPath(path).suffix.lower()
    lang = LANGUAGE_BY_EXT.get(ext)
    if lang in ("javascript", "typescript", "vue", "svelte"):
        if ext in (".vue", ".svelte"):
            return _parse_vue_svelte(content)
        return _parse_js(content)
    if lang == "python":
        return _parse_python(content)
    if lang == "go":
        return _parse_go(content)
    if lang == "rust":
        return _parse_rust(content)
    return []
