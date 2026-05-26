"use client";

import { useState } from "react";
import Avatar from "./ui/Avatar";
import LoadingIndicator from "./LoadingIndicator";
import {
  PRDetailPanel,
  IssueDetailPanel,
  type PRFullDetail,
  type IssueFullDetail,
} from "./ItemDetailPanel";
import { getPRFullDetail, getIssueFullDetail } from "@/lib/github-api";

export interface Item {
  number: number;
  title: string;
  state: string;
  author: string;
  author_avatar?: string;
  created_at: string;
  merged_at?: string | null;
  closed_at?: string | null;
  labels: { name: string; color: string }[];
  comments?: number;
  url: string;
}

const stateStyles: Record<string, string> = {
  open: "bg-emerald-50 text-emerald-700 border-emerald-200",
  closed: "bg-slate-100 text-slate-600 border-slate-200",
  merged: "bg-violet-50 text-violet-700 border-violet-200",
};

function StateBadge({ state }: { state: string }) {
  return (
    <span
      className={`pill shrink-0 border ${stateStyles[state] ?? "border-[var(--app-border)] bg-[var(--app-elevated)] text-[var(--app-muted)]"}`}
    >
      {state}
    </span>
  );
}

function timeAgo(dateStr: string) {
  const diff = Date.now() - new Date(dateStr).getTime();
  const days = Math.floor(diff / 86400000);
  if (days === 0) return "today";
  if (days === 1) return "yesterday";
  if (days < 30) return `${days}d`;
  if (days < 365) return `${Math.floor(days / 30)}mo`;
  return `${Math.floor(days / 365)}y`;
}

export default function ItemList({
  items,
  kind,
  owner,
  repo,
}: {
  items: Item[];
  kind: "pr" | "issue";
  owner: string;
  repo: string;
}) {
  const [expanded, setExpanded] = useState<number | null>(null);
  const [loading, setLoading] = useState<number | null>(null);
  const [prDetails, setPrDetails] = useState<Record<number, PRFullDetail>>({});
  const [issueDetails, setIssueDetails] = useState<Record<number, IssueFullDetail>>({});
  const [error, setError] = useState<string>("");

  async function toggleItem(number: number) {
    if (expanded === number) {
      setExpanded(null);
      return;
    }

    setExpanded(number);
    setError("");

    const cached = kind === "pr" ? prDetails[number] : issueDetails[number];
    if (cached) return;

    setLoading(number);
    try {
      if (kind === "pr") {
        const data = await getPRFullDetail(owner, repo, number);
        setPrDetails((prev) => ({ ...prev, [number]: data }));
      } else {
        const data = await getIssueFullDetail(owner, repo, number);
        setIssueDetails((prev) => ({ ...prev, [number]: data }));
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load details");
      setExpanded(null);
    } finally {
      setLoading(null);
    }
  }

  if (!items.length) {
    return (
      <div className="card flex flex-col items-center justify-center py-14 text-center">
        <span className="mb-2 text-2xl opacity-30">{kind === "pr" ? "⑂" : "◎"}</span>
        <p className="text-sm text-[var(--app-muted)]">
          No {kind === "pr" ? "pull requests" : "issues"} found
        </p>
      </div>
    );
  }

  return (
    <div className="card overflow-hidden">
      {error && (
        <p className="border-b border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
          {error}
        </p>
      )}

      <div className="grid grid-cols-[auto_1fr_auto] gap-x-3 border-b border-[var(--app-border)] bg-[var(--app-elevated)] px-3 py-2 text-[10px] font-semibold uppercase tracking-wider text-[var(--app-muted)]">
        <span className="w-5" />
        <span>Title — click to expand</span>
        <span className="text-right">Meta</span>
      </div>

      <ul className="divide-y divide-[var(--app-border)]">
        {items.map((item) => {
          const isOpen = expanded === item.number;
          const isLoading = loading === item.number;

          return (
            <li key={item.number}>
              <button
                type="button"
                onClick={() => toggleItem(item.number)}
                className="grid w-full grid-cols-[auto_1fr_auto] items-center gap-x-3 px-3 py-2.5 text-left transition-colors hover:bg-[var(--app-elevated)]"
              >
                <Avatar src={item.author_avatar} alt={item.author} size="xs" />

                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <StateBadge state={item.state} />
                    <span className="truncate text-sm font-medium text-[var(--app-heading)]">
                      {item.title}
                    </span>
                  </div>
                  <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1">
                    <span className="text-[10px] text-[var(--app-faint)]">#{item.number}</span>
                    <span className="text-[10px] text-[var(--app-muted)]">{item.author}</span>
                    <span className="text-[10px] text-[var(--app-faint)]">·</span>
                    <span className="text-[10px] text-[var(--app-muted)]">
                      {timeAgo(item.created_at)}
                    </span>
                    {(item.comments ?? 0) > 0 && (
                      <span className="text-[10px] text-[var(--app-muted)]">
                        {item.comments} comments
                      </span>
                    )}
                    {item.labels.slice(0, 3).map((l) => (
                      <span
                        key={l.name}
                        style={{
                          backgroundColor: `#${l.color}22`,
                          color: `#${l.color}`,
                          borderColor: `#${l.color}55`,
                        }}
                        className="rounded border px-1.5 py-px text-[9px] font-medium"
                      >
                        {l.name}
                      </span>
                    ))}
                  </div>
                </div>

                <span className="text-xs text-[var(--app-faint)]" aria-hidden>
                  {isLoading ? "…" : isOpen ? "▾" : "▸"}
                </span>
              </button>

              {isOpen && !isLoading && kind === "pr" && prDetails[item.number] && (
                <PRDetailPanel data={prDetails[item.number]} />
              )}
              {isOpen && !isLoading && kind === "issue" && issueDetails[item.number] && (
                <IssueDetailPanel data={issueDetails[item.number]} />
              )}
              {isOpen && isLoading && (
                <div className="border-t border-[var(--app-border)] px-3 py-4">
                  <LoadingIndicator message="Loading full details…" size="sm" />
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
