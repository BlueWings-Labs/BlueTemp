// @ts-nocheck
"use client";

import { useEffect, useState, type ReactNode } from "react";
import { useSearchParams } from "next/navigation";
import AppShell from "../components/AppShell";
import PageHero from "../components/PageHero";
import StepFooter from "../components/StepFooter";
import LoadingIndicator from "../components/LoadingIndicator";
import AgentBackendSelect, { initialBackend } from "../components/AgentBackendSelect";
import { getAgentStatus } from "@/lib/agent-api";
import { type AgentBackend } from "@/lib/agent-backend";
import {
  fetchInsights,
  askIntelligence,
  type IntelligenceInsights,
  type ChatMessage,
} from "@/lib/intelligence-api";
import { repoHref, saveRepoToSession } from "@/lib/repo-query";
import Link from "next/link";
import AiMarkdownContent from "../components/AiMarkdownContent";

const QUICK_QUESTIONS = [
  "How did this project evolve?",
  "Where should a new developer start?",
  "Which PR changed the architecture?",
  "What modules could become standalone services?",
  "Which files are risky or unstable?",
  "How difficult is migration to another stack?",
];

import { parseRepoUrl } from "@/lib/parse-repo";

function InsightCard({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="card p-4">
      <h3 className="mb-3 text-[10px] font-semibold uppercase tracking-wider text-[var(--app-muted)]">
        {title}
      </h3>
      {children}
    </section>
  );
}

export default function IntelligencePage() {
  const searchParams = useSearchParams();
  const [input, setInput] = useState(searchParams.get("repo") ?? "");
  const [owner, setOwner] = useState("");
  const [repo, setRepo] = useState("");
  const [loading, setLoading] = useState(false);
  const [insights, setInsights] = useState<IntelligenceInsights | null>(null);
  const [error, setError] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const [backend, setBackend] = useState<AgentBackend>(() => initialBackend());
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [icaConfigured, setIcaConfigured] = useState(false);
  const [localLlm, setLocalLlm] = useState(false);

  useEffect(() => {
    const q = searchParams.get("repo");
    if (q) setInput(q);
  }, [searchParams]);

  useEffect(() => {
    getAgentStatus()
      .then((s) => {
        setIcaConfigured(!!s.ica_configured);
        setLocalLlm(!!s.backends_available?.local);
      })
      .catch(() => {});
  }, []);

  async function runAnalysis() {
    const parsed = parseRepoUrl(input);
    if (!parsed) {
      setError("Enter owner/repo or a GitHub URL");
      return;
    }
    setError("");
    setLoading(true);
    setInsights(null);
    setMessages([]);
    setSessionId(null);
    setOwner(parsed.owner);
    setRepo(parsed.repo);
    saveRepoToSession(parsed.owner, parsed.repo);

    try {
      const data = await fetchInsights(parsed.owner, parsed.repo);
      setInsights(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Analysis failed");
    } finally {
      setLoading(false);
    }
  }

  async function sendQuestion(text?: string) {
    const q = (text ?? chatInput).trim();
    if (!q || !insights || chatLoading) return;
    setChatInput("");
    setError("");
    const userMsg: ChatMessage = { role: "user", content: q };
    const next = [...messages, userMsg];
    setMessages(next);
    setChatLoading(true);

    try {
      const res = await askIntelligence(owner, repo, next, insights, {
        backend,
        sessionId: sessionId ?? undefined,
      });
      if (res.session_id) setSessionId(res.session_id);
      setMessages((prev) => [...prev, { role: "assistant", content: res.message }]);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "AI request failed");
      setMessages((prev) => prev.slice(0, -1));
    } finally {
      setChatLoading(false);
    }
  }

  return (
    <AppShell workflow="intelligence">
      <PageHero
        step={3}
        title="Repository Intelligence"
        description="AI software archaeologist — evolution, architecture, onboarding paths, migration risk, and technical debt."
      >
        <form
          className="card flex gap-2 p-2"
          onSubmit={(e) => {
            e.preventDefault();
            runAnalysis();
          }}
        >
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="facebook/react or full GitHub URL"
              className="input-field min-w-0 flex-1 border-0 bg-transparent focus:ring-0"
            />
            <button type="submit" disabled={loading} className="btn-primary shrink-0 py-2">
              {loading ? "Analyzing…" : "Analyze repository"}
            </button>
          </form>

          {loading && (
            <div className="mt-4">
              <LoadingIndicator
                message="Collecting PRs, issues, commits, file tree… (30–90s on large repos)"
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

        {insights && (
          <div className="space-y-6">
            <section className="card flex flex-wrap items-center justify-between gap-3 border-[var(--brand-pale)] bg-[var(--brand-pale)]/30 p-4">
              <div>
                <h3 className="text-sm font-semibold text-[var(--app-heading)]">
                  Next: ICA Context Studio
                </h3>
                <p className="mt-1 max-w-xl text-[10px] text-[var(--app-muted)]">
                  Export project structure, module connections, JSON-LD schema instances, and seven
                  grounded docs for ICA. Intelligence snapshot is reused on export.
                </p>
              </div>
              <Link
                href={repoHref("/context-studio", owner, repo)}
                className="btn-primary shrink-0 py-2 text-xs"
              >
                Open Context Studio →
              </Link>
            </section>

            <div className="grid gap-4 md:grid-cols-2">
              <InsightCard title="Summary">
                <p className="text-sm font-medium text-[var(--app-heading)]">{insights.summary.name}</p>
                <p className="mt-1 text-xs text-[var(--app-muted)]">{insights.summary.description}</p>
                <div className="mt-2 flex flex-wrap gap-2 text-[10px] text-[var(--app-muted)]">
                  <span>{insights.summary.language}</span>
                  <span>·</span>
                  <span>{insights.summary.stats.pr_count} PRs</span>
                  <span>·</span>
                  <span>{insights.summary.stats.file_count} files</span>
                  <span>·</span>
                  <span>migration: {insights.migration.difficulty_estimate}</span>
                </div>
              </InsightCard>

              <InsightCard title="Onboarding — start here">
                <ul className="list-inside list-disc space-y-1 text-xs text-[var(--app-text)]">
                  {insights.onboarding.start_here.map((s, i) => (
                    <li key={i}>{s}</li>
                  ))}
                </ul>
              </InsightCard>
            </div>

            <InsightCard title="Architecture modules">
              <div className="grid gap-2 sm:grid-cols-2">
                {insights.architecture.modules.slice(0, 8).map((m) => (
                  <div
                    key={m.name}
                    className="rounded-lg border border-[var(--app-border)] bg-[var(--app-elevated)] px-2 py-1.5"
                  >
                    <span className="text-xs font-medium text-[var(--brand-royal)]">{m.name}/</span>
                    <span className="ml-2 text-[10px] text-[var(--app-muted)]">
                      {m.file_count} files · {m.importance}
                    </span>
                  </div>
                ))}
              </div>
              {insights.architecture.standalone_service_candidates.length > 0 && (
                <p className="mt-2 text-[10px] text-[var(--app-muted)]">
                  Service candidates:{" "}
                  {insights.architecture.standalone_service_candidates.join(", ")}
                </p>
              )}
            </InsightCard>

            <div className="grid gap-4 md:grid-cols-2">
              <InsightCard title="Hot / risky files">
                <ul className="max-h-40 space-y-1 overflow-y-auto text-[10px]">
                  {insights.hot_files.slice(0, 12).map((f) => (
                    <li key={f.path} className="flex justify-between gap-2 text-[var(--app-text)]">
                      <span className="truncate font-mono text-[10px]">{f.path}</span>
                      <span className={`shrink-0 ${f.risk === "high" ? "text-red-600" : "text-[var(--app-muted)]"}`}>
                        {f.pr_touch_count} PRs
                      </span>
                    </li>
                  ))}
                </ul>
              </InsightCard>

              <InsightCard title="Technical debt">
                <ul className="list-inside list-disc space-y-1 text-xs text-[var(--app-text)]">
                  {insights.technical_debt.length
                    ? insights.technical_debt.map((t, i) => <li key={i}>{t}</li>)
                    : <li className="text-[var(--app-muted)]">No major signals in sampled data.</li>}
                </ul>
              </InsightCard>
            </div>

            <InsightCard title="Migration & stack">
              <p className="text-xs text-[var(--app-text)]">
                Stack: {insights.migration.detected_stack.join(", ") || "unknown"}
              </p>
              <p className="mt-1 text-[10px] text-[var(--app-muted)]">
                Difficulty: <span className="font-medium text-amber-600">{insights.migration.difficulty_estimate}</span>
              </p>
              <ul className="mt-2 list-inside list-decimal space-y-1 text-[10px] text-[var(--app-muted)]">
                {insights.migration.rewrite_strategy_outline.map((s, i) => (
                  <li key={i}>{s}</li>
                ))}
              </ul>
            </InsightCard>

            {/* AI Analyst */}
            <section className="card overflow-hidden">
              <div className="border-b border-[var(--app-border)] bg-[var(--app-elevated)] px-4 py-3">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <h3 className="text-sm font-semibold text-[var(--app-heading)]">AI Analyst</h3>
                    <p className="text-[10px] text-[var(--app-muted)]">
                      ICA agent or local LLM — insights + GitHub tools
                    </p>
                  </div>
                  <AgentBackendSelect
                    value={backend}
                    onChange={setBackend}
                    icaAvailable={icaConfigured}
                    localAvailable={localLlm}
                    compact
                  />
                </div>
              </div>

              <div className="max-h-80 space-y-3 overflow-y-auto p-4">
                {messages.length === 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    {QUICK_QUESTIONS.map((q) => (
                      <button
                        key={q}
                        type="button"
                        onClick={() => sendQuestion(q)}
                        className="rounded-full border border-[var(--app-border)] bg-white px-2 py-1 text-[10px] text-[var(--app-muted)] hover:border-[var(--brand-mid)] hover:text-[var(--brand-royal)]"
                      >
                        {q}
                      </button>
                    ))}
                  </div>
                )}
                {messages.map((m, i) => (
                  <div
                    key={i}
                    className={`text-xs shadow-sm ${
                      m.role === "user" ? "ml-6 sm:ml-10 ai-chat-user" : "mr-6 sm:mr-10 ai-chat-assistant"
                    }`}
                  >
                    <p
                      className={`mb-2 flex items-center gap-1.5 text-[9px] font-semibold uppercase tracking-wide ${
                        m.role === "user" ? "text-[var(--brand-royal)]" : "text-violet-600"
                      }`}
                    >
                      <span
                        className={`inline-block h-1.5 w-1.5 rounded-full ${
                          m.role === "user" ? "bg-[var(--brand-mid)]" : "bg-violet-500"
                        }`}
                        aria-hidden
                      />
                      {m.role === "user" ? "You" : "AI Analyst"}
                    </p>
                    {m.role === "user" ? (
                      <p className="whitespace-pre-wrap leading-relaxed">{m.content}</p>
                    ) : (
                      <AiMarkdownContent content={m.content} />
                    )}
                  </div>
                ))}
                {chatLoading && (
                  <div className="flex justify-center py-2">
                    <LoadingIndicator layout="inline" size="xs" message="Thinking…" />
                  </div>
                )}
              </div>

              <form
                className="flex gap-2 border-t border-[var(--app-border)] bg-[var(--app-elevated)] p-3"
                onSubmit={(e) => {
                  e.preventDefault();
                  sendQuestion();
                }}
              >
                <input
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  disabled={chatLoading}
                  placeholder="Ask about architecture, migration, onboarding…"
                  className="min-w-0 flex-1 bg-transparent text-xs outline-none disabled:opacity-50"
                />
                <button
                  type="submit"
                  disabled={chatLoading || !chatInput.trim()}
                  className="btn-primary shrink-0 py-2 text-xs disabled:opacity-50"
                >
                  Ask
                </button>
              </form>
            </section>
          </div>
        )}

        {!insights && !loading && (
          <section className="card py-16 text-center">
            <p className="text-sm text-[var(--app-muted)]">
              Analyze a repository to unlock intelligence insights
            </p>
            <p className="mt-2 text-xs text-[var(--app-faint)]">
              Evolution · Architecture · Onboarding · Migration · Technical debt
            </p>
          </section>
        )}

      <StepFooter currentStep={3} />
    </AppShell>
  );
}
