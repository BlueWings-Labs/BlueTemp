# BlueWings — AI GitHub Repository Intelligence Platform

**Not a GitHub summarizer.** BlueWings helps teams understand how a codebase was built, evolved, and how to onboard, modernize, or migrate it.

Roles: **Software Archaeologist** · **Architecture Analyst** · **Migration Assistant** · **Onboarding System**

📖 Full vision: [docs/PLATFORM.md](docs/PLATFORM.md) · Roadmap: [docs/ROADMAP.md](docs/ROADMAP.md)

---

## What it does today (Phase 1)

| Surface | URL | Purpose |
|---------|-----|---------|
| **Explorer** | http://localhost:3000 | PRs, issues, full detail (comments, diffs, reviews) |
| **Dependencies** | http://localhost:3000/dependencies | Import graph JSON + interactive React Flow map |
| **Intelligence** | http://localhost:3000/intelligence | Evolution, modules, hot files, onboarding, migration hints + AI analyst |
| **Context Studio** | http://localhost:3000/context-studio | ICA export: JSON-LD schema, repo docs, import wizard, ZIP bundle |
| **Agent** | http://localhost:3000/agent | General GitHub tools chat |

### Intelligence answers questions like

- How did this project evolve?
- Where should a new developer start?
- Which PR changed the architecture?
- What modules are reusable / could become services?
- Which files are risky or high-churn?
- How difficult is migration to another stack?

---

## Architecture

```
github_services.py     ← GitHub API (single source of truth)
intelligence/          ← collector + analyzer + agent context
api.py                 ← REST API
grok_agent.py          ← LLM + tools (Gemini / Groq / Ollama / …)
github_mcp_server.py   ← MCP for Claude / IDE (incl. dependency graph tools)
dependency_graph/      ← Import parser + graph JSON builder
frontend/              ← Next.js + TypeScript + Tailwind
```

**Planned:** Redis cache · PostgreSQL snapshots · Vector DB for semantic memory (see `docker-compose.yml`)

---

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# GITHUB_TOKEN + LLM key (Gemini recommended — free)
```

**GitHub token:** https://github.com/settings/tokens — `repo` or `public_repo`  
**LLM (free):** https://aistudio.google.com/apikey → `GEMINI_API_KEY`, `LLM_PROVIDER=gemini`

---

Dependency graph details: [docs/DEPENDENCY_GRAPH.md](docs/DEPENDENCY_GRAPH.md)

---

## Run

```bash
# API
uvicorn api:app --reload --port 8000

# Frontend
cd frontend && npm install && npm run dev
```

### Key API endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /repo/{owner}/{repo}/intelligence/insights` | Full analysis (collect + insights) |
| `POST /repo/{owner}/{repo}/intelligence/ask` | AI analyst with insights + tools |
| `GET /repo/{owner}/{repo}/pulls/{n}/full` | PR with diffs, reviews, comments |
| `POST /agent/chat` | General agent |

Swagger: http://localhost:8000/docs

---

## MCP (Claude Code / ContextForge / IBM Cloud)

**Local stdio (Cursor):**

```bash
python github_mcp_server.py stdio
```

**HTTP (ContextForge registry, IBM Code Engine):**

```bash
export GITHUB_TOKEN=ghp_...
export MCP_TRANSPORT=streamable-http
python github_mcp_server.py streamable-http
# → http://localhost:8080/mcp
```

Deploy guides: [Render + ICA](docs/MCP_RENDER_ICA.md) · [IBM Cloud + Context Forge](docs/MCP_IBM_DEPLOYMENT.md)  
Context Studio bundle: [docs/CONTEXT_STUDIO_EXPORT.md](docs/CONTEXT_STUDIO_EXPORT.md)

**ICA agent in the app:** set `ICA_API_KEY` + `ICA_FLOW_ID` in `.env`, choose **ICA / Local / Auto** on Agent & Intelligence pages (`AGENT_BACKEND=auto` default).

---

## Example: intelligence via curl

```bash
curl "http://localhost:8000/repo/facebook/react/intelligence/insights"

curl -X POST "http://localhost:8000/repo/facebook/react/intelligence/ask" \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Where should a new developer start?"}]}'
```


Changinh for Auto PR Review
