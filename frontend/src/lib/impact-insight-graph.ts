import type { ChangeImpact } from "./dependency-api";

export interface InsightGraphNode {
  id: string;
  label: string;
  type: string;
  group?: string;
  color?: string;
  path?: string;
  meta?: Record<string, unknown>;
}

export interface InsightGraphEdge {
  id: string;
  source: string;
  target: string;
  label?: string;
  kind?: string;
}

export interface InsightGraph {
  kind: string;
  title: string;
  description?: string;
  ai_title?: string;
  nodes: InsightGraphNode[];
  edges: InsightGraphEdge[];
}

export interface ImpactQuickAction {
  id: string;
  label: string;
  short_label: string;
  prompt: string;
  graph_kind: string;
  request_ai_graph?: boolean;
}

const NODE_COLORS: Record<string, string> = {
  target: "#dc2626",
  file: "#2563eb",
  dependent: "#d97706",
  import: "#7c3aed",
  package: "#8b5cf6",
  pr: "#059669",
  test: "#0891b2",
  layer: "#64748b",
  concept: "#0ea5e9",
  risk: "#b45309",
};

function node(
  id: string,
  label: string,
  type: string,
  extra?: Partial<InsightGraphNode>,
): InsightGraphNode {
  return { id, label, type, group: type, color: NODE_COLORS[type] ?? "#64748b", ...extra };
}

let _edgeSeq = 0;

function edge(
  source: string,
  target: string,
  label?: string,
  kind = "relates",
  explicitId?: string,
): InsightGraphEdge {
  _edgeSeq += 1;
  return {
    id: explicitId ?? `${source}->${target}:${kind}:${_edgeSeq}`,
    source,
    target,
    label,
    kind,
  };
}

/** Ensure unique node/edge ids for React Flow (avoids duplicate key warnings). */
export function normalizeInsightGraph(graph: InsightGraph): InsightGraph {
  const nodeMap = new Map<string, InsightGraphNode>();
  for (const n of graph.nodes) {
    if (n.id && !nodeMap.has(n.id)) nodeMap.set(n.id, n);
  }
  const nodes = [...nodeMap.values()];
  const nodeIds = new Set(nodes.map((n) => n.id));

  const seenEdgeIds = new Set<string>();
  const edges: InsightGraphEdge[] = [];
  for (let i = 0; i < graph.edges.length; i++) {
    const e = graph.edges[i];
    if (!e.source || !e.target || !nodeIds.has(e.source) || !nodeIds.has(e.target)) {
      continue;
    }
    let id = e.id?.trim() || `${e.source}->${e.target}:${e.kind ?? "rel"}:${i}`;
    if (seenEdgeIds.has(id)) id = `${id}-dup${i}`;
    seenEdgeIds.add(id);
    edges.push({ ...e, id });
  }

  return { ...graph, nodes, edges };
}

function finalize(graph: InsightGraph): InsightGraph {
  _edgeSeq = 0;
  return normalizeInsightGraph(graph);
}

export function buildInsightGraph(impact: ChangeImpact, actionId: string): InsightGraph {
  const path = impact.target.resolved ? impact.target.path : "?";
  if (!impact.target.resolved) {
    return { kind: actionId, title: "Unresolved target", nodes: [], edges: [] };
  }

  switch (actionId) {
    case "blast_map":
    case "explain_file":
      return blastMapGraph(impact, path);
    case "dependents_layers":
      return dependentsLayersGraph(impact, path);
    case "imports_chain":
      return importsChainGraph(impact, path);
    case "pr_activity":
      return prActivityGraph(impact, path);
    case "test_matrix":
      return testMatrixGraph(impact, path);
    case "refactor_risk":
    case "review_checklist":
      return refactorRiskGraph(impact, path);
    default:
      return blastMapGraph(impact, path);
  }
}

function blastMapGraph(impact: ChangeImpact, path: string): InsightGraph {
  const nodes: InsightGraphNode[] = impact.subgraph.nodes.map((n) =>
    node(n.id, n.label, n.type === "package" ? "package" : "file", { path: n.path }),
  );
  const edges: InsightGraphEdge[] = impact.subgraph.edges.map((e, i) =>
    edge(e.source, e.target, e.kind, e.kind, e.id || `subgraph-edge-${i}`),
  );
  for (const n of nodes) {
    if (n.id === path) {
      n.type = "target";
      n.group = "target";
      n.color = NODE_COLORS.target;
    }
  }
  return finalize({
    kind: "blast_map",
    title: "Blast radius map",
    description: "Files and imports in the impact neighborhood",
    nodes,
    edges,
  });
}

function dependentsLayersGraph(impact: ChangeImpact, path: string): InsightGraph {
  const nodes: InsightGraphNode[] = [
    node(path, path.split("/").pop() ?? path, "target", { path }),
  ];
  const edges: InsightGraphEdge[] = [];

  const byDepth = impact.dependents.by_depth ?? {};
  for (const [depthStr, files] of Object.entries(byDepth).sort(
    (a, b) => Number(a[0]) - Number(b[0]),
  )) {
    for (const fpath of files) {
      if (fpath === path || fpath.startsWith("pkg:")) continue;
      if (!nodes.some((n) => n.id === fpath)) {
        nodes.push(
          node(fpath, fpath.split("/").pop() ?? fpath, "dependent", {
            path: fpath,
            meta: { depth: Number(depthStr) },
          }),
        );
      }
      edges.push(edge(fpath, path, `depth ${depthStr}`));
    }
  }

  return finalize({
    kind: "dependents_layers",
    title: "Who depends on this file",
    description: "Importer files linked to the change target",
    nodes,
    edges,
  });
}

function importsChainGraph(impact: ChangeImpact, path: string): InsightGraph {
  const nodes: InsightGraphNode[] = [
    node(path, path.split("/").pop() ?? path, "target", { path }),
  ];
  const edges: InsightGraphEdge[] = [];

  for (const item of impact.dependencies.direct) {
    const fp = item.path;
    const ntype = fp.startsWith("pkg:") ? "package" : "import";
    nodes.push(node(fp, item.label, ntype, { path: fp }));
    edges.push(edge(path, fp, "imports"));
  }

  return finalize({
    kind: "imports_chain",
    title: "What this file pulls in",
    description: "Direct imports from the target",
    nodes,
    edges,
  });
}

function prActivityGraph(impact: ChangeImpact, path: string): InsightGraph {
  const nodes: InsightGraphNode[] = [
    node(path, path.split("/").pop() ?? path, "target", { path }),
  ];
  const edges: InsightGraphEdge[] = [];

  for (const pr of impact.related_prs.slice(0, 10)) {
    const pid = `pr:${pr.number}`;
    nodes.push(
      node(pid, `#${pr.number}`, "pr", {
        meta: { title: pr.title, url: pr.url, state: pr.state },
      }),
    );
    edges.push(edge(pid, path, pr.state));
  }

  return finalize({
    kind: "pr_activity",
    title: "Related pull requests",
    description: "PRs that touched this file",
    nodes,
    edges,
  });
}

function testMatrixGraph(impact: ChangeImpact, path: string): InsightGraph {
  const nodes: InsightGraphNode[] = [
    node(path, path.split("/").pop() ?? path, "target", { path }),
    node("test:root", "Regression suite", "test"),
  ];
  const edges: InsightGraphEdge[] = [edge(path, "test:root", "change here")];

  for (const item of impact.dependents.direct.slice(0, 10)) {
    const fp = item.path;
    nodes.push(node(fp, item.label, "dependent", { path: fp }));
    const tid = `test:${fp}`;
    nodes.push(node(tid, `Test ${item.label}`, "test"));
    edges.push(edge(fp, path, "imports"));
    edges.push(edge(tid, fp, "verify"));
  }

  return finalize({
    kind: "test_matrix",
    title: "Suggested test coverage",
    description: "Areas to verify before merge",
    nodes,
    edges,
  });
}

function refactorRiskGraph(impact: ChangeImpact, path: string): InsightGraph {
  const risk = impact.summary.risk_level;
  const nodes: InsightGraphNode[] = [
    node(path, path.split("/").pop() ?? path, "target", { path }),
    node(`risk:${risk}`, `Risk: ${risk}`, "risk"),
  ];
  const edges: InsightGraphEdge[] = [edge(`risk:${risk}`, path, "assessment")];

  for (const item of impact.dependents.direct.slice(0, 15)) {
    nodes.push(
      node(item.path, `${item.label} (${item.in_degree ?? 0} in)`, "dependent", {
        path: item.path,
      }),
    );
    edges.push(edge(item.path, path, "breaks if refactored"));
  }

  return finalize({
    kind: "refactor_risk",
    title: "Refactor risk map",
    description: "Direct importers that need updates",
    nodes,
    edges,
  });
}

export function mergeAiInsightGraph(
  base: InsightGraph,
  aiGraph: InsightGraph | null | undefined,
): InsightGraph {
  if (!aiGraph?.nodes?.length) return base;
  const seen = new Set(base.nodes.map((n) => n.id));
  const nodes = [...base.nodes];
  const edges = [...base.edges];

  for (const n of aiGraph.nodes) {
    const id = n.id || n.label;
    if (!id || seen.has(id)) continue;
    seen.add(id);
    nodes.push(
      node(id, n.label || id, n.type || "concept", { group: n.group, path: n.path }),
    );
  }
  for (const e of aiGraph.edges ?? []) {
    if (e.source && e.target) {
      edges.push(edge(e.source, e.target, e.label, e.kind ?? "concept"));
    }
  }

  return normalizeInsightGraph({
    ...base,
    nodes,
    edges,
    ai_title: aiGraph.title,
  });
}

export function getQuickActionsFromImpact(impact: ChangeImpact): ImpactQuickAction[] {
  const direct = impact.dependents.direct.length;
  const prs = impact.related_prs.length;
  const risk = impact.summary.risk_level;

  const actions: ImpactQuickAction[] = [
    {
      id: "blast_map",
      label: "Impact map",
      short_label: "Map",
      prompt:
        "Walk me through the blast radius map: who imports this file, what it imports, and where the highest-risk edges are.",
      graph_kind: "blast_map",
    },
    {
      id: "explain_file",
      label: "Explain file",
      short_label: "Explain",
      prompt:
        "What are the main functions, exports, and responsibilities of this file? Which symbols would a refactor touch?",
      graph_kind: "blast_map",
      request_ai_graph: true,
    },
    {
      id: "refactor_risk",
      label: "Refactor risk",
      short_label: "Risk",
      prompt:
        "If I refactor this file, which dependent files break first and what should I change in each?",
      graph_kind: "refactor_risk",
    },
  ];

  if (direct > 0) {
    actions.push({
      id: "dependents_layers",
      label: "Who breaks?",
      short_label: "Dependents",
      prompt:
        "List dependent files by blast-radius depth and explain what each one uses from the target file.",
      graph_kind: "dependents_layers",
    });
    actions.push({
      id: "test_matrix",
      label: "Test plan",
      short_label: "Tests",
      prompt:
        "What should I test before merging a change to this file? Map tests to each direct dependent.",
      graph_kind: "test_matrix",
      request_ai_graph: true,
    });
  }

  actions.push({
    id: "imports_chain",
    label: "Imports",
    short_label: "Imports",
    prompt:
      "Explain the import chain: what does this file depend on and could upstream changes affect it?",
    graph_kind: "imports_chain",
  });

  if (prs > 0) {
    actions.push({
      id: "pr_activity",
      label: "PR history",
      short_label: "PRs",
      prompt:
        "Summarize what the related PRs changed in this file and what patterns I should watch for.",
      graph_kind: "pr_activity",
    });
  }

  if (risk === "high" || risk === "medium") {
    actions.push({
      id: "review_checklist",
      label: "Review checklist",
      short_label: "Review",
      prompt:
        "Give a concise pre-merge review checklist for this high-impact file: owners, tests, docs, and rollout steps.",
      graph_kind: "refactor_risk",
      request_ai_graph: true,
    });
  }

  return actions;
}

/** Validate and normalize JSON from export or external tools. */
export function parseInsightGraphJson(raw: unknown): InsightGraph {
  if (!raw || typeof raw !== "object") {
    throw new Error("JSON must be an object");
  }
  const o = raw as Record<string, unknown>;
  const nodesRaw = o.nodes;
  const edgesRaw = o.edges;
  if (!Array.isArray(nodesRaw) || nodesRaw.length === 0) {
    throw new Error("JSON must include a non-empty nodes array");
  }
  if (!Array.isArray(edgesRaw)) {
    throw new Error("JSON must include an edges array");
  }

  const nodes: InsightGraphNode[] = nodesRaw.map((n, i) => {
    if (!n || typeof n !== "object") throw new Error(`Invalid node at index ${i}`);
    const item = n as Record<string, unknown>;
    const id = String(item.id ?? item.label ?? `node-${i}`);
    const label = String(item.label ?? id);
    const type = String(item.type ?? "concept");
    return {
      id,
      label,
      type,
      group: item.group != null ? String(item.group) : type,
      color: item.color != null ? String(item.color) : NODE_COLORS[type] ?? "#64748b",
      path: item.path != null ? String(item.path) : undefined,
      meta:
        item.meta && typeof item.meta === "object"
          ? (item.meta as Record<string, unknown>)
          : undefined,
    };
  });

  const nodeIds = new Set(nodes.map((n) => n.id));
  const edges: InsightGraphEdge[] = edgesRaw.map((e, i) => {
    if (!e || typeof e !== "object") throw new Error(`Invalid edge at index ${i}`);
    const item = e as Record<string, unknown>;
    const source = String(item.source ?? "");
    const target = String(item.target ?? "");
    if (!source || !target) throw new Error(`Edge ${i} needs source and target`);
    if (!nodeIds.has(source) || !nodeIds.has(target)) {
      throw new Error(`Edge ${i} references unknown node (${source} → ${target})`);
    }
    return {
      id: String(item.id ?? `${source}->${target}`),
      source,
      target,
      label: item.label != null ? String(item.label) : undefined,
      kind: item.kind != null ? String(item.kind) : undefined,
    };
  });

  return {
    kind: String(o.kind ?? "imported"),
    title: String(o.title ?? o.ai_title ?? "Imported insight graph"),
    description: o.description != null ? String(o.description) : undefined,
    ai_title: o.ai_title != null ? String(o.ai_title) : undefined,
    nodes,
    edges,
  };
}
