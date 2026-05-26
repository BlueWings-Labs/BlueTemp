"use client";

import { useEffect, useMemo } from "react";
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
import {
  normalizeInsightGraph,
  type InsightGraph,
  type InsightGraphNode,
} from "@/lib/impact-insight-graph";

const TYPE_COLORS: Record<string, string> = {
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

function layoutInsight(
  graphNodes: InsightGraphNode[],
  graphEdges: { id: string; source: string; target: string; label?: string; kind?: string }[],
): { nodes: Node[]; edges: Edge[] } {
  const g = new dagre.graphlib.Graph();
  g.setDefaultEdgeLabel(() => ({}));
  g.setGraph({ rankdir: "TB", nodesep: 40, ranksep: 56, marginx: 20, marginy: 20 });

  const width = 168;
  const height = 40;

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
    const color = n.color ?? TYPE_COLORS[n.type] ?? "#64748b";
    const isTarget = n.type === "target";

    return {
      id: n.id,
      type: "default",
      position: {
        x: (pos?.x ?? 0) - width / 2,
        y: (pos?.y ?? 0) - height / 2,
      },
      data: {
        label: (
          <div className="flex max-w-[150px] flex-col gap-0.5 px-1">
            <span className="truncate text-[10px] font-semibold text-slate-800">{n.label}</span>
            <span className="truncate text-[8px] capitalize text-slate-500">{n.type}</span>
          </div>
        ),
      },
      style: {
        width,
        height,
        borderRadius: 8,
        border: isTarget ? "2.5px solid #dc2626" : `1.5px solid ${color}`,
        background: isTarget
          ? "linear-gradient(145deg, #fef2f2 0%, #ffffff 70%)"
          : `linear-gradient(145deg, ${color}18 0%, #ffffff 70%)`,
        boxShadow: isTarget ? "0 0 16px #dc262633" : `0 0 12px ${color}22`,
        fontSize: 10,
      },
    };
  });

  const flowEdges: Edge[] = graphEdges.map((e) => {
    const stroke =
      e.kind === "import" || e.kind === "package" ? "#7c3aed" : e.kind === "concept" ? "#0ea5e9" : "#64748b";
    return {
      id: e.id,
      source: e.source,
      target: e.target,
      label: e.label,
      labelStyle: { fill: "#64748b", fontSize: 8 },
      animated: true,
      style: { stroke, strokeWidth: 1.6 },
      markerEnd: {
        type: MarkerType.ArrowClosed,
        color: stroke,
        width: 12,
        height: 12,
      },
    };
  });

  return { nodes: flowNodes, edges: flowEdges };
}

interface Props {
  graph: InsightGraph;
}

export default function InsightGraphView({ graph }: Props) {
  const safeGraph = useMemo(() => normalizeInsightGraph(graph), [graph]);

  const laidOut = useMemo(
    () => layoutInsight(safeGraph.nodes, safeGraph.edges),
    [safeGraph.nodes, safeGraph.edges],
  );

  const [nodes, setNodes, onNodesChange] = useNodesState(laidOut.nodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(laidOut.edges);

  useEffect(() => {
    setNodes(laidOut.nodes);
    setEdges(laidOut.edges);
  }, [laidOut, setNodes, setEdges]);

  useEffect(() => {
    const t = setTimeout(() => {
      window.dispatchEvent(new Event("resize"));
    }, 400);
    return () => clearTimeout(t);
  }, [graph.kind, graph.nodes.length]);

  const title = safeGraph.ai_title ?? safeGraph.title;

  return (
    <div className="h-[min(40vh,400px)] w-full overflow-hidden rounded-lg bg-white/50">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        fitView
        fitViewOptions={{ padding: 0.25 }}
        minZoom={0.2}
        maxZoom={2}
        proOptions={{ hideAttribution: true }}
      >
        <Background color="#e2e8f0" gap={20} size={1} />
        <Controls className="!border-[var(--app-border)] !bg-white !shadow-sm [&>button]:!border-[var(--app-border)] [&>button]:!bg-white [&>button]:!text-slate-600" />
        <MiniMap
          nodeColor={(n) => {
            const meta = safeGraph.nodes.find((x) => x.id === n.id);
            return meta?.color ?? TYPE_COLORS[meta?.type ?? "file"] ?? "#94a3b8";
          }}
          maskColor="#f8fafc99"
          className="!border-[var(--app-border)] !bg-white"
        />
        <Panel position="top-left" className="m-2 max-w-md">
          <div className="rounded-lg border border-[var(--app-border)] bg-white/95 px-3 py-2 shadow-sm">
            <p className="text-xs font-semibold text-[var(--app-heading)]">{title}</p>
            {graph.description && (
              <p className="mt-0.5 text-[10px] text-[var(--app-muted)]">{safeGraph.description}</p>
            )}
          </div>
        </Panel>
        <Panel position="bottom-center" className="mb-2 flex flex-wrap justify-center gap-1.5">
          {["target", "dependent", "import", "pr", "test", "concept"].map((t) => (
            <span
              key={t}
              className="rounded-lg border border-[var(--app-border)] bg-white/95 px-2 py-0.5 text-[9px] capitalize text-[var(--app-muted)]"
              style={{ borderLeftColor: TYPE_COLORS[t], borderLeftWidth: 3 }}
            >
              {t}
            </span>
          ))}
        </Panel>
      </ReactFlow>
    </div>
  );
}
