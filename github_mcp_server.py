"""
GitHub MCP Server — exposes github_services as MCP tools for Claude Code / MCP clients.

Supports both github.com and github.ibm.com (GitHub Enterprise).

Run: python github_mcp_server.py stdio
"""

import os

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

import github_services as gh
from github_services import GitHubClient
from dependency_graph.builder import build_dependency_graph
from dependency_graph.impact import build_change_impact


def _transport_security() -> TransportSecuritySettings | None:
    """Render/proxies send Host: *.onrender.com — localhost-only protection rejects them."""
    allowed = os.getenv("MCP_ALLOWED_HOSTS", "").strip()
    if allowed:
        return TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=[h.strip() for h in allowed.split(",") if h.strip()],
        )
    if os.getenv("MCP_DNS_REBINDING", "").lower() in ("1", "true", "yes", "on"):
        return TransportSecuritySettings(enable_dns_rebinding_protection=True)
    return TransportSecuritySettings(enable_dns_rebinding_protection=False)


mcp = FastMCP(
    "GitHub History MCP",
    host=os.getenv("FASTMCP_HOST", "0.0.0.0"),
    transport_security=_transport_security(),
    json_response=os.getenv("MCP_JSON_RESPONSE", "").lower() in ("1", "true", "yes", "on"),
)


def _client(github_host: str = "") -> GitHubClient | None:
    """
    Return an IBM client when the caller passes github_host='ibm' or
    'github.ibm.com'; return None (= default public client) otherwise.
    """
    h = (github_host or "").strip().lower()
    if h in ("ibm", "github.ibm.com"):
        return GitHubClient(host="ibm")
    return None


# ── Pull requests ─────────────────────────────────────────────────────────────

@mcp.tool()
async def list_pull_requests(
    owner: str,
    repo: str,
    state: str = "all",
    sort: str = "created",
    direction: str = "desc",
    per_page: int = 30,
    page: int = 1,
    max_pages: int = 1,
    github_host: str = "",
) -> list[dict]:
    """
    List pull requests for a repository (paginated).

    Defaults: 30 PRs from page 1 — safe for large repos.
    For IBM GitHub Enterprise set github_host='ibm' (requires GITHUB_IBM_TOKEN in env).
    """
    return await gh.list_pull_requests(
        owner, repo,
        state=state, sort=sort, direction=direction,
        per_page=max(1, min(per_page, 100)),
        page=max(1, page),
        max_pages=max(1, min(max_pages, 10)),
        client=_client(github_host),
    )


@mcp.tool()
async def get_pull_request_detail(
    owner: str, repo: str, pr_number: int, github_host: str = ""
) -> dict:
    """Get full detail of a single PR. Use github_host='ibm' for GitHub Enterprise."""
    return await gh.get_pull_request_detail(owner, repo, pr_number, client=_client(github_host))


@mcp.tool()
async def list_pr_reviews(
    owner: str, repo: str, pr_number: int, github_host: str = ""
) -> list[dict]:
    """Get all code reviews for a PR."""
    return await gh.list_pr_reviews(owner, repo, pr_number, client=_client(github_host))


@mcp.tool()
async def list_pr_comments(
    owner: str, repo: str, pr_number: int, github_host: str = ""
) -> list[dict]:
    """Get inline code review comments on a PR."""
    return await gh.list_pr_comments(owner, repo, pr_number, client=_client(github_host))


@mcp.tool()
async def list_pr_commits(
    owner: str, repo: str, pr_number: int, github_host: str = ""
) -> list[dict]:
    """List commits in a pull request."""
    return await gh.list_pr_commits(owner, repo, pr_number, client=_client(github_host))


# ── Issues ────────────────────────────────────────────────────────────────────

@mcp.tool()
async def list_issues(
    owner: str,
    repo: str,
    state: str = "all",
    sort: str = "created",
    direction: str = "desc",
    labels: str = "",
    per_page: int = 30,
    page: int = 1,
    max_pages: int = 1,
    github_host: str = "",
) -> list[dict]:
    """List issues (excludes PRs). Paginated — default 30 per call."""
    return await gh.list_issues(
        owner, repo,
        state=state, sort=sort, direction=direction, labels=labels,
        per_page=max(1, min(per_page, 100)),
        page=max(1, page),
        max_pages=max(1, min(max_pages, 10)),
        client=_client(github_host),
    )


@mcp.tool()
async def get_issue_detail(
    owner: str, repo: str, issue_number: int, github_host: str = ""
) -> dict:
    """Get full detail of a single issue."""
    return await gh.get_issue_detail(owner, repo, issue_number, client=_client(github_host))


@mcp.tool()
async def list_issue_comments(
    owner: str, repo: str, issue_number: int, github_host: str = ""
) -> list[dict]:
    """Get all comments on an issue."""
    return await gh.list_issue_comments(owner, repo, issue_number, client=_client(github_host))


@mcp.tool()
async def list_issue_events(
    owner: str, repo: str, issue_number: int, github_host: str = ""
) -> list[dict]:
    """Get timeline events for an issue."""
    return await gh.list_issue_events(owner, repo, issue_number, client=_client(github_host))


# ── Repo metadata ─────────────────────────────────────────────────────────────

@mcp.tool()
async def get_repo_info(owner: str, repo: str, github_host: str = "") -> dict:
    """Get repository metadata. Use github_host='ibm' for GitHub Enterprise."""
    return await gh.get_repo_info(owner, repo, client=_client(github_host))


@mcp.tool()
async def list_repo_labels(owner: str, repo: str, github_host: str = "") -> list[dict]:
    """List repository labels."""
    return await gh.list_repo_labels(owner, repo, client=_client(github_host))


@mcp.tool()
async def list_repo_contributors(owner: str, repo: str, github_host: str = "") -> list[dict]:
    """List contributors with commit counts."""
    return await gh.list_repo_contributors(owner, repo, client=_client(github_host))


@mcp.tool()
async def search_issues_and_prs(
    owner: str, repo: str, query: str, kind: str = "both", github_host: str = ""
) -> list[dict]:
    """Search issues and/or PRs in a repository."""
    return await gh.search_issues_and_prs(owner, repo, query, kind=kind, client=_client(github_host))


# ── Dependency graph & impact ─────────────────────────────────────────────────

@mcp.tool()
async def get_repository_dependency_graph(
    owner: str,
    repo: str,
    ref: str = "",
    max_files: int = 400,
    include_packages: bool = True,
    github_host: str = "",
) -> dict:
    """
    Build a code dependency graph for a GitHub repository.

    Returns JSON with file_tree, nodes (files + packages), edges (imports), and clusters.
    Use github_host='ibm' to target GitHub Enterprise (github.ibm.com).
    Requires GITHUB_IBM_TOKEN env var for IBM host.
    """
    return await build_dependency_graph(
        owner, repo,
        ref=ref or None,
        max_files=max(50, min(max_files, 800)),
        include_packages=include_packages,
        client=_client(github_host),
    )


@mcp.tool()
async def get_file_dependency_subgraph(
    owner: str,
    repo: str,
    file_path: str,
    ref: str = "",
    max_depth: int = 3,
    max_files: int = 200,
    github_host: str = "",
) -> dict:
    """
    Dependency subgraph starting from one file (outgoing imports, BFS to max_depth).
    Use github_host='ibm' to target GitHub Enterprise.
    """
    return await build_dependency_graph(
        owner, repo,
        ref=ref or None,
        max_files=max(50, min(max_files, 800)),
        focus_path=file_path,
        max_depth=max(1, min(max_depth, 8)),
        client=_client(github_host),
    )


@mcp.tool()
async def get_change_impact(
    owner: str,
    repo: str,
    file_path: str,
    ref: str = "",
    max_files: int = 400,
    include_packages: bool = True,
    max_depth_dependents: int = 4,
    max_depth_dependencies: int = 3,
    pr_sample_size: int = 40,
    github_host: str = "",
) -> dict:
    """
    Blast radius analysis for editing a file: who imports it, what it imports,
    related recent PRs, risk level, and a highlight subgraph.
    Use github_host='ibm' to target GitHub Enterprise (github.ibm.com).
    """
    return await build_change_impact(
        owner, repo, file_path,
        ref=ref or None,
        max_files=max(50, min(max_files, 800)),
        include_packages=include_packages,
        max_depth_dependents=max(1, min(max_depth_dependents, 8)),
        max_depth_dependencies=max(1, min(max_depth_dependencies, 8)),
        pr_sample_size=max(5, min(pr_sample_size, 80)),
        client=_client(github_host),
    )


# ── Health ────────────────────────────────────────────────────────────────────

@mcp.custom_route("/health", methods=["GET"])
async def _health(_request):
    from starlette.responses import JSONResponse
    return JSONResponse({"status": "ok", "service": "github-history-mcp"})


if __name__ == "__main__":
    import sys

    transport = (
        sys.argv[1]
        if len(sys.argv) > 1
        else os.getenv("MCP_TRANSPORT", "stdio")
    )
    if transport in ("streamable-http", "http", "sse"):
        host = os.getenv("MCP_HOST", "0.0.0.0")
        port = int(os.getenv("PORT", os.getenv("MCP_PORT", "8080")))

        if transport == "sse":
            asgi_app = mcp.sse_app()
        else:
            asgi_app = mcp.streamable_http_app()

        import uvicorn
        uvicorn.run(asgi_app, host=host, port=port)
    else:
        mcp.run(transport=transport)


# ── Repository search ─────────────────────────────────────────────────────────
@mcp.tool()
async def search_repository_files(
    owner: str,
    repo: str,
    query: str,
    ref: str = "",
    per_page: int = 30,
    page: int = 1,
    github_host: str = "",
) -> list[dict]:
    """
    Search repository files by filename or path.

    Features:
    - Search by filename
    - Search by extension
    - Search nested paths
    - Pagination support
    - Optional branch/ref support

    Examples:
    - Dockerfile
    - package.json
    - *.yml
    - src/api

    Use github_host='ibm' for GitHub Enterprise.
    """

    return await gh.search_repository_files(
        owner,
        repo,
        query=query,
        ref=ref,
        per_page=max(1, min(per_page, 100)),
        page=max(1, page),
        client=_client(github_host),
    )


@mcp.tool()
async def search_repository_code(
    owner: str,
    repo: str,
    query: str,
    ref: str = "",
    per_page: int = 30,
    page: int = 1,
    github_host: str = "",
) -> list[dict]:
    """
    Search inside repository code/content.

    Features:
    - Search code text
    - Detect deprecated APIs
    - Find routes/functions
    - Pagination support
    - Optional branch/ref support

    Examples:
    - FastAPI
    - TODO
    - deprecated_function
    - router.get

    Use github_host='ibm' for GitHub Enterprise.
    """

    return await gh.search_repository_code(
        owner,
        repo,
        query=query,
        ref=ref,
        per_page=max(1, min(per_page, 100)),
        page=max(1, page),
        client=_client(github_host),
    )
