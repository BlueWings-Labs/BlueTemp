# BlueWings Roadmap

## Phase 1 — Repository Intelligence Core ✅ (in progress)

- [x] Unified GitHub data layer (`github_services.py`)
- [x] PR / issue explorer with full detail expansion
- [x] LLM agent with GitHub tools
- [x] **Snapshot collector** — tree, README, branches, commits, deps
- [x] **Insight analyzer** — evolution, hot files, modules, onboarding hints
- [x] **`/intelligence` API + UI** — dashboard + analyst chat

## Phase 2 — Persistence & cache

- [ ] PostgreSQL schema: `repositories`, `snapshots`, `insights`, `conversations`
- [ ] Redis: cache GitHub responses and computed insights (TTL)
- [ ] Background job: refresh snapshot on demand / schedule
- [ ] Compare snapshots over time (diff two points in history)

## Phase 3 — Semantic memory

- [ ] Embed README, PR bodies, issue threads, file paths
- [ ] Vector DB (pgvector or Qdrant)
- [ ] Semantic search: “where is auth handled?”
- [ ] RAG pipeline for agent answers

## Phase 4 — Deep analysis

- [ ] AST / language-aware parsing (Python, TS, Go)
- [ ] Service boundary detection from imports
- [ ] Migration difficulty scorer per module
- [ ] Architecture diagram generation (Mermaid)
- [ ] PDF / Markdown report export

## Phase 5 — Workflows

- [ ] Saved analyses per team
- [ ] Migration project templates
- [ ] CI webhook: analyze on release tag
- [ ] Multi-repo org dashboards
