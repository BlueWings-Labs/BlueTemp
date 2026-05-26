"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import AgentBackendSelect, { initialBackend } from "./AgentBackendSelect";
import BlastRadiusTopicGrid from "./BlastRadiusTopicGrid";
import LoadingIndicator from "./LoadingIndicator";
import AiMarkdownContent from "./AiMarkdownContent";
import { getAgentStatus } from "@/lib/agent-api";
import { type AgentBackend } from "@/lib/agent-backend";
import {
  askImpactChat,
  type ChangeImpact,
  type ImpactChatMessage,
  type ImpactInsightGraph,
  type ImpactQuickAction,
} from "@/lib/dependency-api";
import {
  buildInsightGraph,
  getQuickActionsFromImpact,
  mergeAiInsightGraph,
  normalizeInsightGraph,
  type InsightGraph,
} from "@/lib/impact-insight-graph";

function toInsightGraph(g: ImpactInsightGraph | undefined): InsightGraph | null {
  if (!g?.nodes?.length) return null;
  return normalizeInsightGraph({
    kind: g.kind,
    title: g.title,
    description: g.description,
    ai_title: g.ai_title,
    nodes: g.nodes.map((n) => ({
      id: n.id,
      label: n.label,
      type: n.type,
      group: n.group,
      color: n.color,
      path: n.path,
    })),
    edges: g.edges.map((e) => ({
      id: e.id,
      source: e.source,
      target: e.target,
      label: e.label,
      kind: e.kind,
    })),
  });
}

export default function BlastRadiusChat({
  owner,
  repo,
  impact,
  onInsightGraph,
  insightSlot,
}: {
  owner: string;
  repo: string;
  impact: ChangeImpact;
  onInsightGraph?: (graph: InsightGraph | null, actionLabel?: string) => void;
  insightSlot?: React.ReactNode;
}) {
  const target = impact.target.resolved ? impact.target.path : null;
  const [messages, setMessages] = useState<ImpactChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [backend, setBackend] = useState<AgentBackend>(() => initialBackend());
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [icaOk, setIcaOk] = useState(false);
  const [localOk, setLocalOk] = useState(false);
  const [quickActions, setQuickActions] = useState<ImpactQuickAction[]>(() =>
    getQuickActionsFromImpact(impact),
  );
  const [activeActionId, setActiveActionId] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  const actions = useMemo(
    () => (quickActions.length ? quickActions : getQuickActionsFromImpact(impact)),
    [quickActions, impact],
  );

  useEffect(() => {
    getAgentStatus()
      .then((s) => {
        setIcaOk(!!s.ica_configured);
        setLocalOk(!!s.backends_available?.local);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    setMessages([]);
    setSessionId(null);
    setError("");
    setActiveActionId(null);
    setQuickActions(getQuickActionsFromImpact(impact));
    onInsightGraph?.(null);
  }, [target, owner, repo, onInsightGraph]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  if (!target) return null;

  async function runAction(action: ImpactQuickAction) {
    setActiveActionId(action.id);
    const preview = normalizeInsightGraph(buildInsightGraph(impact, action.graph_kind));
    onInsightGraph?.(preview, action.label);
    await send(action.prompt, { actionId: action.id, actionLabel: action.label });
  }

  async function send(
    text?: string,
    opts?: { actionId?: string; actionLabel?: string },
  ) {
    const content = (text ?? input).trim();
    if (!content || loading) return;
    setInput("");
    setError("");
    const next = [...messages, { role: "user" as const, content }];
    setMessages(next);
    setLoading(true);

    try {
      const res = await askImpactChat(owner, repo, impact, next, {
        backend,
        sessionId: sessionId ?? undefined,
        actionId: opts?.actionId,
      });
      if (res.session_id) setSessionId(res.session_id);
      if (res.quick_actions?.length) setQuickActions(res.quick_actions);

      const serverGraph = toInsightGraph(res.insight_graph);
      const merged =
        serverGraph ??
        normalizeInsightGraph(
          buildInsightGraph(impact, opts?.actionId ?? "blast_map"),
        );
      onInsightGraph?.(merged, opts?.actionLabel);

      setMessages((prev) => [...prev, { role: "assistant", content: res.message }]);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Chat failed");
      setMessages((prev) => prev.slice(0, -1));
      if (!opts?.actionId) onInsightGraph?.(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col border-t border-[var(--app-border)]">
      <BlastRadiusTopicGrid
        actions={actions}
        activeActionId={activeActionId}
        loading={loading}
        onSelect={runAction}
      />

      {insightSlot}

      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--app-border)] bg-[var(--app-elevated)]/50 px-4 py-2">
        <span className="text-xs font-medium text-[var(--app-heading)]">AI conversation</span>
        <AgentBackendSelect
          value={backend}
          onChange={setBackend}
          icaAvailable={icaOk}
          localAvailable={localOk}
          compact
        />
      </div>

      <div className="max-h-[280px] min-h-[140px] space-y-3 overflow-y-auto px-4 py-3">
        {messages.length === 0 && !loading && (
          <p className="text-center text-sm text-[var(--app-muted)]">
            Choose a topic above to generate a graph and AI explanation.
          </p>
        )}
        {messages.map((m, i) => (
          <div
            key={`msg-${i}-${m.role}`}
            className="animate-fade-slide-up"
            style={{ animationDelay: `${i * 60}ms` }}
          >
            <span
              className={`mb-1 block text-[10px] font-semibold uppercase tracking-wide ${
                m.role === "user" ? "text-[var(--brand-royal)]" : "text-violet-600"
              }`}
            >
              {m.role === "user" ? "You" : "AI"}
            </span>
            <div className={m.role === "user" ? "chat-bubble-user" : "ai-chat-assistant"}>
              {m.role === "user" ? (
                <p className="whitespace-pre-wrap text-sm">{m.content}</p>
              ) : (
                <AiMarkdownContent content={m.content} />
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="animate-fade-in">
            <span className="text-[10px] font-semibold uppercase text-violet-600">AI</span>
            <div className="chat-bubble-ai mt-1">
              <LoadingIndicator layout="inline" size="xs" message="Analyzing blast radius…" />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {error && (
        <p className="border-t border-red-200 bg-red-50 px-4 py-2 text-xs text-red-700">{error}</p>
      )}

      <form
        className="flex gap-2 border-t border-[var(--app-border)] bg-white p-3"
        onSubmit={(e) => {
          e.preventDefault();
          setActiveActionId(null);
          send();
        }}
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={loading}
          placeholder="Or type your own question about this file…"
          className="input-field min-w-0 flex-1 disabled:opacity-50"
        />
        <button type="submit" disabled={loading || !input.trim()} className="btn-primary shrink-0">
          Send
        </button>
      </form>
    </div>
  );
}
