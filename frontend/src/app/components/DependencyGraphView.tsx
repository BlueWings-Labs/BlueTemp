"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  MarkerType,
  type Node,
  type Edge,
  useNodesState,
  useEdgesState,
  Panel,
} from "@xyflow/react";
import dagre from "@dagrejs/dagre";
import "@xyflow/react/dist/style.css";
import type { DependencyGraph, DependencyNode } from "@/lib/dependency-api";

const LANG_COLORS: Record<string, string> = {
  typescript: "#3178c6",
  javascript: "#e8c547",
  python: "#3b9ee8",
  go: "#00add8",
  rust: "#dea584",
  java: "#e76f00",
  vue: "#42b883",
  svelte: "#ff3e00",
  external: "#a371f7",
  unknown: "#6e7681",
};

function nodeColor(n: DependencyNode): string {
  if (n.type === "package") return LANG_COLORS.external;
  return LANG_COLORS[n.language] ?? LANG_COLORS.unknown;
}

function layoutGraph(
  graphNodes: DependencyNode[],
  graphEdges: { id: string; source: string; target: string; kind: string }[],
  impact?: ImpactHighlight | null,
): { nodes: Node[]; edges: Edge[] } {
  const g = new dagre.graphlib.Graph();
  g.setDefaultEdgeLabel(() => ({}));
  g.setGraph({ rankdir: "LR", nodesep: 48, ranksep: 72, marginx: 24, marginy: 24 });

  const width = 180;
  const height = 44;

  for (const n of graphNodes) {
    g.setNode(n.id, { width, height });
  }
  for (const e of graphEdges) {
    if (g.hasNode(e.source) && g.hasNode(e.target)) {
      g.setEdge(e.source, e.target);
    }
  }

  dagre.layout(g);

  const flowNodes: Node[] = graphNodes.map((n) => {
    const pos = g.node(n.id);
    const color = nodeColor(n);
    const role = nodeImpactRole(n.id, impact);
    const border =
      role === "target"
        ? "2.5px solid #dc2626"
        : role === "dependent"
          ? "2px solid #d97706"
          : role === "dependency"
            ? "2px solid #2563eb"
            : `1.5px solid ${color}`;
    const bg =
      role === "target"
        ? "linear-gradient(145deg, #fef2f2 0%, #ffffff 70%)"
        : role === "dependent"
          ? "linear-gradient(145deg, #fffbeb 0%, #ffffff 70%)"
          : role === "dependency"
            ? "linear-gradient(145deg, #eff6ff 0%, #ffffff 70%)"
            : `linear-gradient(145deg, ${color}18 0%, #ffffff 70%)`;

    return {
      id: n.id,
      type: "default",
      position: {
        x: (pos?.x ?? 0) - width / 2,
        y: (pos?.y ?? 0) - height / 2,
      },
      data: {
        label: (
          <div className="flex max-w-[160px] flex-col gap-0.5 px-1">
            <span className="truncate text-[10px] font-semibold text-slate-800">
              {n.label}
            </span>
            {n.type === "file" && (
              <span className="truncate text-[8px] text-slate-500">{n.language}</span>
            )}
          </div>
        ),
      },
      style: {
        width,
        height,
        borderRadius: 8,
        border,
        background: bg,
        boxShadow: role ? `0 0 16px ${role === "target" ? "#dc262633" : role === "dependent" ? "#d9770633" : "#2563eb33"}` : `0 0 20px ${color}33`,
        fontSize: 10,
      },
    };
  });

  const impactEdgeIds = new Set<string>();
  if (impact) {
    for (const e of graphEdges) {
      const srcRole = nodeImpactRole(e.source, impact);
      const tgtRole = nodeImpactRole(e.target, impact);
      if (srcRole || tgtRole) impactEdgeIds.add(e.id);
    }
  }

  const flowEdges: Edge[] = graphEdges.map((e) => {
    const highlighted = impactEdgeIds.has(e.id);
    return {
      id: e.id,
      source: e.source,
      target: e.target,
      animated: e.kind === "dynamic" || highlighted,
      label: e.kind === "package" ? "npm" : undefined,
      labelStyle: { fill: "#64748b", fontSize: 8 },
      style: {
        stroke: highlighted ? "#dc2626" : e.kind === "package" ? "#8b5cf6" : "#2563eb",
        strokeWidth: highlighted ? 2 : 1.2,
      },
      markerEnd: {
        type: MarkerType.ArrowClosed,
        color: highlighted ? "#dc2626" : "#2563eb",
        width: 14,
        height: 14,
      },
    };
  });

  return { nodes: flowNodes, edges: flowEdges };
}

export interface ImpactHighlight {
  targetPath: string;
  dependentPaths: Set<string>;
  dependencyPaths: Set<string>;
}

interface Props {
  graph: DependencyGraph;
  highlightPath?: string | null;
  impact?: ImpactHighlight | null;
  onSelectFile?: (path: string) => void;
}

function nodeImpactRole(
  id: string,
  impact: ImpactHighlight | null | undefined,
): "target" | "dependent" | "dependency" | null {
  if (!impact) return null;
  if (id === impact.targetPath) return "target";
  if (impact.dependentPaths.has(id)) return "dependent";
  if (impact.dependencyPaths.has(id)) return "dependency";
  return null;
}

export default function DependencyGraphView({
  graph,
  highlightPath,
  impact,
  onSelectFile,
}: Props) {
  const [query, setQuery] = useState("");
  const [showPackages, setShowPackages] = useState(true);

  const filtered = useMemo(() => {
    let nodes = graph.nodes;
    let edges = graph.edges;
    if (!showPackages) {
      nodes = nodes.filter((n) => n.type !== "package");
      const ids = new Set(nodes.map((n) => n.id));
      edges = edges.filter((e) => ids.has(e.source) && ids.has(e.target));
    }
    if (query.trim()) {
      const q = query.toLowerCase();
      nodes = nodes.filter(
        (n) => n.path.toLowerCase().includes(q) || n.label.toLowerCase().includes(q),
      );
      const ids = new Set(nodes.map((n) => n.id));
      edges = edges.filter((e) => ids.has(e.source) && ids.has(e.target));
    }
    return { nodes, edges };
  }, [graph, query, showPackages]);

  const laidOut = useMemo(
    () => layoutGraph(filtered.nodes, filtered.edges, impact),
    [filtered.nodes, filtered.edges, impact],
  );

  const [nodes, setNodes, onNodesChange] = useNodesState(laidOut.nodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(laidOut.edges);

  useEffect(() => {
    setNodes(laidOut.nodes);
    setEdges(laidOut.edges);
  }, [laidOut, setNodes, setEdges]);

  const onNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      if (node.id.startsWith("pkg:")) return;
      onSelectFile?.(node.id);
    },
    [onSelectFile],
  );

  return (
    <div className="h-[min(72vh,640px)] w-full overflow-hidden rounded-lg border border-[var(--app-border)] bg-white shadow-inner">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={onNodeClick}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.15}
        maxZoom={2}
        proOptions={{ hideAttribution: true }}
      >
        <Background color="#e2e8f0" gap={20} size={1} />
        <Controls className="!border-[var(--app-border)] !bg-white !shadow-sm [&>button]:!border-[var(--app-border)] [&>button]:!bg-white [&>button]:!text-slate-600" />
        <MiniMap
          nodeColor={(n) => {
            const id = n.id;
            const meta = graph.nodes.find((x) => x.id === id);
            return meta ? nodeColor(meta) : "#94a3b8";
          }}
          maskColor="#f8fafc99"
          className="!border-[var(--app-border)] !bg-white"
        />
        <Panel position="top-left" className="m-2 flex flex-wrap gap-2">
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Filter files…"
            className="input-field w-44 py-1.5 text-xs"
          />
          <label className="flex cursor-pointer items-center gap-1.5 rounded-lg border border-[var(--app-border)] bg-white px-2 py-1 text-[10px] text-[var(--app-muted)] shadow-sm">
            <input
              type="checkbox"
              checked={showPackages}
              onChange={(e) => setShowPackages(e.target.checked)}
              className="accent-[var(--brand-royal)]"
            />
            Packages
          </label>
        </Panel>
        {(highlightPath || impact) && (
          <Panel position="bottom-center" className="mb-2 flex flex-wrap justify-center gap-2">
            {impact && (
              <>
                <span className="rounded-lg border border-red-200 bg-red-50 px-2 py-1 text-[10px] text-red-800">
                  Target
                </span>
                <span className="rounded-lg border border-amber-200 bg-amber-50 px-2 py-1 text-[10px] text-amber-900">
                  Importers
                </span>
                <span className="rounded-lg border border-blue-200 bg-blue-50 px-2 py-1 text-[10px] text-blue-800">
                  Imports
                </span>
              </>
            )}
            {highlightPath && (
              <span className="rounded-lg border border-[var(--app-border)] bg-white/95 px-3 py-1 text-[10px] font-medium text-[var(--brand-royal)] shadow-sm">
                Selected: {highlightPath}
              </span>
            )}
          </Panel>
        )}
      </ReactFlow>
    </div>
  );
}
