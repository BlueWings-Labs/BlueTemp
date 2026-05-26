"""
Collect a repository snapshot for intelligence analysis.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

import github_services as gh
from github_services import GitHubClient


async def collect_repository_snapshot(
    owner: str,
    repo: str,
    *,
    pr_file_sample: int = 25,
    client: GitHubClient | None = None,
) -> dict[str, Any]:
    """
    Gather repository data for analysis.
    PR file churn is sampled from recent merged/closed PRs to limit API calls.

    Pass `client=GitHubClient(host='ibm')` to target GitHub Enterprise.
    """
    info, readme, branches, contributors, pulls, issues, commits, tree = await asyncio.gather(
        gh.get_repo_info(owner, repo, client=client),
        gh.get_readme(owner, repo, client=client),
        gh.list_branches(owner, repo, client=client),
        gh.list_repo_contributors(owner, repo, client=client),
        gh.list_pull_requests(owner, repo, state="all", client=client),
        gh.list_issues(owner, repo, state="all", client=client),
        gh.list_commits(owner, repo, limit=80, client=client),
        gh.get_repo_file_tree(owner, repo, client=client),
    )

    tree_paths = [f["path"] for f in tree]
    dependencies = await gh.detect_dependency_files(owner, repo, tree_paths, client=client)

    pr_file_changes: list[dict[str, Any]] = []
    sample_prs = sorted(
        [p for p in pulls if p.get("merged_at") or p.get("state") == "closed"],
        key=lambda p: p.get("merged_at") or p.get("updated_at") or "",
        reverse=True,
    )[:pr_file_sample]

    async def _pr_files(pr: dict) -> None:
        try:
            files = await gh.list_pr_files(owner, repo, pr["number"], client=client)
            for f in files:
                pr_file_changes.append({
                    "pr_number": pr["number"],
                    "pr_title":  pr["title"],
                    "merged_at": pr.get("merged_at"),
                    "filename":  f["filename"],
                    "additions": f["additions"],
                    "deletions": f["deletions"],
                    "status":    f["status"],
                })
        except Exception:
            pass

    if sample_prs:
        await asyncio.gather(*[_pr_files(pr) for pr in sample_prs])

    return {
        "collected_at":    datetime.now(timezone.utc).isoformat(),
        "owner":           owner,
        "repo":            repo,
        "github_host":     (client.host.value if client else "github.com"),
        "info":            info,
        "readme":          readme,
        "branches":        branches,
        "contributors":    contributors,
        "pull_requests":   pulls,
        "issues":          issues,
        "commits":         commits,
        "file_tree":       tree,
        "dependencies":    dependencies,
        "pr_file_changes": pr_file_changes,
        "stats": {
            "pr_count":           len(pulls),
            "issue_count":        len(issues),
            "commit_sample":      len(commits),
            "file_count":         len(tree),
            "branch_count":       len(branches),
            "contributor_count":  len(contributors),
        },
    }