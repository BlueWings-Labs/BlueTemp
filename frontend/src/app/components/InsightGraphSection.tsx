"use client";

import { useRef, useState } from "react";
import InsightGraphView from "./InsightGraphView";
import {
  parseInsightGraphJson,
  type InsightGraph,
} from "@/lib/impact-insight-graph";

interface Props {
  graph: InsightGraph;
  actionLabel?: string | null;
  onGraphChange: (graph: InsightGraph | null, label?: string | null) => void;
  embedded?: boolean;
}

export default function InsightGraphSection({
  graph,
  actionLabel,
  onGraphChange,
  embedded,
}: Props) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [importError, setImportError] = useState("");
  const graphKey = `${graph.kind}-${graph.nodes.length}-${actionLabel ?? ""}`;

  function exportJson() {
    const blob = new Blob([JSON.stringify(graph, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `insight-graph-${graph.kind}-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  function handleImportFile(file: File) {
    setImportError("");
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const parsed = JSON.parse(String(reader.result)) as unknown;
        const next = parseInsightGraphJson(parsed);
        onGraphChange(next, actionLabel ?? next.title);
      } catch (e: unknown) {
        setImportError(e instanceof Error ? e.message : "Invalid JSON file");
      }
    };
    reader.onerror = () => setImportError("Could not read file");
    reader.readAsText(file);
  }

  const content = (
    <div key={graphKey} className="animate-insight-reveal">
      <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3">
        <div className="flex items-start gap-3">
          <span
            className="graph-zone-label border-violet-200 bg-violet-100 text-violet-800"
            aria-hidden
          >
            ◆ Step 3
          </span>
          <div>
            <h3 className="text-sm font-bold text-[var(--app-heading)]">
              Insight graph
              {actionLabel ? (
                <span className="ml-2 font-normal text-violet-600">· {actionLabel}</span>
              ) : null}
            </h3>
            <p className="mt-0.5 text-xs text-[var(--app-muted)]">
              Visual map for your question — the repository graph above stays the same
            </p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button type="button" onClick={exportJson} className="btn-secondary px-3 py-1.5 text-xs">
            Export JSON
          </button>
          <button
            type="button"
            onClick={() => fileRef.current?.click()}
            className="btn-secondary px-3 py-1.5 text-xs"
          >
            Import JSON
          </button>
          <input
            ref={fileRef}
            type="file"
            accept=".json,application/json"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) handleImportFile(file);
              e.target.value = "";
            }}
          />
          <button
            type="button"
            onClick={() => onGraphChange(null, null)}
            className="rounded-xl border border-[var(--app-border)] px-3 py-1.5 text-xs font-medium text-[var(--app-muted)] transition hover:bg-[var(--app-elevated)]"
          >
            Hide graph
          </button>
        </div>
      </div>

      {importError && (
        <p className="mx-4 mb-2 animate-fade-in rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
          {importError}
        </p>
      )}

      <div className="mx-4 mb-4">
        <div className="insight-graph-panel">
          <InsightGraphView graph={graph} />
        </div>
      </div>
    </div>
  );

  return (
    <div className="border-t border-violet-200/60 bg-gradient-to-b from-violet-50/30 to-transparent">
      {content}
    </div>
  );
}
