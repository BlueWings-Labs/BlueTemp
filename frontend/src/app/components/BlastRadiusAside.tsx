"use client";

import BlastRadiusPanel from "./BlastRadiusPanel";
import BlastRadiusChat from "./BlastRadiusChat";
import type { ChangeImpact } from "@/lib/dependency-api";
import type { InsightGraph } from "@/lib/impact-insight-graph";

export default function BlastRadiusAside({
  impact,
  owner,
  repo,
  onClose,
  onInsightGraph,
}: {
  impact: ChangeImpact;
  owner: string;
  repo: string;
  onClose: () => void;
  onInsightGraph?: (graph: InsightGraph | null, label?: string) => void;
}) {
  if (!impact.target.resolved) {
    return (
      <section className="impact-studio p-5 text-sm text-[var(--app-muted)] animate-fade-in">
        Could not resolve file in graph. Try increasing max files or pick another path.
      </section>
    );
  }

  return (
    <aside className="impact-studio flex min-h-0 flex-col lg:sticky lg:top-4 lg:max-h-[calc(100vh-6rem)] animate-fade-slide-up">
      <header className="border-b border-[var(--app-border)]/80 bg-gradient-to-r from-amber-50/90 via-white to-[var(--brand-pale)]/50 px-4 py-3">
        <div className="flex items-start justify-between gap-2">
          <div>
            <h2 className="text-sm font-bold text-[var(--app-heading)]">Impact studio</h2>
            <p className="mt-0.5 text-[11px] text-[var(--app-muted)]">
              Analyze blast radius with AI — graphs update in the center
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-[var(--app-border)] bg-white px-2.5 py-1 text-[10px] font-medium text-[var(--app-muted)] transition hover:border-red-200 hover:text-red-600"
          >
            Close
          </button>
        </div>
      </header>

      <div className="max-h-[220px] shrink-0 overflow-hidden border-b border-[var(--app-border)]/80">
        <BlastRadiusPanel impact={impact} />
      </div>

      <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
        <BlastRadiusChat owner={owner} repo={repo} impact={impact} onInsightGraph={onInsightGraph} />
      </div>
    </aside>
  );
}
