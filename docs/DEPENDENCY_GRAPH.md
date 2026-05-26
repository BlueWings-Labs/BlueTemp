# Dependency graph

BlueWings analyzes **import relationships** between source files in a GitHub repo and returns a **graph-ready JSON** document for MCP clients, REST APIs, and the Next.js `/dependencies` page.

## JSON shape (v1.0)

| Field | Description |
|-------|-------------|
| `repository` | Owner, repo, branch, URL |
| `meta` | `analyzed_at`, `truncated`, `focus_path`, etc. |
| `stats` | Node/edge counts, languages |
| `file_tree` | Nested directory tree (files in the graph only) |
| `nodes` | Files and external packages (`type`: `file` \| `package`) |
| `edges` | `source` → `target`, `kind`: `import` \| `require` \| `dynamic` \| `package` |
| `clusters` | Top-level folder groupings |

## REST API

```http
GET /repo/{owner}/{repo}/dependencies/graph?max_files=400&include_packages=true
GET /repo/{owner}/{repo}/dependencies/graph?focus_path=src/app/page.tsx&max_depth=4
```

## MCP (Cursor / Claude)

Add to `.cursor/mcp.json` (or Claude MCP config):

```json
{
  "mcpServers": {
    "bluewings-github": {
      "command": "python",
      "args": ["C:/BlueWings/github_mcp_server.py", "stdio"],
      "env": {
        "GITHUB_TOKEN": "ghp_..."
      }
    }
  }
}
```

### Tools

- **`get_repository_dependency_graph`** — Full repo graph (up to 800 files).
- **`get_file_dependency_subgraph`** — BFS from one file (`file_path`, `max_depth`).
- **`get_change_impact`** — Blast radius: reverse dependents, forward imports, related PRs, risk level.

### REST — blast radius

```http
GET /repo/{owner}/{repo}/dependencies/impact?file_path=src/app/page.tsx&max_files=400
```

Returns `summary.risk_level`, `dependents`, `dependencies`, `related_prs`, and `highlight` paths for the UI graph.

Example prompt in chat:

> Use get_repository_dependency_graph for facebook/react and summarize the most connected modules.

## Next.js visualization

1. `uvicorn api:app --reload --port 8000`
2. `cd frontend && npm run dev`
3. Open http://localhost:3000/dependencies

Uses **React Flow** + **dagre** layout. Export JSON for custom D3/Cytoscape frontends.

## Supported languages

JavaScript, TypeScript, Python, Go, Rust (regex import parsing). Vue/Svelte via `<script>` blocks.

## Limits

- Skips `node_modules`, `dist`, `.next`, `venv`, etc.
- Default 400 files per run (GitHub API rate limits).
- Large monorepos may set `truncated: true` in `meta`.

### Timeouts / slow networks

Batch file fetch uses a **single shared HTTP client**, **5 concurrent** requests (configurable), and **retries**. Tune via `.env`:

```env
GITHUB_BATCH_CONCURRENCY=5
GITHUB_HTTP_CONNECT_TIMEOUT=45
GITHUB_HTTP_READ_TIMEOUT=90
GITHUB_HTTP_RETRIES=3
```

If you still see timeouts, lower `max_files` to **100–150** in the UI or query string.
