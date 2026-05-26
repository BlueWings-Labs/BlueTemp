"""
Shared GitHub data layer — used by api.py, github_mcp_server.py, and grok_agent.py.

Supports multiple GitHub hosts (github.com and github.ibm.com) via GitHubClient.
Module-level functions use the default public GitHub client and are fully
backward-compatible. Pass a GitHubClient instance (or host="ibm") wherever
you need IBM GitHub Enterprise support.
"""

from __future__ import annotations

import asyncio
import base64
import os
from enum import Enum
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv()

# ── Host configuration ────────────────────────────────────────────────────────

class GitHubHost(str, Enum):
    PUBLIC = "github.com"
    IBM    = "github.ibm.com"


# Public GitHub (github.com)
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_API   = "https://api.github.com"

# IBM GitHub Enterprise (github.ibm.com)
GITHUB_IBM_TOKEN = os.getenv("GITHUB_IBM_TOKEN", "")
GITHUB_IBM_API   = os.getenv(
    "GITHUB_IBM_API",
    "https://github.ibm.com/api/v3",
)

# Shared timeouts for large batch fetches (dependency graph)
GITHUB_HTTP_TIMEOUT = httpx.Timeout(
    connect=float(os.getenv("GITHUB_HTTP_CONNECT_TIMEOUT", "45")),
    read=float(os.getenv("GITHUB_HTTP_READ_TIMEOUT", "90")),
    write=30.0,
    pool=30.0,
)
GITHUB_HTTP_RETRIES      = int(os.getenv("GITHUB_HTTP_RETRIES", "3"))
GITHUB_BATCH_CONCURRENCY = int(os.getenv("GITHUB_BATCH_CONCURRENCY", "5"))


class GitHubError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


# ── GitHubClient ──────────────────────────────────────────────────────────────

class GitHubClient:
    """
    Encapsulates base URL + auth token for one GitHub host.

    Usage
    -----
    gh_public = GitHubClient()                          # uses GITHUB_TOKEN
    gh_ibm    = GitHubClient(host=GitHubHost.IBM)       # uses GITHUB_IBM_TOKEN
    gh_ibm    = GitHubClient.for_host("ibm")            # convenience shorthand
    gh_custom = GitHubClient(base_url="https://...", token="ghp_...")
    """

    def __init__(
        self,
        *,
        host: GitHubHost | str | None = None,
        base_url: str | None = None,
        token: str | None = None,
    ) -> None:
        # Resolve host enum
        if isinstance(host, str):
            _h = host.lower().strip()
            if _h in ("ibm", "github.ibm.com"):
                host = GitHubHost.IBM
            else:
                host = GitHubHost.PUBLIC

        if base_url:
            self.base_url = base_url.rstrip("/")
            self.token = token or GITHUB_TOKEN
            self.host = GitHubHost.PUBLIC  # treat custom as public for header purposes
        elif host == GitHubHost.IBM:
            self.base_url = GITHUB_IBM_API.rstrip("/")
            self.token = token or GITHUB_IBM_TOKEN
            self.host = GitHubHost.IBM
        else:
            self.base_url = GITHUB_API.rstrip("/")
            self.token = token or GITHUB_TOKEN
            self.host = GitHubHost.PUBLIC

    @classmethod
    def for_host(cls, host: str | None) -> "GitHubClient":
        """Convenience: GitHubClient.for_host('ibm') or for_host('public')."""
        return cls(host=host)

    # ── Request helpers ───────────────────────────────────────────────────────

    def _headers(self) -> dict[str, str]:
        if not self.token:
            var = "GITHUB_IBM_TOKEN" if self.host == GitHubHost.IBM else "GITHUB_TOKEN"
            raise GitHubError(500, f"{var} not set")
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
        }
        # GHE v3 API does not always require the version header, but it is harmless
        if self.host == GitHubHost.PUBLIC:
            headers["X-GitHub-Api-Version"] = "2022-11-28"
        return headers

    def url(self, path: str) -> str:
        """Build absolute API URL from a relative path like /repos/owner/repo."""
        return f"{self.base_url}/{path.lstrip('/')}"

    async def paginate(self, path: str, params: dict | None = None) -> list[dict]:
        """Fetch all pages. Use only for bounded endpoints."""
        url = self.url(path)
        results: list[dict] = []
        req_params = {**(params or {}), "per_page": 100, "page": 1}
        async with httpx.AsyncClient(timeout=30) as client:
            while True:
                resp = await client.get(url, headers=self._headers(), params=req_params)
                if resp.status_code != 200:
                    raise GitHubError(resp.status_code, resp.text)
                data = resp.json()
                if not data:
                    break
                results.extend(data)
                if len(data) < 100:
                    break
                req_params["page"] += 1
        return results

    async def fetch_pages_limited(
        self,
        path: str,
        params: dict | None = None,
        *,
        per_page: int = 30,
        page: int = 1,
        max_pages: int = 1,
    ) -> list[dict]:
        per_page  = max(1, min(per_page, 100))
        page      = max(1, page)
        max_pages = max(1, min(max_pages, 10))
        url = self.url(path)
        results: list[dict] = []
        async with httpx.AsyncClient(timeout=30) as client:
            current_page = page
            for _ in range(max_pages):
                req_params = {**(params or {}), "per_page": per_page, "page": current_page}
                resp = await client.get(url, headers=self._headers(), params=req_params)
                if resp.status_code != 200:
                    raise GitHubError(resp.status_code, resp.text)
                data = resp.json()
                if not data:
                    break
                results.extend(data)
                if len(data) < per_page:
                    break
                current_page += 1
        return results

    async def get_one(self, path: str, params: dict | None = None) -> dict:
        url = self.url(path)
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, headers=self._headers(), params=params)
            if resp.status_code != 200:
                raise GitHubError(resp.status_code, resp.text)
            return resp.json()

    # ── Repo ──────────────────────────────────────────────────────────────────

    async def get_repo_info(self, owner: str, repo: str) -> dict:
        r = await self.get_one(f"/repos/{owner}/{repo}")
        return {
            "name":           r["full_name"],
            "description":    r.get("description"),
            "language":       r.get("language"),
            "stars":          r["stargazers_count"],
            "forks":          r["forks_count"],
            "open_issues":    r["open_issues_count"],
            "topics":         r.get("topics", []),
            "default_branch": r["default_branch"],
            "created_at":     r["created_at"],
            "updated_at":     r["updated_at"],
            "url":            r["html_url"],
        }

    async def list_repo_contributors(self, owner: str, repo: str) -> list[dict]:
        data = await self.paginate(f"/repos/{owner}/{repo}/contributors")
        return [
            {"login": c["login"], "contributions": c["contributions"], "url": c["html_url"]}
            for c in data
        ]

    async def list_repo_labels(self, owner: str, repo: str) -> list[dict]:
        data = await self.paginate(f"/repos/{owner}/{repo}/labels")
        return [
            {"name": l["name"], "color": l["color"], "description": l.get("description")}
            for l in data
        ]

    # ── Pull requests ─────────────────────────────────────────────────────────

    async def list_pull_requests(
        self,
        owner: str,
        repo: str,
        state: str = "all",
        sort: str = "created",
        direction: str = "desc",
        per_page: int = 30,
        page: int = 1,
        max_pages: int = 1,
    ) -> list[dict]:
        prs = await self.fetch_pages_limited(
            f"/repos/{owner}/{repo}/pulls",
            {"state": state, "sort": sort, "direction": direction},
            per_page=per_page,
            page=page,
            max_pages=max_pages,
        )
        return [
            {
                "number":     pr["number"],
                "title":      pr["title"],
                "state":      pr["state"],
                "author":     pr["user"]["login"],
                "created_at": pr["created_at"],
                "updated_at": pr["updated_at"],
                "merged_at":  pr["merged_at"],
                "draft":      pr["draft"],
                "labels":     [l["name"] for l in pr.get("labels", [])],
                "url":        pr["html_url"],
            }
            for pr in prs
        ]

    async def get_pull_request_detail(self, owner: str, repo: str, pr_number: int) -> dict:
        pr = await self.get_one(f"/repos/{owner}/{repo}/pulls/{pr_number}")
        return {
            "number":        pr["number"],
            "title":         pr["title"],
            "state":         pr["state"],
            "author":        pr["user"]["login"],
            "body":          pr.get("body"),
            "created_at":    pr["created_at"],
            "merged_at":     pr["merged_at"],
            "draft":         pr["draft"],
            "labels":        [l["name"] for l in pr.get("labels", [])],
            "assignees":     [a["login"] for a in pr.get("assignees", [])],
            "reviewers":     [r["login"] for r in pr.get("requested_reviewers", [])],
            "commits":       pr["commits"],
            "additions":     pr["additions"],
            "deletions":     pr["deletions"],
            "changed_files": pr["changed_files"],
            "base":          pr["base"]["ref"],
            "head":          pr["head"]["ref"],
            "url":           pr["html_url"],
        }

    async def list_pr_reviews(self, owner: str, repo: str, pr_number: int) -> list[dict]:
        data = await self.paginate(f"/repos/{owner}/{repo}/pulls/{pr_number}/reviews")
        return [
            {
                "reviewer":     r["user"]["login"],
                "state":        r["state"],
                "body":         r.get("body"),
                "submitted_at": r["submitted_at"],
            }
            for r in data
        ]

    async def list_pr_comments(self, owner: str, repo: str, pr_number: int) -> list[dict]:
        data = await self.paginate(f"/repos/{owner}/{repo}/pulls/{pr_number}/comments")
        return [
            {
                "author":     c["user"]["login"],
                "body":       c["body"],
                "path":       c["path"],
                "line":       c.get("line"),
                "created_at": c["created_at"],
            }
            for c in data
        ]

    async def list_pr_commits(self, owner: str, repo: str, pr_number: int) -> list[dict]:
        data = await self.paginate(f"/repos/{owner}/{repo}/pulls/{pr_number}/commits")
        return [
            {
                "sha":     c["sha"][:7],
                "author":  c["commit"]["author"]["name"],
                "message": c["commit"]["message"].split("\n")[0],
                "date":    c["commit"]["author"]["date"],
            }
            for c in data
        ]

    async def list_pr_files(self, owner: str, repo: str, pr_number: int) -> list[dict]:
        data = await self.paginate(f"/repos/{owner}/{repo}/pulls/{pr_number}/files")
        return [
            {
                "filename":  f["filename"],
                "status":    f["status"],
                "additions": f["additions"],
                "deletions": f["deletions"],
                "changes":   f["changes"],
                "patch":     f.get("patch"),
            }
            for f in data
        ]

    async def get_pr_full_detail(self, owner: str, repo: str, pr_number: int) -> dict:
        detail, reviews, inline_comments, commits, files, discussion = await asyncio.gather(
            self.get_pull_request_detail(owner, repo, pr_number),
            self.list_pr_reviews(owner, repo, pr_number),
            self.list_pr_comments(owner, repo, pr_number),
            self.list_pr_commits(owner, repo, pr_number),
            self.list_pr_files(owner, repo, pr_number),
            self.list_issue_comments(owner, repo, pr_number),
        )
        if detail.get("merged_at"):
            detail["state"] = "merged"
        return {
            "detail":              detail,
            "reviews":             reviews,
            "inline_comments":     inline_comments,
            "discussion_comments": discussion,
            "commits":             commits,
            "files":               files,
        }

    # ── Issues ────────────────────────────────────────────────────────────────

    async def list_issues(
        self,
        owner: str,
        repo: str,
        state: str = "all",
        sort: str = "created",
        direction: str = "desc",
        labels: str = "",
        per_page: int = 30,
        page: int = 1,
        max_pages: int = 1,
    ) -> list[dict]:
        params: dict[str, Any] = {"state": state, "sort": sort, "direction": direction}
        if labels:
            params["labels"] = labels
        all_items = await self.fetch_pages_limited(
            f"/repos/{owner}/{repo}/issues",
            params,
            per_page=per_page,
            page=page,
            max_pages=max_pages,
        )
        issues = [i for i in all_items if "pull_request" not in i]
        return [
            {
                "number":     i["number"],
                "title":      i["title"],
                "state":      i["state"],
                "author":     i["user"]["login"],
                "created_at": i["created_at"],
                "updated_at": i["updated_at"],
                "closed_at":  i["closed_at"],
                "labels":     [l["name"] for l in i.get("labels", [])],
                "comments":   i["comments"],
                "url":        i["html_url"],
            }
            for i in issues
        ]

    async def get_issue_detail(self, owner: str, repo: str, issue_number: int) -> dict:
        i = await self.get_one(f"/repos/{owner}/{repo}/issues/{issue_number}")
        return {
            "number":    i["number"],
            "title":     i["title"],
            "state":     i["state"],
            "author":    i["user"]["login"],
            "body":      i.get("body"),
            "created_at": i["created_at"],
            "closed_at": i["closed_at"],
            "labels":    [l["name"] for l in i.get("labels", [])],
            "assignees": [a["login"] for a in i.get("assignees", [])],
            "comments":  i["comments"],
            "url":       i["html_url"],
        }

    async def list_issue_comments(self, owner: str, repo: str, issue_number: int) -> list[dict]:
        data = await self.paginate(f"/repos/{owner}/{repo}/issues/{issue_number}/comments")
        return [
            {
                "author":     c["user"]["login"],
                "body":       c["body"],
                "created_at": c["created_at"],
                "url":        c["html_url"],
            }
            for c in data
        ]

    async def list_issue_events(self, owner: str, repo: str, issue_number: int) -> list[dict]:
        data = await self.paginate(f"/repos/{owner}/{repo}/issues/{issue_number}/events")
        return [
            {
                "event":      e["event"],
                "actor":      e["actor"]["login"] if e.get("actor") else None,
                "created_at": e["created_at"],
                "label":      e["label"]["name"] if e.get("label") else None,
            }
            for e in data
        ]

    async def get_issue_full_detail(self, owner: str, repo: str, issue_number: int) -> dict:
        detail, comments, events = await asyncio.gather(
            self.get_issue_detail(owner, repo, issue_number),
            self.list_issue_comments(owner, repo, issue_number),
            self.list_issue_events(owner, repo, issue_number),
        )
        return {"detail": detail, "comments": comments, "events": events}

    # ── Structure & history ───────────────────────────────────────────────────

    async def get_readme(self, owner: str, repo: str) -> dict | None:
        try:
            data = await self.get_one(f"/repos/{owner}/{repo}/readme")
            content = ""
            if data.get("content"):
                content = base64.b64decode(data["content"]).decode("utf-8", errors="replace")
            return {
                "name":    data.get("name"),
                "path":    data.get("path"),
                "size":    data.get("size"),
                "content": content[:50000],
                "url":     data.get("html_url"),
            }
        except GitHubError as e:
            if e.status_code == 404:
                return None
            raise

    async def list_branches(self, owner: str, repo: str) -> list[dict]:
        data = await self.paginate(f"/repos/{owner}/{repo}/branches")
        return [
            {
                "name":      b["name"],
                "protected": b.get("protected", False),
                "sha":       b["commit"]["sha"][:7],
            }
            for b in data
        ]

    async def list_commits(self, owner: str, repo: str, limit: int = 100) -> list[dict]:
        data = await self.paginate(
            f"/repos/{owner}/{repo}/commits",
            {"per_page": min(limit, 100)},
        )
        commits = data[:limit]
        return [
            {
                "sha":     c["sha"][:7],
                "author":  c["commit"]["author"]["name"] if c["commit"].get("author") else "unknown",
                "message": c["commit"]["message"].split("\n")[0],
                "date":    (
                    c["commit"]["author"]["date"]
                    if c["commit"].get("author")
                    else c["commit"]["committer"]["date"]
                ),
                "url": c["html_url"],
            }
            for c in commits
        ]

    async def get_repo_file_tree(self, owner: str, repo: str, max_files: int = 2000) -> list[dict]:
        """Recursive file tree (blobs only). Truncates very large repos."""
        r      = await self.get_one(f"/repos/{owner}/{repo}")
        branch = r["default_branch"]
        ref    = await self.get_one(f"/repos/{owner}/{repo}/git/ref/heads/{branch}")
        sha    = ref["object"]["sha"]
        tree   = await self.get_one(
            f"/repos/{owner}/{repo}/git/trees/{sha}",
            {"recursive": "1"},
        )
        files: list[dict] = []
        for item in tree.get("tree", []):
            if item.get("type") != "blob":
                continue
            path = item["path"]
            files.append({
                "path":      path,
                "size":      item.get("size", 0),
                "extension": path.rsplit(".", 1)[-1].lower() if "." in path else "",
            })
            if len(files) >= max_files:
                break
        return files

    # ── File content (batch) ──────────────────────────────────────────────────

    @staticmethod
    def _decode_content_payload(data: dict) -> str | None:
        if data.get("encoding") != "base64" or not data.get("content"):
            return None
        raw = base64.b64decode(data["content"]).decode("utf-8", errors="replace")
        return raw[:512_000] if len(raw) > 512_000 else raw

    async def _fetch_file_content(
        self,
        client: httpx.AsyncClient,
        owner: str,
        repo: str,
        path: str,
        *,
        ref: str | None = None,
    ) -> str | None:
        params: dict[str, str] = {}
        if ref:
            params["ref"] = ref
        encoded_path = path.replace("#", "%23")
        url = self.url(f"/repos/{owner}/{repo}/contents/{encoded_path}")

        last_exc: Exception | None = None
        for attempt in range(GITHUB_HTTP_RETRIES):
            try:
                resp = await client.get(url, headers=self._headers(), params=params or None)
                if resp.status_code == 404:
                    return None
                if resp.status_code in (403, 429):
                    last_exc = GitHubError(resp.status_code, resp.text)
                    await asyncio.sleep(min(30, 2 ** (attempt + 2)))
                    continue
                if resp.status_code != 200:
                    raise GitHubError(resp.status_code, resp.text)
                return self._decode_content_payload(resp.json())
            except GitHubError:
                raise
            except (
                httpx.ConnectTimeout,
                httpx.ReadTimeout,
                httpx.PoolTimeout,
                httpx.NetworkError,
            ) as exc:
                last_exc = exc
                if attempt < GITHUB_HTTP_RETRIES - 1:
                    await asyncio.sleep(1.5 * (attempt + 1))
                    continue
                return None
        if last_exc and isinstance(last_exc, GitHubError):
            raise last_exc
        return None

    async def get_file_content(
        self,
        owner: str,
        repo: str,
        path: str,
        *,
        ref: str | None = None,
    ) -> str | None:
        async with httpx.AsyncClient(timeout=GITHUB_HTTP_TIMEOUT) as client:
            try:
                return await self._fetch_file_content(client, owner, repo, path, ref=ref)
            except GitHubError as e:
                if e.status_code == 404:
                    return None
                raise

    async def get_file_contents_batch(
        self,
        owner: str,
        repo: str,
        paths: list[str],
        *,
        ref: str | None = None,
        concurrency: int | None = None,
    ) -> tuple[dict[str, str | None], dict[str, Any]]:
        if not paths:
            return {}, {"requested": 0, "fetched": 0, "failed": 0, "failed_paths": []}

        limit = max(1, min(concurrency if concurrency is not None else GITHUB_BATCH_CONCURRENCY, 10))
        results: dict[str, str | None] = {}
        failed_paths: list[str] = []
        sem = asyncio.Semaphore(limit)
        http_limits = httpx.Limits(
            max_connections=limit + 2,
            max_keepalive_connections=limit,
        )

        async with httpx.AsyncClient(timeout=GITHUB_HTTP_TIMEOUT, limits=http_limits) as client:

            async def _one(path: str) -> None:
                async with sem:
                    try:
                        content = await self._fetch_file_content(client, owner, repo, path, ref=ref)
                    except GitHubError:
                        content = None
                        failed_paths.append(path)
                    results[path] = content

            await asyncio.gather(*[_one(p) for p in paths])

        fetched = sum(1 for v in results.values() if v)
        return results, {
            "requested":    len(paths),
            "fetched":      fetched,
            "failed":       len(failed_paths),
            "failed_paths": failed_paths[:50],
        }

    # ── Search ────────────────────────────────────────────────────────────────

    async def search_issues_and_prs(
        self, owner: str, repo: str, query: str, kind: str = "both"
    ) -> list[dict]:
        type_filter = {"issue": " type:issue", "pr": " type:pr", "both": ""}.get(kind, "")
        q = f"{query} repo:{owner}/{repo}{type_filter}"
        data = await self.get_one("/search/issues", {"q": q, "per_page": 50})
        return [
            {
                "number":     i["number"],
                "title":      i["title"],
                "type":       "pr" if "pull_request" in i else "issue",
                "state":      i["state"],
                "author":     i["user"]["login"],
                "created_at": i["created_at"],
                "labels":     [l["name"] for l in i.get("labels", [])],
                "url":        i["html_url"],
            }
            for i in data.get("items", [])
        ]

    async def detect_dependency_files(
        self, owner: str, repo: str, tree_paths: list[str] | None = None
    ) -> list[dict]:
        if tree_paths is None:
            tree = await self.get_repo_file_tree(owner, repo, max_files=5000)
            tree_paths = [t["path"] for t in tree]
        found = []
        for path in tree_paths:
            name = path.split("/")[-1]
            if name in DEPENDENCY_FILES or path in DEPENDENCY_FILES:
                found.append({"path": path, "kind": name})
        return found


# ── Default public-GitHub client + module-level backward-compat functions ─────

_default_client = GitHubClient()  # uses GITHUB_TOKEN / GITHUB_API


def _get_client(client: GitHubClient | None) -> GitHubClient:
    """Return the provided client or the module-level default."""
    return client if client is not None else _default_client


# Dependency-file manifest
DEPENDENCY_FILES = frozenset({
    "package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
    "requirements.txt", "pyproject.toml", "Pipfile", "poetry.lock",
    "go.mod", "go.sum", "Cargo.toml", "Cargo.lock",
    "pom.xml", "build.gradle", "build.gradle.kts",
    "Gemfile", "composer.json", "Dockerfile", "docker-compose.yml",
})


# ── Backward-compatible module-level shims ────────────────────────────────────
# All accept an optional `client: GitHubClient | None = None` keyword argument
# so callers can pass an IBM client without breaking existing call sites.

async def paginate(url: str, params: dict | None = None) -> list[dict]:
    """Legacy helper — wraps the default client. Prefer client.paginate() for new code."""
    return await _default_client.paginate(url.replace(GITHUB_API, "").replace(_default_client.base_url, ""), params)


async def fetch_pages_limited(
    url: str,
    params: dict | None = None,
    *,
    per_page: int = 30,
    page: int = 1,
    max_pages: int = 1,
) -> list[dict]:
    path = url.replace(_default_client.base_url, "").replace(GITHUB_API, "")
    return await _default_client.fetch_pages_limited(path, params, per_page=per_page, page=page, max_pages=max_pages)


async def get_one(url: str, params: dict | None = None) -> dict:
    path = url.replace(_default_client.base_url, "").replace(GITHUB_API, "")
    return await _default_client.get_one(path, params)


async def get_repo_info(owner: str, repo: str, *, client: GitHubClient | None = None) -> dict:
    return await _get_client(client).get_repo_info(owner, repo)


async def list_repo_contributors(owner: str, repo: str, *, client: GitHubClient | None = None) -> list[dict]:
    return await _get_client(client).list_repo_contributors(owner, repo)


async def list_repo_labels(owner: str, repo: str, *, client: GitHubClient | None = None) -> list[dict]:
    return await _get_client(client).list_repo_labels(owner, repo)


async def list_pull_requests(
    owner: str,
    repo: str,
    state: str = "all",
    sort: str = "created",
    direction: str = "desc",
    per_page: int = 30,
    page: int = 1,
    max_pages: int = 1,
    *,
    client: GitHubClient | None = None,
) -> list[dict]:
    return await _get_client(client).list_pull_requests(
        owner, repo, state=state, sort=sort, direction=direction,
        per_page=per_page, page=page, max_pages=max_pages,
    )


async def get_pull_request_detail(owner: str, repo: str, pr_number: int, *, client: GitHubClient | None = None) -> dict:
    return await _get_client(client).get_pull_request_detail(owner, repo, pr_number)


async def list_pr_reviews(owner: str, repo: str, pr_number: int, *, client: GitHubClient | None = None) -> list[dict]:
    return await _get_client(client).list_pr_reviews(owner, repo, pr_number)


async def list_pr_comments(owner: str, repo: str, pr_number: int, *, client: GitHubClient | None = None) -> list[dict]:
    return await _get_client(client).list_pr_comments(owner, repo, pr_number)


async def list_pr_commits(owner: str, repo: str, pr_number: int, *, client: GitHubClient | None = None) -> list[dict]:
    return await _get_client(client).list_pr_commits(owner, repo, pr_number)


async def list_pr_files(owner: str, repo: str, pr_number: int, *, client: GitHubClient | None = None) -> list[dict]:
    return await _get_client(client).list_pr_files(owner, repo, pr_number)


async def get_pr_full_detail(owner: str, repo: str, pr_number: int, *, client: GitHubClient | None = None) -> dict:
    return await _get_client(client).get_pr_full_detail(owner, repo, pr_number)


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
    *,
    client: GitHubClient | None = None,
) -> list[dict]:
    return await _get_client(client).list_issues(
        owner, repo, state=state, sort=sort, direction=direction,
        labels=labels, per_page=per_page, page=page, max_pages=max_pages,
    )


async def get_issue_detail(owner: str, repo: str, issue_number: int, *, client: GitHubClient | None = None) -> dict:
    return await _get_client(client).get_issue_detail(owner, repo, issue_number)


async def list_issue_comments(owner: str, repo: str, issue_number: int, *, client: GitHubClient | None = None) -> list[dict]:
    return await _get_client(client).list_issue_comments(owner, repo, issue_number)


async def list_issue_events(owner: str, repo: str, issue_number: int, *, client: GitHubClient | None = None) -> list[dict]:
    return await _get_client(client).list_issue_events(owner, repo, issue_number)


async def get_issue_full_detail(owner: str, repo: str, issue_number: int, *, client: GitHubClient | None = None) -> dict:
    return await _get_client(client).get_issue_full_detail(owner, repo, issue_number)


async def get_readme(owner: str, repo: str, *, client: GitHubClient | None = None) -> dict | None:
    return await _get_client(client).get_readme(owner, repo)


async def list_branches(owner: str, repo: str, *, client: GitHubClient | None = None) -> list[dict]:
    return await _get_client(client).list_branches(owner, repo)


async def list_commits(owner: str, repo: str, limit: int = 100, *, client: GitHubClient | None = None) -> list[dict]:
    return await _get_client(client).list_commits(owner, repo, limit)


async def get_repo_file_tree(owner: str, repo: str, max_files: int = 2000, *, client: GitHubClient | None = None) -> list[dict]:
    return await _get_client(client).get_repo_file_tree(owner, repo, max_files)


async def get_file_content(
    owner: str,
    repo: str,
    path: str,
    *,
    ref: str | None = None,
    client: GitHubClient | None = None,
) -> str | None:
    return await _get_client(client).get_file_content(owner, repo, path, ref=ref)


async def get_file_contents_batch(
    owner: str,
    repo: str,
    paths: list[str],
    *,
    ref: str | None = None,
    concurrency: int | None = None,
    client: GitHubClient | None = None,
) -> tuple[dict[str, str | None], dict[str, Any]]:
    return await _get_client(client).get_file_contents_batch(
        owner, repo, paths, ref=ref, concurrency=concurrency
    )


async def detect_dependency_files(
    owner: str,
    repo: str,
    tree_paths: list[str] | None = None,
    *,
    client: GitHubClient | None = None,
) -> list[dict]:
    return await _get_client(client).detect_dependency_files(owner, repo, tree_paths)


async def search_issues_and_prs(
    owner: str,
    repo: str,
    query: str,
    kind: str = "both",
    *,
    client: GitHubClient | None = None,
) -> list[dict]:
    return await _get_client(client).search_issues_and_prs(owner, repo, query, kind)