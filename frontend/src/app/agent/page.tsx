"use client";

import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import AppShell from "../components/AppShell";
import PageHero from "../components/PageHero";
import StepFooter from "../components/StepFooter";
import LoadingIndicator from "../components/LoadingIndicator";
import { parseRepoUrl } from "@/lib/parse-repo";
import AgentBackendSelect, { initialBackend } from "../components/AgentBackendSelect";
import {
  sendAgentMessage,
  getAgentStatus,
  type ChatMessage,
  type ToolCallLog,
  type AgentStatus,
} from "@/lib/agent-api";
import { type AgentBackend } from "@/lib/agent-backend";
import AiMarkdownContent from "../components/AiMarkdownContent";

const SUGGESTIONS = [
  "Summarize open pull requests",
  "What are the most commented issues?",
  "Who are the top contributors?",
  "Search for bugs related to authentication",
];

function MessageBubble({
  role,
  content,
  toolCalls,
}: {
  role: "user" | "assistant";
  content: string;
  toolCalls?: ToolCallLog[];
}) {
  const isUser = role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div className={`max-w-[min(92%,42rem)] ${isUser ? "ai-chat-user" : "ai-chat-assistant"}`}>
        {!isUser && (
          <p className="mb-2 flex items-center gap-1.5 text-[9px] font-semibold uppercase tracking-wider text-violet-600">
            <span className="inline-block h-1.5 w-1.5 rounded-full bg-violet-500" aria-hidden />
            Assistant
          </p>
        )}
        {isUser ? (
          <p className="whitespace-pre-wrap text-xs leading-relaxed">{content}</p>
        ) : (
          <AiMarkdownContent content={content} size="sm" />
        )}
        {toolCalls && toolCalls.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1 border-t border-[var(--app-border)] pt-2">
            {toolCalls.map((t, i) => (
              <span
                key={`${t.name}-${i}`}
                className="rounded border border-[var(--brand-pale)] bg-[var(--brand-pale)] px-1.5 py-px text-[9px] font-medium text-[var(--brand-deep)]"
              >
                {t.name}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function defaultAgentRepo() {
  return { input: "facebook/react", owner: "facebook", repo: "react" };
}

export default function AgentPage() {
  const searchParams = useSearchParams();
  const repoFromQuery = searchParams.get("repo");
  const parsedQuery = repoFromQuery ? parseRepoUrl(repoFromQuery) : null;
  const defaults = defaultAgentRepo();
  const [repoInput, setRepoInput] = useState(repoFromQuery ?? defaults.input);
  const [owner, setOwner] = useState(parsedQuery?.owner ?? defaults.owner);
  const [repo, setRepo] = useState(parsedQuery?.repo ?? defaults.repo);
  const [messages, setMessages] = useState<(ChatMessage & { tool_calls?: ToolCallLog[] })[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [status, setStatus] = useState<AgentStatus | null>(null);
  const [backend, setBackend] = useState<AgentBackend>(() => initialBackend());
  const [sessionId, setSessionId] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const q = searchParams.get("repo");
    if (!q) return;
    setRepoInput(q);
    const parsed = parseRepoUrl(q);
    if (parsed) {
      setOwner(parsed.owner);
      setRepo(parsed.repo);
      setError("");
    }
  }, [searchParams]);

  useEffect(() => {
    getAgentStatus().then(setStatus).catch(() => setStatus(null));
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  function applyRepo() {
    const parsed = parseRepoUrl(repoInput);
    if (parsed) {
      setOwner(parsed.owner);
      setRepo(parsed.repo);
      setError("");
    } else {
      setError("Invalid repo — use owner/repo");
    }
  }

  async function handleSend(text?: string) {
    const content = (text ?? input).trim();
    if (!content || loading) return;

    setInput("");
    setError("");
    const userMsg: ChatMessage = { role: "user", content };
    const nextMessages = [...messages, userMsg];
    setMessages(nextMessages);
    setLoading(true);

    try {
      const res = await sendAgentMessage(
        nextMessages.map(({ role, content: c }) => ({ role, content: c })),
        owner,
        repo,
        { backend, sessionId: sessionId ?? undefined },
      );
      if (res.session_id) setSessionId(res.session_id);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: res.message, tool_calls: res.tool_calls },
      ]);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Agent failed";
      setError(msg);
      setMessages((prev) => prev.slice(0, -1));
    } finally {
      setLoading(false);
    }
  }

  return (
    <AppShell workflow="agent">
      <PageHero
        step={5}
        title="AI Agent"
        description="Chat with ICA (MCP workflow) or local LLM — GitHub tools and dependency analysis."
      />

      <div className="flex flex-col gap-4">
        <section className="card flex flex-wrap items-center gap-2 p-3">
          <span className="text-[10px] font-medium text-[var(--app-muted)]">Repo</span>
          <input
            value={repoInput}
            onChange={(e) => setRepoInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && applyRepo()}
            className="input-field min-w-0 flex-1 border-0 bg-transparent py-1.5 focus:ring-0"
            placeholder="owner/repo"
          />
          <button
            type="button"
            onClick={applyRepo}
            className="rounded-lg border border-[var(--app-border)] px-3 py-1.5 text-xs text-[var(--app-muted)] hover:text-[var(--app-heading)]"
          >
            Set
          </button>
          <span className="text-[10px] font-medium text-[var(--brand-royal)]">
            {owner}/{repo}
          </span>
          <div className="ml-auto flex flex-wrap items-center gap-2">
            <AgentBackendSelect
              value={backend}
              onChange={setBackend}
              icaAvailable={!!status?.ica_configured}
              localAvailable={!!status?.backends_available?.local}
              compact
            />
            {status && (
              <span className="text-[9px] text-[var(--app-muted)]">
                {status.ica_configured ? "ICA ready" : "ICA not configured"}
                {status.llm_configured ? " · Local LLM ready" : ""}
              </span>
            )}
          </div>
        </section>

        {error && (
          <p className="mb-2 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
            {error}
          </p>
        )}

        <section className="card flex min-h-[420px] flex-1 flex-col overflow-hidden">
          <div className="flex-1 space-y-3 overflow-y-auto p-3">
            {messages.length === 0 && (
              <div className="py-8 text-center">
                <p className="text-sm text-[var(--app-muted)]">
                  Ask about <span className="font-medium text-[var(--brand-royal)]">{owner}/{repo}</span>
                </p>
                <p className="mt-1 text-[10px] text-[var(--app-faint)]">
                  Choose ICA, Local, or Auto above
                </p>
                <div className="mt-4 flex flex-wrap justify-center gap-1.5">
                  {SUGGESTIONS.map((s) => (
                    <button
                      key={s}
                      type="button"
                      onClick={() => handleSend(s)}
                      className="rounded-full border border-[var(--app-border)] bg-white px-2.5 py-1 text-[10px] text-[var(--app-muted)] transition hover:border-[var(--brand-mid)] hover:text-[var(--brand-royal)]"
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((m, i) => (
              <MessageBubble
                key={i}
                role={m.role}
                content={m.content}
                toolCalls={m.tool_calls}
              />
            ))}

            {loading && (
              <div className="flex justify-start">
                <div className="rounded-xl border border-[var(--app-border)] bg-white px-3 py-2 shadow-sm">
                  <LoadingIndicator
                    layout="inline"
                    size="xs"
                    message={backend === "ica" ? "ICA agent thinking…" : "Calling GitHub tools…"}
                  />
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          <form
            className="flex gap-2 border-t border-[var(--app-border)] bg-[var(--app-elevated)] p-3"
            onSubmit={(e) => {
              e.preventDefault();
              handleSend();
            }}
          >
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={loading}
              placeholder="Ask about PRs, issues, contributors…"
              className="input-field min-w-0 flex-1 py-2 text-xs disabled:opacity-50"
            />
            <button type="submit" disabled={loading || !input.trim()} className="btn-primary shrink-0 py-2 text-xs disabled:opacity-50">
              Send
            </button>
          </form>
        </section>

        <StepFooter currentStep={4} />
      </div>
    </AppShell>
  );
}
