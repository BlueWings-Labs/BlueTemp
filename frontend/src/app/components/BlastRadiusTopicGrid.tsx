"use client";

import type { ImpactQuickAction } from "@/lib/dependency-api";
import { metaForAction } from "@/lib/impact-action-meta";

export default function BlastRadiusTopicGrid({
  actions,
  activeActionId,
  loading,
  onSelect,
}: {
  actions: ImpactQuickAction[];
  activeActionId: string | null;
  loading: boolean;
  onSelect: (action: ImpactQuickAction) => void;
}) {
  return (
    <div className="border-b border-[var(--app-border)] bg-white px-4 py-4">
      <h4 className="text-sm font-semibold text-[var(--app-heading)]">
        Graph topics — pick one to ask AI
      </h4>
      <p className="mt-0.5 text-xs text-[var(--app-muted)]">
        Each button builds an insight graph in the section below
      </p>
      <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-7">
        {actions.map((action, idx) => {
          const meta = metaForAction(action);
          const isActive = activeActionId === action.id;
          return (
            <button
              key={action.id}
              type="button"
              disabled={loading}
              onClick={() => onSelect(action)}
              title={action.prompt}
              className={`topic-card animate-fade-slide-up min-h-[72px] bg-gradient-to-br ${meta.color} ${
                isActive ? "topic-card-active" : ""
              }`}
              style={{ animationDelay: `${idx * 40}ms` }}
            >
              <span className="text-base" aria-hidden>
                {meta.icon}
              </span>
              <span className="mt-1 block text-xs font-semibold leading-tight text-[var(--app-heading)]">
                {action.label}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
