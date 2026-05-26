import type { AgentBackend } from "./agent-backend";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface ImpactChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ImpactInsightGraphNode {
  id: string;
  label: string;
  type: string;
  group?: string;
  color?: string;
  path?: string;
}

export interface ImpactInsightGraph {
  kind: string;
  title: string;
  description?: string;
  ai_title?: string;
  nodes: ImpactInsightGraphNode[];
  edges: { id: string; source: string; target: string; label?: string; kind?: string }[];
}

export interface ImpactQuickAction {
  id: string;
  label: string;
  short_label: string;
  prompt: string;
  graph_kind: string;
  request_ai_graph?: boolean;
}

export interface ImpactChatResponse {
  message: string;
  model: string;
  provider?: string;
  backend?: string;
  session_id?: string;
  tool_calls?: { name: string; arguments: Record<string, unknown> }[];
  insight_graph?: ImpactInsightGraph;
  action_id?: string;
  quick_actions?: ImpactQuickAction[];
}

export interface DependencyNode {
  id: string;
  path: string;
  label: string;
  type: "file" | "package";
  language: string;
  extension: string;
  in_degree: number;
  out_degree: number;
}

export interface DependencyEdge {
  id: string;
  source: string;
  target: string;
  kind: string;
  specifier?: string;
}

export interface FileTreeNode {
  type: "directory" | "file";
  name: string;
  path?: string;
  children?: FileTreeNode[];
}

export interface DependencyGraph {
  version: string;
  repository: {
    owner: string;
    repo: string;
    full_name: string;
    default_branch: string;
    primary_language?: string | null;
    url?: string;
  };
  meta: {
    analyzed_at: string;
    files_analyzed: number;
    files_in_tree: number;
    truncated: boolean;
    include_packages: boolean;
    focus_path?: string | null;
    max_depth?: number | null;
    fetch?: {
      requested: number;
      fetched: number;
      failed: number;
      failed_paths?: string[];
    };
  };
  stats: {
    node_count: number;
    edge_count: number;
    file_count: number;
    package_count: number;
    languages: Record<string, number>;
  };
  file_tree: FileTreeNode;
  nodes: DependencyNode[];
  edges: DependencyEdge[];
  clusters: { id: string; label: string; file_count: number; paths: string[] }[];
}

export interface FetchGraphOptions {
  ref?: string;
  maxFiles?: number;
  includePackages?: boolean;
  focusPath?: string;
  maxDepth?: number;
}

export interface ChangeImpact {
  version: string;
  target: {
    path: string;
    requested_path?: string;
    resolved: boolean;
    cluster?: string;
    language?: string;
  };
  repository: DependencyGraph["repository"];
  meta: {
    analyzed_at: string;
    graph_truncated?: boolean;
    files_analyzed?: number;
    max_depth_dependents?: number;
    max_depth_dependencies?: number;
    pr_sample_size?: number;
    error?: string;
  };
  summary: {
    risk_level: "high" | "medium" | "low" | "unknown";
    direct_dependent_count?: number;
    transitive_dependent_count?: number;
    direct_dependency_count?: number;
    package_dependency_count?: number;
    related_pr_count?: number;
    total_affected_files?: number;
    message: string;
  };
  dependents: {
    direct: { path: string; label: string; language: string; cluster: string }[];
    transitive: { path: string; label: string; language: string; cluster: string }[];
    by_depth: Record<string, string[]>;
  };
  dependencies: {
    direct: { path: string; label: string; type: string }[];
    transitive: { path: string; label: string; language: string; cluster: string }[];
  };
  related_prs: {
    number: number;
    title: string;
    state: string;
    author?: string;
    merged_at?: string | null;
    updated_at?: string;
    url?: string;
    file_status?: string;
    additions?: number;
    deletions?: number;
  }[];
  highlight: {
    target?: string;
    dependent_paths?: string[];
    dependency_paths?: string[];
    node_ids: string[];
    edge_ids: string[];
    paths: string[];
  };
  subgraph: {
    nodes: DependencyNode[];
    edges: DependencyEdge[];
  };
}

export interface FetchImpactOptions {
  ref?: string;
  maxFiles?: number;
  includePackages?: boolean;
  maxDepthDependents?: number;
  maxDepthDependencies?: number;
  prSampleSize?: number;
}

export async function fetchChangeImpact(
  owner: string,
  repo: string,
  filePath: string,
  options: FetchImpactOptions = {},
): Promise<ChangeImpact> {
  const params = new URLSearchParams({ file_path: filePath });
  if (options.ref) params.set("ref", options.ref);
  if (options.maxFiles) params.set("max_files", String(options.maxFiles));
  if (options.includePackages === false) params.set("include_packages", "false");
  if (options.maxDepthDependents)
    params.set("max_depth_dependents", String(options.maxDepthDependents));
  if (options.maxDepthDependencies)
    params.set("max_depth_dependencies", String(options.maxDepthDependencies));
  if (options.prSampleSize) params.set("pr_sample_size", String(options.prSampleSize));
  const res = await fetch(
    `${API_BASE}/repo/${owner}/${repo}/dependencies/impact?${params.toString()}`,
  );
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function askImpactChat(
  owner: string,
  repo: string,
  impact: ChangeImpact,
  messages: ImpactChatMessage[],
  options?: {
    backend?: AgentBackend;
    sessionId?: string;
    maxContextFiles?: number;
    actionId?: string;
  },
): Promise<ImpactChatResponse> {
  const res = await fetch(
    `${API_BASE}/repo/${owner}/${repo}/dependencies/impact/chat`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        messages,
        impact,
        backend: options?.backend ?? "auto",
        session_id: options?.sessionId ?? null,
        max_context_files: options?.maxContextFiles ?? 8,
        action_id: options?.actionId ?? null,
      }),
    },
  );
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.detail ?? data.error ?? `Impact chat failed (${res.status})`);
  }
  return data;
}

export async function fetchDependencyGraph(
  owner: string,
  repo: string,
  options: FetchGraphOptions = {},
): Promise<DependencyGraph> {
  const params = new URLSearchParams();
  if (options.ref) params.set("ref", options.ref);
  if (options.maxFiles) params.set("max_files", String(options.maxFiles));
  if (options.includePackages === false) params.set("include_packages", "false");
  if (options.focusPath) {
    params.set("focus_path", options.focusPath);
    if (options.maxDepth) params.set("max_depth", String(options.maxDepth));
  }
  const qs = params.toString();
  const res = await fetch(
    `${API_BASE}/repo/${owner}/${repo}/dependencies/graph${qs ? `?${qs}` : ""}`,
  );
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
