"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import AppShell from "../components/AppShell";
import PageHero from "../components/PageHero";
import RepoCard from "../components/RepoCard";
import ItemList from "../components/ItemList";
import ContributorsGrid from "../components/ContributorsGrid";
import LoadingIndicator from "../components/LoadingIndicator";
import {
  getRepoInfo,
  getPullRequests,
  getIssues,
  getContributors,
  type RepoInfo,
  type ListItem,
  type Contributor,
} from "@/lib/github-api";
import { parseRepoUrl } from "@/lib/parse-repo";
import { WORKFLOW } from "@/lib/brand";

type Tab = "pulls" | "issues" | "contributors";

const TABS: { key: Tab; label: string }[] = [
  { key: "pulls", label: "Pull requests" },
  { key: "issues", label: "Issues" },
  { key: "contributors", label: "Contributors" },
];

export default function ExplorerPage() {
  const searchParams = useSearchParams();
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [repoInfo, setRepoInfo] = useState<RepoInfo | null>(null);
  const [tab, setTab] = useState<Tab>("pulls");
  const [pulls, setPulls] = useState<ListItem[]>([]);
  const [issues, setIssues] = useState<ListItem[]>([]);
  const [contributors, setContributors] = useState<Contributor[]>([]);
  const [repoOwner, setRepoOwner] = useState("");
  const [repoName, setRepoName] = useState("");

  useEffect(() => {
    const q = searchParams.get("repo");
    if (q) setInput(q);
  }, [searchParams]);

  const counts: Record<Tab, number> = {
    pulls: pulls.length,
    issues: issues.length,
    contributors: contributors.length,
  };

  async function handleSearch() {
    const parsed = parseRepoUrl(input);
    if (!parsed) {
      setError("Enter a valid GitHub URL or owner/repo (e.g. facebook/react)");
      return;
    }

    setError("");
    setLoading(true);
    setRepoInfo(null);
    setPulls([]);
    setIssues([]);
    setContributors([]);

    try {
      const [info, pullsData, issuesData, contribData] = await Promise.all([
        getRepoInfo(parsed.owner, parsed.repo),
        getPullRequests(parsed.owner, parsed.repo),
        getIssues(parsed.owner, parsed.repo),
        getContributors(parsed.owner, parsed.repo),
      ]);

      setRepoInfo(info);
      setPulls(pullsData);
      setIssues(issuesData);
      setContributors(contribData);
      setRepoOwner(parsed.owner);
      setRepoName(parsed.repo);
      setTab("pulls");
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "Fetch failed";
      if (message.includes("Failed to fetch") || message.includes("NetworkError")) {
        setError("Cannot reach the API. Run: uvicorn api:app --reload --port 8000");
      } else {
        setError(message);
      }
    } finally {
      setLoading(false);
    }
  }

  const nextStep = WORKFLOW[1];

  return (
    <AppShell workflow="explorer">
      <PageHero
        step={1}
        title="Repository Explorer"
        description="Search any public repository to browse pull requests, issues, and contributors with rich detail views."
      >
        <form
          className="card flex flex-col gap-2 p-2 sm:flex-row"
          onSubmit={(e) => {
            e.preventDefault();
            handleSearch();
          }}
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="owner/repo or github.com/…"
            className="input-field min-w-0 flex-1 border-0 bg-transparent focus:ring-0"
          />
          <button type="submit" disabled={loading} className="btn-primary shrink-0 px-6 py-2">
            {loading ? "Loading…" : "Explore repository"}
          </button>
        </form>
        {error && (
          <p className="mt-3 rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-2 text-sm text-red-300">
            {error}
          </p>
        )}
      </PageHero>

      {loading && (
        <LoadingIndicator message="Loading repository…" size="lg" />
      )}

      {repoInfo && !loading && (
        <div className="space-y-5">
          <RepoCard info={repoInfo} />

          <nav
            className="flex gap-1 rounded-xl border border-[var(--app-border)] bg-[var(--app-surface)] p-1"
            aria-label="Repository sections"
          >
            {TABS.map((t) => (
              <button
                key={t.key}
                type="button"
                onClick={() => setTab(t.key)}
                className={`flex flex-1 items-center justify-center gap-2 rounded-lg px-3 py-2 text-xs font-medium transition ${
                  tab === t.key
                    ? "bg-[var(--app-elevated)] text-[var(--app-heading)]"
                    : "text-[var(--app-muted)] hover:text-[var(--app-heading)]"
                }`}
              >
                {t.label}
                <span className="rounded-full bg-[var(--app-border)] px-2 py-0.5 text-[10px] tabular-nums">
                  {counts[t.key]}
                </span>
              </button>
            ))}
          </nav>

          {tab === "pulls" && (
            <ItemList
              key={`pulls-${repoOwner}-${repoName}`}
              items={pulls}
              kind="pr"
              owner={repoOwner}
              repo={repoName}
            />
          )}
          {tab === "issues" && (
            <ItemList
              key={`issues-${repoOwner}-${repoName}`}
              items={issues}
              kind="issue"
              owner={repoOwner}
              repo={repoName}
            />
          )}
          {tab === "contributors" && <ContributorsGrid contributors={contributors} />}
        </div>
      )}

      {!repoInfo && !loading && (
        <section className="card flex flex-col items-center py-20 text-center">
          <p className="text-4xl opacity-20">◎</p>
          <p className="mt-3 text-sm text-[var(--app-muted)]">Search a repository to begin</p>
        </section>
      )}

      {repoInfo && (
        <footer className="mt-10 flex items-center justify-between rounded-xl border border-[var(--app-border)] bg-[var(--app-elevated)] px-4 py-3">
          <p className="text-xs text-[var(--app-muted)]">
            Next: <strong className="text-[var(--app-heading)]">{nextStep.title}</strong>
          </p>
          <Link href={nextStep.href} className="btn-primary py-2 text-xs">
            Continue to {nextStep.short} →
          </Link>
        </footer>
      )}
    </AppShell>
  );
}
