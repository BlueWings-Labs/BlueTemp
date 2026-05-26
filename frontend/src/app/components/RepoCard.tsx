"use client";

import Avatar from "./ui/Avatar";

export interface RepoInfo {
  name: string;
  description: string | null;
  language: string | null;
  stars: number;
  forks: number;
  open_issues: number;
  topics: string[];
  default_branch: string;
  created_at: string;
  updated_at: string;
  url: string;
  avatar?: string;
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="stat-chip">
      <span className="text-[10px] font-medium uppercase tracking-wider text-[var(--app-muted)]">
        {label}
      </span>
      <span className="text-sm font-semibold text-[var(--app-heading)]">{value}</span>
    </div>
  );
}

export default function RepoCard({ info }: { info: RepoInfo }) {
  return (
    <section className="card mb-5 overflow-hidden">
      <div className="flex items-start gap-3 border-b border-[var(--app-border)] px-4 py-3">
        <Avatar src={info.avatar} alt={info.name} size="md" />
        <div className="min-w-0 flex-1">
          <a
            href={info.url}
            target="_blank"
            rel="noreferrer"
            className="text-base font-semibold text-[var(--brand-royal)] hover:underline"
          >
            {info.name}
          </a>
          {info.description && (
            <p className="mt-0.5 line-clamp-2 text-xs leading-relaxed text-[var(--app-muted)]">
              {info.description}
            </p>
          )}
        </div>
        {info.language && (
          <span className="pill shrink-0 border border-[var(--app-border)] bg-[var(--app-elevated)] normal-case text-[var(--app-text)]">
            <span className="h-2 w-2 rounded-full bg-amber-400" />
            {info.language}
          </span>
        )}
      </div>

      <div className="grid grid-cols-2 gap-2 p-3 sm:grid-cols-4">
        <Stat label="Stars" value={info.stars.toLocaleString()} />
        <Stat label="Forks" value={info.forks.toLocaleString()} />
        <Stat label="Open issues" value={info.open_issues.toLocaleString()} />
        <Stat label="Branch" value={info.default_branch} />
      </div>

      {info.topics?.length > 0 && (
        <div className="flex flex-wrap gap-1.5 border-t border-[var(--app-border)] px-4 py-2.5">
          {info.topics.map((t) => (
            <span
              key={t}
              className="rounded-full border border-[var(--brand-pale)] bg-[var(--brand-pale)] px-2 py-0.5 text-[10px] font-medium text-[var(--brand-deep)]"
            >
              {t}
            </span>
          ))}
        </div>
      )}
    </section>
  );
}
