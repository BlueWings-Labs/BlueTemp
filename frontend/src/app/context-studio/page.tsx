// @ts-nocheck
"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import AppShell from "../components/AppShell";
import PageHero from "../components/PageHero";
import StepFooter from "../components/StepFooter";
import LoadingIndicator from "../components/LoadingIndicator";
import {
  downloadContextStudioBundle,
  downloadGlobalSchema,
  fetchContextStudioPreview,
  type ContextStudioPreview,
} from "@/lib/context-studio-api";
import { fetchInsights, type IntelligenceInsights } from "@/lib/intelligence-api";
import { parseRepoUrl } from "@/lib/parse-repo";
import { repoHref, saveRepoToSession } from "@/lib/repo-query";

const VALUE_CARDS = [
  {
    title: "Project structure",
    body: "Directory tree, code layers, and cross-folder import links — schema types ProjectStructure, Directory, CodeLayer.",
  },
  {
    title: "File dependencies",
    body: "How source files import each other — DependencyGraph, SourceFile, ImportsFile, hubs, and external packages.",
  },
  {
    title: "Agent memory",
    body: "Eight grounded docs + JSON-LD instances so ICA knows layout, imports, onboarding, and risks.",
  },
  {
    title: "Live + snapshot",
    body: "Context Studio holds layout and connections; BlueWings MCP refreshes blast radius and full graphs.",
  },
];

export default function ContextStudioPage() {
  const searchParams = useSearchParams();
  const repoParam = searchParams.get("repo");

  const [input, setInput] = useState(repoParam ?? "");
  const [owner, setOwner] = useState("");
  const [repo, setRepo] = useState("");
  const [insights, setInsights] = useState<IntelligenceInsights | null>(null);
  const [preview, setPreview] = useState<ContextStudioPreview | null>(null);
  const [error, setError] = useState("");
  const [previewLoading, setPreviewLoading] = useState(false);
  const [exportLoading, setExportLoading] = useState(false);
  const [llmEnhance, setLlmEnhance] = useState(false);
  const [includeGraph, setIncludeGraph] = useState(true);
  const [useCachedInsights, setUseCachedInsights] = useState(true);

  const resolveRepo = useCallback(() => {
    const parsed = parseRepoUrl(input);
    if (!parsed) return null;
    return parsed;
  }, [input]);

  useEffect(() => {
    if (!repoParam) return;
    const parsed = parseRepoUrl(repoParam);
    if (parsed) {
      setInput(repoParam);
      setOwner(parsed.owner);
      setRepo(parsed.repo);
    }
  }, [repoParam]);

  async function loadInsights() {
    const parsed = resolveRepo();
    if (!parsed) {
      setError("Enter owner/repo or a GitHub URL");
      return null;
    }
    setOwner(parsed.owner);
    setRepo(parsed.repo);
    saveRepoToSession(parsed.owner, parsed.repo);
    const data = await fetchInsights(parsed.owner, parsed.repo);
    setInsights(data);
    return data;
  }

  async function runPreview() {
    const parsed = resolveRepo();
    if (!parsed) {
      setError("Enter owner/repo or a GitHub URL");
      return;
    }
    setError("");
    setPreviewLoading(true);
    setPreview(null);
    setOwner(parsed.owner);
    setRepo(parsed.repo);
    saveRepoToSession(parsed.owner, parsed.repo);

    try {
      let cached = insights;
      if (useCachedInsights && (!cached || cached.repository !== `${parsed.owner}/${parsed.repo}`)) {
        cached = await loadInsights();
      }
      const data = await fetchContextStudioPreview(parsed.owner, parsed.repo, {
        includeGraph,
        llmEnhanceDocs: false,
        insights: useCachedInsights && cached ? cached : undefined,
      });
      setPreview(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Preview failed");
    } finally {
      setPreviewLoading(false);
    }
  }

  async function runExport() {
    const parsed = resolveRepo();
    if (!parsed || exportLoading) return;
    setError("");
    setExportLoading(true);
    try {
      await downloadContextStudioBundle(parsed.owner, parsed.repo, {
        includeGraph,
        llmEnhanceDocs: llmEnhance,
        insights: useCachedInsights && insights ? insights : undefined,
      });
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Export failed");
    } finally {
      setExportLoading(false);
    }
  }

  const intelligenceHref = owner && repo ? repoHref("/intelligence", owner, repo) : "/intelligence";

  return (
    <AppShell workflow="context-studio">
      <PageHero
        step={4}
        title="ICA Context Studio"
        description="Turn repository intelligence into durable agent context — JSON-LD schema, grounded docs, and an import checklist for IBM ICA."
      >
        <form
          className="card flex flex-col gap-2 p-2 sm:flex-row"
          onSubmit={(e) => {
            e.preventDefault();
            runPreview();
          }}
        >
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="owner/repo or GitHub URL"
            className="input-field min-w-0 flex-1 border-0 bg-transparent focus:ring-0"
          />
          <button type="submit" disabled={previewLoading || exportLoading} className="btn-primary shrink-0 py-2">
            {previewLoading ? "Building preview…" : "Preview bundle"}
          </button>
          <button
            type="button"
            disabled={previewLoading || exportLoading}
            onClick={runExport}
            className="btn-secondary shrink-0 py-2 text-xs disabled:opacity-50"
          >
            {exportLoading ? "Exporting…" : "Download ZIP"}
          </button>
        </form>

        <div className="mt-3 flex flex-wrap gap-4 text-[10px] text-[var(--app-muted)]">
          <label className="flex items-center gap-1.5">
            <input
              type="checkbox"
              checked={includeGraph}
              onChange={(e) => setIncludeGraph(e.target.checked)}
              className="rounded border-[var(--app-border)]"
            />
            Include file dependency graph
          </label>
          <label className="flex items-center gap-1.5">
            <input
              type="checkbox"
              checked={useCachedInsights}
              onChange={(e) => setUseCachedInsights(e.target.checked)}
              className="rounded border-[var(--app-border)]"
            />
            Reuse Intelligence analysis when available
          </label>
          <label className="flex items-center gap-1.5">
            <input
              type="checkbox"
              checked={llmEnhance}
              onChange={(e) => setLlmEnhance(e.target.checked)}
              className="rounded border-[var(--app-border)]"
            />
            LLM polish docs (export only)
          </label>
        </div>

        {(previewLoading || exportLoading) && (
          <div className="mt-4">
            <LoadingIndicator
              message={
                exportLoading
                  ? "Building ZIP: schema, instances, facts, structure, dependencies, docs…"
                  : "Analyzing repo and building Context Studio preview…"
              }
              size="md"
            />
          </div>
        )}

        {error && (
          <p className="mt-2 rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-2 text-sm text-red-300">
            {error}
          </p>
        )}
      </PageHero>

      <section className="mb-8 grid gap-3 sm:grid-cols-3">
        {VALUE_CARDS.map((c) => (
          <article key={c.title} className="card p-4">
            <h3 className="text-xs font-semibold text-[var(--app-heading)]">{c.title}</h3>
            <p className="mt-2 text-[10px] leading-relaxed text-[var(--app-muted)]">{c.body}</p>
          </article>
        ))}
      </section>

      <section className="card mb-8 p-4">
        <h3 className="text-sm font-semibold text-[var(--app-heading)]">Global schema (once per ICA team)</h3>
        <p className="mt-1 text-[10px] text-[var(--app-muted)]">
          Import <code className="text-[var(--brand-royal)]">software-repository-archaeology-schema.jsonld</code>{" "}
          under Schemas — same syntax as the ICA Context Studio lab. Each repo gets its own context + docs.
        </p>
        <button type="button" onClick={downloadGlobalSchema} className="btn-secondary mt-3 py-2 text-xs">
          Download schema only
        </button>
      </section>

      {preview && (
        <div className="space-y-6">
          <section className="card p-4">
            <h3 className="text-sm font-semibold text-[var(--app-heading)]">Bundle preview</h3>
            <p className="mt-1 text-[10px] text-[var(--app-muted)]">
              Suggested context:{" "}
              <span className="font-medium text-[var(--brand-royal)]">
                {preview.suggested_context_name ?? preview.manifest.suggested_context_name}
              </span>
              {preview.facts_summary.collected_at && (
                <> · Snapshot {preview.facts_summary.collected_at}</>
              )}
            </p>
            <dl className="mt-4 grid grid-cols-2 gap-3 text-[10px] sm:grid-cols-4">
              {[
                ["Files (tree)", preview.facts_summary.total_files ?? "—"],
                ["Import edges", preview.facts_summary.file_dependency_edges ?? "—"],
                ["Modeled files", preview.facts_summary.modeled_source_files ?? "—"],
                ["Sample edges", preview.facts_summary.sampled_import_edges ?? "—"],
                ["Directories", preview.facts_summary.total_directories ?? "—"],
                ["Module links", preview.facts_summary.cross_module_links ?? "—"],
                ["Graph hubs", preview.facts_summary.graph_hub_count],
                ["Ext. packages", preview.facts_summary.external_package_count ?? "—"],
                ["Modules", preview.facts_summary.module_count],
                ["JSON-LD nodes", preview.instance_count],
                ["Migration", preview.facts_summary.migration_difficulty],
              ].map(([k, v]) => (
                <div key={k} className="rounded-lg border border-[var(--app-border)] bg-[var(--app-elevated)] px-2 py-1.5">
                  <dt className="text-[var(--app-faint)]">{k}</dt>
                  <dd className="mt-0.5 font-medium text-[var(--app-text)]">{String(v)}</dd>
                </div>
              ))}
            </dl>
            {preview.validation_errors.length > 0 && (
              <p className="mt-3 text-[10px] text-amber-600">
                Validation notes: {preview.validation_errors.join("; ")}
              </p>
            )}
          </section>

          <section className="card p-4">
            <h3 className="text-sm font-semibold text-[var(--app-heading)]">ZIP contents</h3>
            <ul className="mt-2 list-inside list-disc space-y-1 text-[10px] text-[var(--app-text)]">
              <li>
                <code>schema/</code> — global ontology (or use Download schema only above)
              </li>
              <li>
                <code>instances/</code> — this repo&apos;s modules, hot files, PRs, hubs
              </li>
              <li>
                <code>data/</code> — facts JSON (ground truth)
              </li>
              <li>
                <code>structure/</code> — project tree + connectivity JSON
              </li>
              <li>
                <code>dependencies/</code> — file-to-file imports, per-file lists, packages
              </li>
              {preview.documents.map((d) => (
                <li key={d.path}>
                  <code>{d.path}</code>
                </li>
              ))}
            </ul>
          </section>

          <section className="card p-4">
            <h3 className="mb-3 text-sm font-semibold text-[var(--app-heading)]">
              Import into Context Studio
            </h3>
            <ol className="list-decimal space-y-2 pl-4 text-[10px] leading-relaxed text-[var(--app-text)]">
              {preview.import_checklist.map((step, i) => (
                <li key={i}>{step}</li>
              ))}
            </ol>
            <p className="mt-4 text-[10px] text-[var(--app-muted)]">
              See <code className="text-[var(--brand-royal)]">docs/CONTEXT_STUDIO_EXPORT.md</code> in the
              BlueWings repository. Use Context Studio <code>ctx_...</code> with BlueWings GitHub MCP in
              Context Forge for live blast radius.
            </p>
          </section>

          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              disabled={exportLoading}
              onClick={runExport}
              className="btn-primary py-2 text-xs disabled:opacity-50"
            >
              Download full ZIP
            </button>
            <Link href={intelligenceHref} className="btn-secondary py-2 text-xs">
              Open Intelligence →
            </Link>
          </div>
        </div>
      )}

      {!preview && !previewLoading && (
        <section className="card py-12 text-center">
          <p className="text-sm text-[var(--app-muted)]">
            Enter a repository and preview what will go into Context Studio
          </p>
          <p className="mt-2 text-xs text-[var(--app-faint)]">
            Recommended: run{" "}
            <Link href={intelligenceHref} className="text-[var(--brand-royal)] hover:underline">
              Intelligence
            </Link>{" "}
            first, then export here with cached analysis
          </p>
        </section>
      )}

      <StepFooter currentStep={4} />
    </AppShell>
  );
}
