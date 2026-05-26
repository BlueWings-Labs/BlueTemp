"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { WORKFLOW, type WorkflowSlug } from "@/lib/brand";
import { parseRepoUrl } from "@/lib/parse-repo";
import { repoHref } from "@/lib/repo-query";

export default function WorkflowRail({ active }: { active: WorkflowSlug }) {
  const searchParams = useSearchParams();
  const repoKey = searchParams.get("repo");
  const parsed = repoKey ? parseRepoUrl(repoKey) : null;
  const idx = WORKFLOW.findIndex((w) => w.slug === active);

  return (
    <nav
      aria-label="Platform workflow"
      className="mb-8 w-full rounded-xl border border-[var(--app-border)] bg-[var(--app-surface)] p-1 shadow-sm"
    >
      <ol className="grid w-full grid-cols-2 gap-1 sm:grid-cols-3 lg:grid-cols-5">
        {WORKFLOW.map((item, i) => {
          const isActive = item.slug === active;
          const isPast = i < idx;
          const href = repoHref(item.href, parsed?.owner ?? null, parsed?.repo ?? null);
          return (
            <li key={item.slug} className="min-w-0">
              <Link
                href={href}
                className={`flex h-full min-h-[2.75rem] flex-col items-center justify-center gap-1 rounded-lg px-2 py-2.5 text-center transition sm:flex-row sm:gap-2 sm:px-3 ${
                  isActive
                    ? "bg-[var(--brand-royal)] text-white shadow-sm"
                    : isPast
                      ? "text-[var(--brand-deep)] hover:bg-[var(--app-elevated)]"
                      : "text-[var(--app-muted)] hover:bg-[var(--app-elevated)] hover:text-[var(--app-heading)]"
                }`}
              >
                <span
                  className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-md font-mono text-[11px] font-bold ${
                    isActive
                      ? "bg-white/20"
                      : isPast
                        ? "bg-[var(--brand-pale)] text-[var(--brand-deep)]"
                        : "bg-[var(--app-elevated)] text-[var(--app-muted)]"
                  }`}
                >
                  {String(item.step).padStart(2, "0")}
                </span>
                <span className="truncate text-[11px] font-semibold leading-tight sm:text-xs">
                  {item.short}
                </span>
              </Link>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
