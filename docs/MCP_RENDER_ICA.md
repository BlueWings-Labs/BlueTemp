# BlueWings MCP on Render → Context Forge → ICA → Your App

This guide adapts the **ICA Agentic App Studio (Low Code)** lab to **your** codebase:

| Lab (generic) | Your project |
|---------------|--------------|
| Context Studio MCP + `ctx_...` | **BlueWings GitHub MCP** (`github_mcp_server.py`) |
| Context vector query tools | `get_change_impact`, `get_repository_dependency_graph`, PR/issue tools |
| IBM Code Engine | **Render** (Docker `Dockerfile.mcp`) |
| Context Forge in ICA | Same — register your Render MCP URL |

Your Next.js app can keep using local `api.py` + `grok_agent.py`, **or** call the ICA workflow API for the deployed agent.

---

## Architecture

```
  BlueWings Next.js (Vercel/local)
        │  POST /api/ica/chat  (optional proxy)
        ▼
  ICA Langflow API  (workflow: Chat In → ICA Agent → Chat Out)
        │
        ▼
  ICA Context Forge (Virtual Server)
        │
        ▼
  BlueWings MCP on Render  https://<service>.onrender.com/mcp
        │
        ▼
  GitHub API  (GITHUB_TOKEN secret on Render)
```

**Important:** Do not point ICA directly at a public MCP URL without auth unless you accept open tool access. For demos, use ICA Context Forge **Bearer** auth on the gateway and keep the raw Render URL private (register only inside Forge).

---

## Part 1 — Deploy BlueWings MCP on Render

### 1.1 Prerequisites

- GitHub repo pushed (this `BlueWings` repo)
- [Render](https://render.com) account
- GitHub PAT with `public_repo` or `repo` → you will set `GITHUB_TOKEN` on Render

### 1.2 Create Web Service (Docker)

1. Render Dashboard → **New** → **Web Service**
2. Connect your GitHub repo
3. Settings:
   - **Name:** `bluewings-mcp`
   - **Runtime:** Docker
   - **Dockerfile Path:** `Dockerfile.mcp`
   - **Instance type:** at least **512 MB** (1 GB+ recommended for large graphs)
   - **Health Check Path:** `/health` (MCP endpoint remains `/mcp`)

Or use the repo’s `render.yaml` (Blueprint): deploy from repo root with Blueprint sync.

### 1.3 Environment variables (Render → Environment)

| Key | Value |
|-----|--------|
| `GITHUB_TOKEN` | `ghp_...` (secret) |
| `MCP_TRANSPORT` | `streamable-http` |
| `MCP_HOST` | `0.0.0.0` |
| `MCP_PORT` | `8080` |
| `MCP_PATH` | `/mcp` |

`Dockerfile.mcp` already sets these defaults; `GITHUB_TOKEN` is required at runtime.

### 1.4 Verify deploy

After deploy, note:

```text
MCP_URL=https://bluewings-mcp.onrender.com/mcp
```

Quick check (from your machine):

```bash
curl -sS -o /dev/null -w "%{http_code}\n" https://YOUR-SERVICE.onrender.com/mcp
```

A `405` or MCP handshake response is normal; total failure is connection timeout or `502` (service sleeping on free tier — first request may take ~30s).

**Free tier:** Render spins down idle services. ICA tool calls may time out on cold start; use a paid instance or keep-alive ping for demos.

---

## Part 2 — Context Forge (`mcp-context-forge`)

You have two options.

### Option A — ICA built-in Context Forge (matches the lab)

Use the Forge opened from **Agentic App Studio → MCP Servers → Access MCP Gateway**. No separate Render deploy for Forge.

Skip to **Part 3**.

### Option B — Self-hosted Context Forge (local or Render)

Use when you want the [IBM gateway UI](https://ibm.github.io/mcp-context-forge/) outside ICA.

**Local (dev):**

```bash
docker run -d --name mcpgateway -p 4444:4444 \
  -e HOST=0.0.0.0 \
  -e JWT_SECRET_KEY="$(openssl rand -hex 32)" \
  -e PLATFORM_ADMIN_EMAIL=admin@example.com \
  -e PLATFORM_ADMIN_PASSWORD=changeme \
  -e MCPGATEWAY_UI_ENABLED=true \
  ghcr.io/ibm/mcp-context-forge:1.0.0-RC-2
```

Admin: http://localhost:4444/admin

Register BlueWings:

```bash
export MCPGATEWAY_BEARER_TOKEN=<jwt-from-forge-docs>
curl -X POST "http://localhost:4444/gateways" \
  -H "Authorization: Bearer $MCPGATEWAY_BEARER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"bluewings-github","url":"https://YOUR-SERVICE.onrender.com/mcp"}'
```

Expose Forge to ICA via **ngrok** or deploy Forge on Render (second service, PostgreSQL recommended for production — see [IBM Code Engine guide](https://ibm.github.io/mcp-context-forge/howto/ibm-cloud-code-engine/)).

More detail: [MCP_IBM_DEPLOYMENT.md](./MCP_IBM_DEPLOYMENT.md).

---

## Part 3 — ICA Agentic App Studio (adapted lab steps)

### 3.1 Create agentic app

1. Log in to [IBM Consulting Advantage](https://servicesessentials.ibm.com/)
2. Switch to **Personal Team**
3. Open [Agentic App Studio](https://servicesessentials.ibm.com/launchpad/agent-assistant-studio)
4. **Create an Agentic App** — e.g. name: `BlueWings GitHub Intelligence`

### 3.2 Configure MCP (lab §2, adapted)

1. In the app → **MCP Servers** → **Access MCP Gateway** (Context Forge)
2. **MCP Servers** tab → **Add New MCP Server**
3. Fill in:

| Field | Your value |
|-------|------------|
| Server Name | `BlueWings GitHub MCP` |
| Server URL | `https://YOUR-SERVICE.onrender.com/mcp` |
| Description | GitHub PRs/issues, dependency graph, blast radius |
| Transport | **Streamable HTTP** |
| Authentication | **None** if MCP is open; prefer **Bearer** if you put Forge in front and use gateway token only |

4. **Save** → status **Active**
5. **Virtual Server** tab → edit default server → enable **all BlueWings tools**, e.g.:
   - `list_pull_requests`, `get_pull_request_detail`
   - `get_repository_dependency_graph`, `get_file_dependency_subgraph`
   - `get_change_impact`
   - `get_repo_info`, `search_issues_and_prs`
   - (and other tools from `github_mcp_server.py`)
6. Back in the app **MCP Servers** page → click tool count → confirm tools list

### 3.3 Create agent (lab §3, adapted)

**Agents** → **Create Agent Orchestration**

| Setting | Value |
|---------|--------|
| Platform | ICA |
| Framework | Strands |
| Model | GPT-5.1 (or latest available) |
| Pattern | Single |

**Agent prompt (copy and edit owner/repo examples):**

```text
You are a GitHub repository intelligence agent for BlueWings.

Use MCP tools to answer questions about pull requests, issues, dependency graphs, and change blast radius.

Rules:
- Always ask for owner/repo if missing (format: owner/repo, e.g. facebook/react).
- For architecture or import questions, use get_repository_dependency_graph or get_file_dependency_subgraph.
- For "what breaks if I edit file X", use get_change_impact with the file path relative to repo root.
- For PR/issue history, use list_pull_requests, get_pull_request_detail, list_issues, search_issues_and_prs.
- Summarize findings clearly; cite tool results, not guesses.

Do not invent GitHub data — only use tool outputs.
```

**Review YAML:** ensure **Tools** includes your BlueWings MCP tools (not Context Studio `vector_query`).

**Deploy** the agent → note **Agent Name**.

**Invoke test:**

> What is the blast radius of changing `README.md` in `facebook/react`?

### 3.4 Workflow (lab §4)

1. **Workflow** → **Create New Workflow**
2. Add **Chat Input** → **ICA Agent** → **Chat Output**
3. ICA Agent config:
   - **Agentic App ID:** from app header/URL
   - **Agent Name:** your deployed agent
4. Connect: Chat Input → ICA Agent → Chat Output
5. **Playground** test with a real `owner/repo` question

### 3.5 API access (lab §5)

1. Workflow → **Share** → **API Access**
2. Copy cURL; change host per lab note:
   - From: `agentstudio.servicesessentials.ibm.com`
   - To: **`langflow.servicesessentials.ibm.com`**
3. **Create an API Key** → store in password manager (shown once)
4. Test:

```bash
curl --request POST \
  --url 'https://langflow.servicesessentials.ibm.com/api/v1/run/YOUR_FLOW_ID?stream=false' \
  --header 'Content-Type: application/json' \
  --header 'x-api-key: YOUR_API_KEY' \
  --data '{
    "output_type": "chat",
    "input_type": "chat",
    "input_value": "Blast radius of changing src/index.js in facebook/react?",
    "session_id": "bluewings-demo-1"
  }'
```

Never commit `x-api-key` to git.

---

## Part 4 — Use ICA agent inside BlueWings (Next.js)

Your app today uses `frontend/src/lib/agent-api.ts` → `api.py` `/agent/chat`. To add ICA as an optional backend:

### 4.1 Environment variables

**Server-only** (e.g. `.env.local`, Vercel secrets):

```env
ICA_WORKFLOW_URL=https://langflow.servicesessentials.ibm.com/api/v1/run/YOUR_FLOW_ID?stream=false
ICA_API_KEY=your_ica_api_key
```

Optional feature flag:

```env
NEXT_PUBLIC_AGENT_BACKEND=ica
```

### 4.2 API route proxy (recommended)

Create `frontend/src/app/api/ica/chat/route.ts` so the browser never sees `ICA_API_KEY`:

```typescript
import { NextRequest, NextResponse } from "next/server";

export async function POST(req: NextRequest) {
  const url = process.env.ICA_WORKFLOW_URL;
  const apiKey = process.env.ICA_API_KEY;
  if (!url || !apiKey) {
    return NextResponse.json({ error: "ICA not configured" }, { status: 503 });
  }

  const { message, session_id } = await req.json();
  const res = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-api-key": apiKey,
    },
    body: JSON.stringify({
      output_type: "chat",
      input_type: "chat",
      input_value: message,
      session_id: session_id ?? `bw-${Date.now()}`,
    }),
  });

  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    return NextResponse.json(
      { error: data.detail ?? data.message ?? "ICA workflow failed" },
      { status: res.status }
    );
  }
  return NextResponse.json(data);
}
```

### 4.3 Wire Agent page

In `frontend/src/app/agent/page.tsx`, when `NEXT_PUBLIC_AGENT_BACKEND=ica`, POST to `/api/ica/chat` instead of `sendAgentMessage()` from `agent-api.ts`.

Parse ICA response shape from your test cURL (field names may be `outputs`, `result`, or `message` depending on Langflow version — adjust after first successful test).

---

## Lab checklist (your version)

| Criterion | How you verify |
|-----------|----------------|
| MCP on Render | `https://...onrender.com/mcp` deploy healthy |
| Context Forge | Tools visible in ICA MCP Servers (15 tools from `github_mcp_server.py`) |
| Agent deployed | Invoke: blast radius / PR question with real repo |
| Workflow | Playground: Chat In → Agent → Chat Out |
| API | cURL to `langflow.servicesessentials.ibm.com` returns answer |
| Project | Optional `/api/ica/chat` + Agent page |

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| No tools in ICA | Virtual Server not selecting BlueWings tools; MCP URL wrong (`/mcp` suffix) |
| 502 / timeout | Render cold start; retry or upgrade instance |
| GitHub rate limit | Lower `max_files` in prompts; set `GITHUB_BATCH_CONCURRENCY` on Render |
| Agent hallucinates repo data | Strengthen system prompt: tools only; test Invoke before workflow |
| API 401 | Regenerate ICA API key; header `x-api-key` |
| Wrong API host | Use `langflow.servicesessentials.ibm.com` not `agentstudio...` |

---

## Related files in this repo

| File | Role |
|------|------|
| `github_mcp_server.py` | MCP tools + HTTP transport |
| `Dockerfile.mcp` | Render / container image |
| `render.yaml` | Render Blueprint for MCP service |
| `docs/MCP_IBM_DEPLOYMENT.md` | Context Forge + IBM Cloud variant |
| `frontend/src/lib/agent-api.ts` | Local Python agent client |

---

## Security

- Store `GITHUB_TOKEN` and `ICA_API_KEY` only in Render/Vercel secrets or local `.env` (gitignored).
- Public Render MCP without auth allows anyone to spend your GitHub rate limit — prefer ICA Forge with Bearer, or add auth in front of MCP for production.
