"use client";

import type { ChangeImpact } from "@/lib/dependency-api";

const RISK_STYLES: Record<string, string> = {
  high: "border-red-200 bg-red-50 text-red-800",
  medium: "border-amber-200 bg-amber-50 text-amber-900",
  low: "border-emerald-200 bg-emerald-50 text-emerald-800",
  unknown: "border-[var(--app-border)] bg-[var(--app-elevated)] text-[var(--app-muted)]",
};

export default function BlastRadiusPanel({
  impact,
}: {
  impact: ChangeImpact;
  onClose?: () => void;
}) {
  const risk = impact.summary.risk_level;
  const target =
    impact.target.resolved
      ? impact.target.path
      : (impact.target as { requested_path?: string }).requested_path ?? impact.target.path;

  return (
    <section className="flex flex-col overflow-hidden bg-white/50">
      <div className="flex items-start justify-between gap-3 px-4 py-2.5">
        <div className="min-w-0">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-[var(--app-muted)]">
            Target file
          </p>
          <p className="truncate font-mono text-[11px] text-[var(--app-heading)]">{target}</p>
        </div>
        <span
          className={`shrink-0 animate-fade-in rounded-full border px-2.5 py-1 text-[10px] font-bold uppercase tracking-wide ${RISK_STYLES[risk] ?? RISK_STYLES.unknown}`}
        >
          {risk}
        </span>
      </div>

      <p className="line-clamp-2 px-4 pb-2 text-[11px] leading-snug text-[var(--app-muted)]">
        {impact.summary.message}
      </p>

      <div className="grid grid-cols-4 gap-1.5 px-4 pb-3">
        {[
          { label: "Direct importers", value: impact.summary.direct_dependent_count ?? 0 },
          { label: "Transitive", value: impact.summary.transitive_dependent_count ?? 0 },
          { label: "Imports", value: impact.summary.direct_dependency_count ?? 0 },
          { label: "Related PRs", value: impact.summary.related_pr_count ?? 0 },
        ].map((s, idx) => (
          <div
            key={s.label}
            className="animate-fade-slide-up rounded-lg border border-[var(--app-border)]/80 bg-white px-2 py-1.5 text-center shadow-sm"
            style={{ animationDelay: `${idx * 50}ms` }}
          >
            <span className="block text-[8px] uppercase tracking-wider text-[var(--app-muted)]">
              {s.label}
            </span>
            <span className="text-base font-bold text-[var(--app-heading)]">{s.value}</span>
          </div>
        ))}
      </div>

    </section>
  );
}
