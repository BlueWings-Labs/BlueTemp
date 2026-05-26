"use client";

import Avatar from "./ui/Avatar";

export interface Contributor {
  login: string;
  contributions: number;
  avatar: string;
  url: string;
}

export default function ContributorsGrid({ contributors }: { contributors: Contributor[] }) {
  if (!contributors.length) {
    return (
      <div className="card flex flex-col items-center justify-center py-14 text-center">
        <p className="text-sm text-[var(--app-muted)]">No contributors found</p>
      </div>
    );
  }

  return (
    <div className="card overflow-hidden">
      <div className="grid grid-cols-1 divide-y divide-[var(--app-border)] sm:grid-cols-2 sm:divide-y-0 lg:grid-cols-3">
        {contributors.map((c) => (
          <a
            key={c.login}
            href={c.url}
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-2.5 px-3 py-2.5 transition-colors hover:bg-[var(--app-elevated)] sm:border-r sm:border-[var(--app-border)] sm:last:border-r-0"
          >
            <Avatar src={c.avatar} alt={c.login} size="sm" />
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium text-[var(--brand-royal)]">{c.login}</p>
              <p className="text-[10px] text-[var(--app-muted)]">
                {c.contributions.toLocaleString()} contributions
              </p>
            </div>
          </a>
        ))}
      </div>
    </div>
  );
}
