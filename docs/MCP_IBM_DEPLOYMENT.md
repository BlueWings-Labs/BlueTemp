# Deploy BlueWings MCP on IBM Cloud + ContextForge

[IBM mcp-context-forge](https://ibm.github.io/mcp-context-forge/) (ContextForge) is a **gateway/registry** that federates MCP servers. BlueWings is your **MCP tool server** (GitHub + dependency graph + blast radius).

You deploy **two things**:

| Component | Role | IBM service |
|-----------|------|-------------|
| **ContextForge** | Admin UI, auth, tool routing, observability | Code Engine app #1 |
| **BlueWings MCP** | Your tools (`get_change_impact`, PRs, graph, …) | Code Engine app #2 |

Your Next.js app + `api.py` can stay local, on Vercel, or a third Code Engine app — they are separate from MCP federation.

---

## Architecture

```
  Developer / Agent
        │
        ▼
  ContextForge (IBM Code Engine)     https://mcpgateway-xxx.../admin
        │  registers
        ▼
  BlueWings MCP (IBM Code Engine)    https://bluewings-mcp-xxx.../mcp
        │
        ▼
  GitHub API  (GITHUB_TOKEN)
```

**Two-way usage:**

1. **Cursor / Claude** → ContextForge → BlueWings tools  
2. **BlueWings web UI** → `api.py` (same logic, REST not MCP)

---

## Path A — Local proof (before IBM Cloud)

### 1. Start ContextForge

```bash
docker run -d --name mcpgateway -p 4444:4444 \
  -e HOST=0.0.0.0 \
  -e JWT_SECRET_KEY="$(openssl rand -hex 32)" \
  -e PLATFORM_ADMIN_EMAIL=admin@example.com \
  -e PLATFORM_ADMIN_PASSWORD=changeme \
  -e MCPGATEWAY_UI_ENABLED=true \
  ghcr.io/ibm/mcp-context-forge:1.0.0-RC-2
```

Admin UI: http://localhost:4444/admin

Generate bearer token (same `JWT_SECRET_KEY`):

```bash
pip install mcp-contextforge-gateway
export JWT_SECRET_KEY=<same-as-container>
export MCPGATEWAY_BEARER_TOKEN=$(python3 -m mcpgateway.utils.create_jwt_token -u admin@example.com)
```

Docs: [ContextForge getting started](https://ibm.github.io/mcp-context-forge/)

### 2. Run BlueWings MCP over HTTP

```bash
cd BlueWings
pip install -r requirements.txt
export GITHUB_TOKEN=ghp_...
export MCP_TRANSPORT=streamable-http
export MCP_HOST=0.0.0.0
export MCP_PORT=8080
python github_mcp_server.py streamable-http
```

Or with Docker:

```bash
docker build -f Dockerfile.mcp -t bluewings-mcp .
docker run -p 8080:8080 -e GITHUB_TOKEN=ghp_... bluewings-mcp
```

MCP endpoint: `http://localhost:8080/mcp`

### 3. Register BlueWings in ContextForge

```bash
curl -X POST "http://localhost:4444/gateways" \
  -H "Authorization: Bearer $MCPGATEWAY_BEARER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "bluewings-github",
    "url": "http://host.docker.internal:8080/mcp"
  }'
```

On Linux use your host IP instead of `host.docker.internal`, or run both containers on the same Docker network.

**Alternative (stdio, no HTTP change):** use ContextForge translate bridge:

```bash
python3 -m mcpgateway.translate \
  --stdio "python /path/to/BlueWings/github_mcp_server.py stdio" \
  --expose-sse \
  --port 8002
```

Then register `http://localhost:8002/sse`. See [mcpgateway.translate](https://ibm.github.io/mcp-context-forge/using/mcpgateway-translate/).

### 4. Test a tool via gateway

Use the Admin UI **Tools** tab or MCP client pointed at ContextForge with your bearer token. Example prompt:

> Use get_change_impact for facebook/react on README.md

---

## Path B — IBM Cloud (recommended for hackathon)

Official guide: [Deploy ContextForge on IBM Cloud with Code Engine](https://ibm.github.io/mcp-context-forge/howto/ibm-cloud-code-engine/)

### Prerequisites

- IBM Cloud account
- IBM Cloud CLI + plugins: `container-registry`, `code-engine`
- Code Engine project (e.g. `bluewings-mcp-project`)
- IBM Container Registry namespace (e.g. `bluewings-ns`)

```bash
ibmcloud plugin install container-registry code-engine -f
ibmcloud login
ibmcloud cr namespace-create bluewings-ns   # once
ibmcloud ce project create --name bluewings-mcp-project
ibmcloud ce project select --name bluewings-mcp-project
```

### Step 1 — Deploy ContextForge gateway

Clone IBM’s repo and follow their Makefile flow, **or** pull their image:

```bash
# Example: push IBM image to your registry or use their doc's make ibmcloud-deploy
# Image: ghcr.io/ibm/mcp-context-forge:1.0.0-RC-2
```

Production tips from IBM:

- Use **PostgreSQL** (`DATABASE_URL`) not SQLite on Code Engine ([guide](https://ibm.github.io/mcp-context-forge/howto/ibm-cloud-code-engine/))
- Set `JWT_SECRET_KEY` (32+ bytes), `AUTH_REQUIRED=true`
- Scale: start with **1 vCPU / 4 GB** for the gateway

Note the **public URL** after deploy, e.g. `https://mcpgateway.abc123.us-south.codeengine.appdomain.cloud`

### Step 2 — Build & push BlueWings MCP image

```bash
cd BlueWings
docker build -f Dockerfile.mcp -t bluewings-mcp .
docker tag bluewings-mcp us.icr.io/bluewings-ns/bluewings-mcp:latest
ibmcloud cr login
docker push us.icr.io/bluewings-ns/bluewings-mcp:latest
```

### Step 3 — Deploy BlueWings MCP on Code Engine

```bash
ibmcloud ce secret create --name github-token \
  --from-literal GITHUB_TOKEN=ghp_your_token_here

ibmcloud ce app create --name bluewings-mcp \
  --image us.icr.io/bluewings-ns/bluewings-mcp:latest \
  --registry-secret-url us.icr.io/bluewings-ns \
  --port 8080 \
  --cpu 1 --memory 4G \
  --min-scale 0 --max-scale 2 \
  --env MCP_TRANSPORT=streamable-http \
  --env MCP_HOST=0.0.0.0 \
  --env MCP_PORT=8080 \
  --env-from-secret github-token

ibmcloud ce app get --name bluewings-mcp
```

Note the app URL, e.g. `https://bluewings-mcp.abc123.us-south.codeengine.appdomain.cloud`

**Sizing:** blast radius and full graphs are CPU/API heavy — use **at least 1 vCPU / 4 GB**; increase `max_files` limits only after testing.

### Step 4 — Register BlueWings in ContextForge (production)

```bash
export GATEWAY_URL=https://mcpgateway.abc123.us-south.codeengine.appdomain.cloud
export MCP_URL=https://bluewings-mcp.abc123.us-south.codeengine.appdomain.cloud/mcp
export MCPGATEWAY_BEARER_TOKEN=<jwt-from-your-gateway>

curl -X POST "$GATEWAY_URL/gateways" \
  -H "Authorization: Bearer $MCPGATEWAY_BEARER_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"bluewings-github\",\"url\":\"$MCP_URL\"}"
```

Confirm in **Admin UI → Gateways / Tools** that tools appear (`get_change_impact`, `get_repository_dependency_graph`, `list_pull_requests`, …).

### Step 5 — Use from agents

Point MCP clients at ContextForge (not directly at BlueWings), with the gateway bearer token. ContextForge routes tool calls to your Code Engine MCP app.

---

## Environment variables (BlueWings MCP container)

| Variable | Purpose |
|----------|---------|
| `GITHUB_TOKEN` | **Required** — GitHub API access |
| `MCP_TRANSPORT` | `streamable-http` for remote deploy |
| `MCP_HOST` | `0.0.0.0` in containers |
| `MCP_PORT` | `8080` (match Code Engine port) |
| `MCP_PATH` | `/mcp` (default) |
| `GITHUB_BATCH_CONCURRENCY` | Optional — lower if rate-limited |

---

## Security checklist (production)

- [ ] Store `GITHUB_TOKEN` in Code Engine secrets, never in the image  
- [ ] ContextForge: `AUTH_REQUIRED=true`, strong `JWT_SECRET_KEY`  
- [ ] HTTPS only (Code Engine provides TLS on public URLs)  
- [ ] Restrict gateway admin password / use IBM IAM where possible  
- [ ] Fine-grained GitHub token (`public_repo` or scoped PAT)  

---

## Hackathon demo script

1. Show **BlueWings UI** — Dependencies + Blast radius on a public repo.  
2. Show **ContextForge Admin** — BlueWings registered as a gateway.  
3. In **Cursor** (MCP config → gateway URL + token), ask:  
   *“What is the blast radius of changing `api.py` in this repo?”*  
4. Explain: same engine locally (REST) and enterprise path (IBM MCP gateway).

---

## Links

- ContextForge docs: https://ibm.github.io/mcp-context-forge/  
- IBM Code Engine deploy: https://ibm.github.io/mcp-context-forge/howto/ibm-cloud-code-engine/  
- Register servers: https://ibm.github.io/mcp-context-forge/using/servers/  
- BlueWings graph + blast radius: [DEPENDENCY_GRAPH.md](./DEPENDENCY_GRAPH.md)  
- Local MCP (stdio): [readme.md](../readme.md#mcp-claude-code)
