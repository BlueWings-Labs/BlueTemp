"use client";

import BlastRadiusPanel from "./BlastRadiusPanel";
import BlastRadiusChat from "./BlastRadiusChat";
import InsightGraphSection from "./InsightGraphSection";
import type { ChangeImpact } from "@/lib/dependency-api";
import type { InsightGraph } from "@/lib/impact-insight-graph";

export default function BlastRadiusBottomPanel({
  impact,
  owner,
  repo,
  insightGraph,
  insightGraphLabel,
  onInsightGraph,
  onClose,
}: {
  impact: ChangeImpact;
  owner: string;
  repo: string;
  insightGraph: InsightGraph | null;
  insightGraphLabel: string | null;
  onInsightGraph: (g: InsightGraph | null, label?: string | null) => void;
  onClose: () => void;
}) {
  if (!impact.target.resolved) {
    return (
      <section className="card mt-3 p-4 text-sm text-[var(--app-muted)]">
        Could not resolve file in the graph. Increase max files or choose another path.
      </section>
    );
  }

  return (
    <section className="card mt-3 overflow-hidden shadow-md animate-fade-slide-up">
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--app-border)] bg-gradient-to-r from-amber-50/80 via-white to-[var(--brand-pale)]/40 px-4 py-3">
        <div>
          <h2 className="text-base font-bold text-[var(--app-heading)]">Blast radius analysis</h2>
          <p className="text-xs text-[var(--app-muted)]">
            Pick a topic → read AI answer → explore the insight graph (repo map above stays full size)
          </p>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="rounded-lg border border-[var(--app-border)] bg-white px-3 py-1.5 text-xs font-medium text-[var(--app-muted)] hover:text-red-600"
        >
          Close
        </button>
      </header>

      <BlastRadiusPanel impact={impact} />

      <BlastRadiusChat
        owner={owner}
        repo={repo}
        impact={impact}
        onInsightGraph={onInsightGraph}
        insightSlot={
          insightGraph && insightGraph.nodes.length > 0 ? (
            <InsightGraphSection
              graph={insightGraph}
              actionLabel={insightGraphLabel}
              onGraphChange={onInsightGraph}
            />
          ) : null
        }
      />
    </section>
  );
}
