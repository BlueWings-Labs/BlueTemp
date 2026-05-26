# BlueWings — AI GitHub Repository Intelligence Platform

## Vision

BlueWings is **not** a GitHub summarizer. It is an **AI Software Archaeologist** that helps teams understand how a codebase was built, how it evolved, and how to onboard, modernize, or migrate it.

## Core capabilities

| Role | What it does |
|------|----------------|
| **Software Archaeologist** | Reconstructs project history from PRs, commits, issues, and file churn |
| **Architecture Analyst** | Maps modules, dependencies, hot paths, and structural boundaries |
| **Migration Assistant** | Estimates complexity, surfaces risky areas, drafts rewrite strategies |
| **Onboarding System** | Tells new developers where to start and what to read first |

## Questions the platform answers

- How did this project evolve over time?
- Where should a new developer start?
- Which PR changed the architecture?
- What modules are reusable or could become standalone services?
- Which files are risky, unstable, or high-churn?
- How difficult is migration to another language or framework?
- What are the main services and responsibilities?
- Which contributors worked on critical systems?

## Data collected per repository

- Pull requests (metadata + file changes sample)
- Issues and timeline events
- Commits (recent history)
- Branches
- Contributors
- File tree / structure
- README and documentation paths
- Dependency manifests (`package.json`, `requirements.txt`, etc.)
- Discussion comments (via issue/PR threads)

## System architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Next.js Frontend (TypeScript)                │
│  Explorer │ Intelligence Dashboard │ AI Agent Chat               │
└────────────────────────────┬────────────────────────────────────┘
                             │ REST
┌────────────────────────────▼────────────────────────────────────┐
│                     FastAPI (api.py)                             │
│  /repo/*  │  /intelligence/*  │  /agent/*                        │
└─────┬──────────────┬─────────────────────┬──────────────────────┘
      │              │                     │
      ▼              ▼                     ▼
 github_services   intelligence/        grok_agent.py
 (GitHub API)      collector + analyzer   (LLM + tools)
      │              │
      │         Phase 2+ ──► Redis (cache) ──► PostgreSQL (snapshots)
      │                    └──► Vector DB (semantic memory)
      ▼
 GitHub REST API
```

## Backend modules (current → planned)

| Module | Status | Purpose |
|--------|--------|---------|
| `github_services.py` | ✅ Active | All GitHub HTTP calls |
| `intelligence/collector.py` | ✅ Phase 1 | Build repository snapshot |
| `intelligence/analyzer.py` | ✅ Phase 1 | Deterministic insights from snapshot |
| `grok_agent.py` | ✅ Active | Tool-calling agent |
| `github_mcp_server.py` | ✅ Active | MCP tools for Claude / IDE |
| `intelligence/memory.py` | 🔜 Phase 2 | Redis cache + Postgres persistence |
| `intelligence/embeddings.py` | 🔜 Phase 3 | Vector search over repo memory |

## Intelligence pipeline

1. **Collect** — Fetch repo metadata, tree, README, deps, PRs, issues, commits, contributors.
2. **Analyze** — Compute timelines, hot files, modules, onboarding paths, debt signals.
3. **Reason** — LLM uses structured insights + tools for deep Q&A.
4. **Generate** — Reports: architecture summary, onboarding guide, migration outline.

## Frontend surfaces

- **`/`** — Explorer: browse PRs, issues, full detail panels
- **`/intelligence`** — Dashboard: insights + AI analyst chat
- **`/agent`** — General GitHub tools chat

## Tech stack

| Layer | Technology |
|-------|------------|
| API | FastAPI |
| GitHub | REST API via `github_services` |
| LLM | Grok / Gemini / Groq / Ollama (`grok_agent.py`) |
| Cache (planned) | Redis |
| Storage (planned) | PostgreSQL |
| Semantic memory (planned) | pgvector or Qdrant |
| UI | Next.js, TypeScript, Tailwind |

## Report types (roadmap)

- Architecture summary
- Developer onboarding guide
- Dependency map
- Project timeline
- Rewrite / migration strategy
- Module explanations
- Technical debt report
- Modernization suggestions

See [ROADMAP.md](./ROADMAP.md) for phased delivery.
