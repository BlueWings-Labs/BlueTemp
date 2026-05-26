"use client";

import { Suspense, useCallback, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import AppShell from "../components/AppShell";
import PageHero from "../components/PageHero";
import StepFooter from "../components/StepFooter";
import DependencyGraphView, {
  type ImpactHighlight,
} from "../components/DependencyGraphView";
import FileTreePanel from "../components/FileTreePanel";
import BlastRadiusBottomPanel from "../components/BlastRadiusBottomPanel";
import LoadingIndicator from "../components/LoadingIndicator";
import type { InsightGraph } from "@/lib/impact-insight-graph";
import {
  fetchDependencyGraph,
  fetchChangeImpact,
  type ChangeImpact,
  type DependencyGraph,
} from "@/lib/dependency-api";
import { parseRepoUrl } from "@/lib/parse-repo";

function DependenciesContent() {
  const searchParams = useSearchParams();
  const [input, setInput] = useState(searchParams.get("repo") ?? "");
  const [loading, setLoading] = useState(false);
  const [impactLoading, setImpactLoading] = useState(false);
  const [error, setError] = useState("");
  const [graph, setGraph] = useState<DependencyGraph | null>(null);
  const [impact, setImpact] = useState<ChangeImpact | null>(null);
  const [selected, setSelected] = useState<string | null>(
    searchParams.get("focus") || null,
  );
  const [maxFiles, setMaxFiles] = useState(150);
  const [focusMode, setFocusMode] = useState(false);
  const [repoOwner, setRepoOwner] = useState("");
  const [repoName, setRepoName] = useState("");
  const [insightGraph, setInsightGraph] = useState<InsightGraph | null>(null);
  const [insightGraphLabel, setInsightGraphLabel] = useState<string | null>(null);

  const handleInsightGraph = useCallback(
    (g: InsightGraph | null, label?: string | null) => {
      setInsightGraph(g);
      setInsightGraphLabel(label ?? null);
    },
    [],
  );

  const impactHighlight: ImpactHighlight | null = useMemo(() => {
    if (!impact?.target.resolved || !impact.highlight) return null;
    const deps = new Set(
      (impact.highlight.dependent_paths ?? []).filter((p) => !p.startsWith("pkg:")),
    );
    const fwd = new Set(
      (impact.highlight.dependency_paths ?? []).filter((p) => !p.startsWith("pkg:")),
    );
    deps.delete(impact.target.path);
    fwd.delete(impact.target.path);
    return {
      targetPath: impact.target.path,
      dependentPaths: deps,
      dependencyPaths: fwd,
    };
  }, [impact]);

  async function runAnalysis(focusPath?: string) {
    const parsed = parseRepoUrl(input);
    if (!parsed) {
      setError("Enter owner/repo or a GitHub URL");
      return;
    }
    setError("");
    setLoading(true);
    if (!focusPath) {
      setGraph(null);
      setImpact(null);
    }

    try {
      const data = await fetchDependencyGraph(parsed.owner, parsed.repo, {
        maxFiles,
        focusPath: focusPath ?? (focusMode && selected ? selected : undefined),
        maxDepth: focusPath || (focusMode && selected) ? 4 : undefined,
        includePackages: true,
      });
      setGraph(data);
      setRepoOwner(parsed.owner);
      setRepoName(parsed.repo);
      if (focusPath) setSelected(focusPath);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Analysis failed";
      setError(
        msg.includes("Failed to fetch")
          ? "Cannot reach API. Run: uvicorn api:app --reload --port 8000"
          : msg,
      );
    } finally {
      setLoading(false);
    }
  }

  async function runBlastRadius(path?: string) {
    const target = path ?? selected;
    const parsed = parseRepoUrl(input);
    if (!parsed) {
      setError("Enter owner/repo first");
      return;
    }
    if (!target) {
      setError("Select a file in the tree or graph, then run blast radius");
      return;
    }

    setError("");
    setImpactLoading(true);
    setSelected(target);

    try {
      const data = await fetchChangeImpact(parsed.owner, parsed.repo, target, {
        maxFiles,
      });
      setImpact(data);
      setInsightGraph(null);
      setInsightGraphLabel(null);
      setRepoOwner(parsed.owner);
      setRepoName(parsed.repo);
      if (!data.target.resolved) {
        setError(data.summary.message);
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Blast radius analysis failed");
      setImpact(null);
    } finally {
      setImpactLoading(false);
    }
  }

  function exportJson() {
    if (!graph) return;
    const blob = new Blob([JSON.stringify(graph, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${graph.repository.owner}-${graph.repository.repo}-deps.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <AppShell workflow="dependencies">
      <PageHero
        step={2}
        title="Code dependency graph"
        description="Map imports across the repo. Select a file and run blast radius to see who depends on it and related PR history."
      >
        <form
          className="card flex flex-wrap items-center gap-3 p-3"
          onSubmit={(e) => {
            e.preventDefault();
            runAnalysis();
          }}
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="owner/repo or github.com/…"
            className="input-field min-w-[200px] flex-1"
          />
          <label className="flex items-center gap-2 text-xs text-[var(--app-muted)]">
            Max files
            <input
              type="number"
              min={50}
              max={800}
              value={maxFiles}
              onChange={(e) => setMaxFiles(Number(e.target.value))}
              className="w-16 rounded-lg border border-[var(--app-border)] bg-[var(--app-base)] px-2 py-1 text-[var(--app-heading)]"
            />
          </label>
          <label className="flex items-center gap-2 text-xs text-[var(--app-muted)]">
            <input
              type="checkbox"
              checked={focusMode}
              onChange={(e) => setFocusMode(e.target.checked)}
              className="accent-[var(--brand-mid)]"
            />
            Focus on click
          </label>
          <button type="submit" disabled={loading || impactLoading} className="btn-primary py-2">
            {loading ? "Analyzing…" : "Build graph"}
          </button>
          <button
            type="button"
            disabled={!graph || loading || impactLoading || !selected}
            onClick={() => runBlastRadius()}
            className="rounded-xl border border-amber-300 bg-amber-50 px-4 py-2 text-xs font-semibold text-amber-900 transition hover:bg-amber-100 disabled:opacity-50"
          >
            {impactLoading ? "Scanning…" : "Blast radius"}
          </button>
          {graph && (
            <button
              type="button"
              onClick={exportJson}
              className="rounded-xl border border-[var(--app-border)] px-4 py-2 text-xs font-medium text-[var(--app-muted)] hover:text-[var(--app-heading)]"
            >
              Export JSON
            </button>
          )}
        </form>
        {error && (
          <p className="mt-3 rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-2 text-sm text-red-300">
            {error}
          </p>
        )}
      </PageHero>

      {(loading || impactLoading) && (
        <LoadingIndicator
          message={
            impactLoading
              ? "Computing blast radius (graph + PR history)…"
              : "Building dependency graph…"
          }
          size="lg"
        />
      )}

      {graph && !loading && (
        <>
          <div className="mb-2 flex flex-wrap gap-2">
            {[
              `${graph.stats.file_count} files`,
              `${graph.stats.edge_count} edges`,
              `${graph.stats.package_count} packages`,
            ].map((label) => (
              <span
                key={label}
                className="rounded-lg border border-[var(--app-border)] bg-[var(--app-elevated)] px-3 py-1 text-xs text-[var(--app-muted)]"
              >
                {label}
              </span>
            ))}
            {impact && (
              <span
                className={`rounded-lg border px-3 py-1 text-xs font-medium ${
                  impact.summary.risk_level === "high"
                    ? "border-red-200 bg-red-50 text-red-800"
                    : impact.summary.risk_level === "medium"
                      ? "border-amber-200 bg-amber-50 text-amber-900"
                      : "border-emerald-200 bg-emerald-50 text-emerald-800"
                }`}
              >
                Blast radius: {impact.summary.risk_level}
              </span>
            )}
            {graph.meta.truncated && (
              <span className="rounded-lg border border-amber-500/30 px-3 py-1 text-xs text-amber-300">
                truncated
              </span>
            )}
          </div>

          <div className="grid gap-3 lg:grid-cols-[minmax(180px,220px)_minmax(0,1fr)]">
            <FileTreePanel
              tree={graph.file_tree}
              selected={selected}
              onSelect={(path) => {
                setSelected(path);
                if (focusMode) runAnalysis(path);
              }}
            />

            <section className="card flex min-w-0 flex-col overflow-hidden shadow-md">
              <div className="border-b border-[var(--app-border)] bg-gradient-to-r from-[var(--brand-pale)]/40 via-white to-white px-4 py-3">
                <h3 className="text-sm font-bold text-[var(--app-heading)]">
                  Repository dependency map
                </h3>
                <p className="text-xs text-[var(--app-muted)]">
                  Full-size graph · click nodes to select · blast radius highlights in color
                </p>
              </div>
              <div className="p-3">
                <DependencyGraphView
                  graph={graph}
                  highlightPath={selected}
                  impact={impactHighlight}
                  onSelectFile={(path) => {
                    setSelected(path);
                    if (focusMode) runAnalysis(path);
                  }}
                />
              </div>
            </section>
          </div>

          {impact && !impactLoading && repoOwner && repoName && (
            <BlastRadiusBottomPanel
              impact={impact}
              owner={repoOwner}
              repo={repoName}
              insightGraph={insightGraph}
              insightGraphLabel={insightGraphLabel}
              onInsightGraph={handleInsightGraph}
              onClose={() => {
                setImpact(null);
                setInsightGraph(null);
                setInsightGraphLabel(null);
              }}
            />
          )}
        </>
      )}

      {!graph && !loading && (
        <section className="card flex flex-col items-center py-24 text-center">
          <p className="text-5xl opacity-20">⑂</p>
          <p className="mt-3 text-sm text-[var(--app-muted)]">
            Enter a repository to map file dependencies
          </p>
        </section>
      )}

      <StepFooter currentStep={2} />
    </AppShell>
  );
}

export default function DependenciesPage() {
  return (
    <Suspense
      fallback={
        <LoadingIndicator layout="fullscreen" message="Loading dependencies…" size="xl" />
      }
    >
      <DependenciesContent />
    </Suspense>
  );
}
