# Context Studio export (ICA lab)

Generate an import-ready bundle for **IBM ICA Context Studio** from any GitHub repository BlueWings can analyze.

## What you get (ZIP)

| Path | Purpose |
|------|---------|
| `schema/software-repository-archaeology-schema.jsonld` | Global ontology — import **once** (ICA lab JSON-LD syntax) |
| `instances/{owner}-{repo}-instances.jsonld` | Per-repo entity instances + relationships |
| `data/{owner}-{repo}-facts.json` | Curated facts pack (ground truth for agents) |
| `docs/01-project-overview.md` … `07-project-structure.md` … `08-file-dependencies.md` … `06-agent-instructions.md` | Upload to Context Studio **Source & Data** (structure = layout; dependencies = file imports) |
| `structure/{owner}-{repo}-project-structure.json` | Machine-readable tree, layers, cross-module connections |
| `dependencies/{owner}-{repo}-file-dependencies.json` | File-to-file edges, per-file import lists, external packages |
| `manifest.json` | Import steps, suggested context name, validation notes |
| `README.txt` | Quick import order |

## API

```http
POST /repo/{owner}/{repo}/context-studio/export
Content-Type: application/json

{
  "ref": "",
  "include_graph": true,
  "graph_max_files": 300,
  "llm_enhance_docs": false,
  "pr_file_sample": 25
}
```

Returns `application/zip`. Same options via GET query params.

**UI:** **Context Studio** page (`/context-studio`) — preview bundle, import checklist, download ZIP. Intelligence links here after analysis.

## Import into Context Studio

1. **New Schema** → Import `json-ld` → upload `schema/software-repository-archaeology-schema.jsonld`
2. **Publish** the schema
3. **New Context** → link schema → name e.g. `BlueWings — owner/repo`
4. **Source & Data** → upload all `docs/*.md`
5. Add business rules (e.g. high-risk hot files need architecture review)
6. Expose Context Studio MCP; register **BlueWings GitHub MCP** in Context Forge (see [MCP_RENDER_ICA.md](./MCP_RENDER_ICA.md))

## Design (why it scales to large repos)

- **Project structure** in schema (`ProjectStructure`, `Directory`, `CodeLayer`, `ImportsFromModule`) + `07-project-structure.md` + `structure/*.json`
- **File dependencies** in schema (`DependencyGraph`, `SourceFile`, `ImportsFile`, `ExternalPackage`) + `08-file-dependencies.md` + `dependencies/*.json` — how files import each other (sampled)
- **No every source file** in JSON-LD — directory tree, modules, hot files, hubs, ~100 import edges, per-file lists for high-impact paths
- **Instances** are built **deterministically** from `analyze_snapshot` + optional dependency graph
- **LLM** is optional (`llm_enhance_docs`) for markdown polish only; facts stay in JSON
- **Live data** remains on BlueWings MCP (`get_change_impact`, etc.)

## Dual MCP pattern (recommended)

| MCP server | Role |
|------------|------|
| Context Studio (`ctx_...`) | Stable project memory + vector docs |
| BlueWings GitHub MCP | Live PRs, blast radius, full graph |

Example ICA prompt:

> Using context ctx_xxx and BlueWings tools for owner/repo, what is the blast radius of editing `src/...` and does it match our hot-file list in context?
