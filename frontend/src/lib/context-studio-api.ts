import type { IntelligenceInsights } from "./intelligence-api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface ContextStudioExportOptions {
  ref?: string;
  includeGraph?: boolean;
  graphMaxFiles?: number;
  llmEnhanceDocs?: boolean;
  insights?: IntelligenceInsights | null;
}

export interface ContextStudioPreview {
  manifest: {
    suggested_context_name?: string;
    suggested_context_description?: string;
    collected_at?: string;
    repository?: string;
    files?: Record<string, string | string[]>;
  };
  facts_summary: {
    repository: string;
    collected_at?: string;
    module_count: number;
    hot_file_count: number;
    graph_hub_count: number;
    migration_difficulty?: string;
    detected_stack?: string[];
    graph_truncated?: boolean;
    total_files?: number;
    total_directories?: number;
    cross_module_links?: number;
    code_layers?: number;
    dependencies_available?: boolean;
    file_dependency_edges?: number;
    modeled_source_files?: number;
    sampled_import_edges?: number;
    external_package_count?: number;
  };
  instance_count: number;
  documents: { path: string; title: string }[];
  import_checklist: string[];
  suggested_context_name?: string;
  validation_errors: string[];
}

function exportBody(options?: ContextStudioExportOptions) {
  return {
    ref: options?.ref ?? "",
    include_graph: options?.includeGraph ?? true,
    graph_max_files: options?.graphMaxFiles ?? 300,
    llm_enhance_docs: options?.llmEnhanceDocs ?? false,
    insights: options?.insights ?? undefined,
  };
}

export async function fetchContextStudioPreview(
  owner: string,
  repo: string,
  options?: ContextStudioExportOptions,
): Promise<ContextStudioPreview> {
  const res = await fetch(`${API_BASE}/repo/${owner}/${repo}/context-studio/preview`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(exportBody(options)),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function downloadContextStudioBundle(
  owner: string,
  repo: string,
  options?: ContextStudioExportOptions,
): Promise<void> {
  const res = await fetch(`${API_BASE}/repo/${owner}/${repo}/context-studio/export`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(exportBody(options)),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Export failed (${res.status})`);
  }
  const blob = await res.blob();
  const disposition = res.headers.get("Content-Disposition");
  let filename = `${owner}-${repo}-context-studio.zip`;
  const match = disposition?.match(/filename="?([^";]+)"?/);
  if (match?.[1]) filename = match[1];
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export function downloadGlobalSchema(): void {
  const url = `${API_BASE}/context-studio/schema`;
  const a = document.createElement("a");
  a.href = url;
  a.download = "software-repository-archaeology-schema.jsonld";
  a.click();
}
