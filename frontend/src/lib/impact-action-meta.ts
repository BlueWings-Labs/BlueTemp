import type { ImpactQuickAction } from "./dependency-api";

export const ACTION_META: Record<
  string,
  { icon: string; hint: string; color: string }
> = {
  blast_map: {
    icon: "🗺️",
    hint: "Full impact neighborhood",
    color: "from-blue-500/10 to-sky-500/5",
  },
  explain_file: {
    icon: "📄",
    hint: "Exports, functions & roles",
    color: "from-indigo-500/10 to-violet-500/5",
  },
  refactor_risk: {
    icon: "⚠️",
    hint: "What breaks if you change this",
    color: "from-amber-500/15 to-orange-500/5",
  },
  dependents_layers: {
    icon: "↗️",
    hint: "Who imports this file",
    color: "from-orange-500/10 to-amber-500/5",
  },
  test_matrix: {
    icon: "🧪",
    hint: "What to test before merge",
    color: "from-cyan-500/10 to-teal-500/5",
  },
  imports_chain: {
    icon: "📦",
    hint: "Upstream dependencies",
    color: "from-violet-500/10 to-purple-500/5",
  },
  pr_activity: {
    icon: "🔀",
    hint: "Recent PRs on this file",
    color: "from-emerald-500/10 to-green-500/5",
  },
  review_checklist: {
    icon: "✅",
    hint: "Pre-merge review steps",
    color: "from-rose-500/10 to-red-500/5",
  },
};

export function metaForAction(action: ImpactQuickAction) {
  return (
    ACTION_META[action.id] ?? {
      icon: "💬",
      hint: action.prompt.slice(0, 48) + (action.prompt.length > 48 ? "…" : ""),
      color: "from-slate-500/10 to-slate-500/5",
    }
  );
}
