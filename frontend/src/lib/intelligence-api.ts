import type { AgentBackend } from "./agent-backend";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface IntelligenceInsights {
  summary?: {
    name?: string;
    description?: string | null;
    language?: string | null;
    stats?: { pr_count?: number; file_count?: number };
  };
  evolution?: Record<string, unknown>;
  modules?: Record<string, unknown>;
  onboarding?: Record<string, unknown>;
  migration?: { difficulty_estimate?: string };
  [key: string]: unknown;
}

export async function fetchInsights(owner: string, repo: string): Promise<IntelligenceInsights> {
  const res = await fetch(`${API_BASE}/repo/${owner}/${repo}/intelligence/insights`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function askIntelligence(
  owner: string,
  repo: string,
  messages: ChatMessage[],
  insights?: IntelligenceInsights | null,
  options?: { backend?: AgentBackend; sessionId?: string },
) {
  const res = await fetch(`${API_BASE}/repo/${owner}/${repo}/intelligence/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      messages,
      insights: insights ?? undefined,
      backend: options?.backend ?? "auto",
      session_id: options?.sessionId ?? null,
    }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<{
    message: string;
    model: string;
    provider?: string;
    backend?: string;
    session_id?: string;
  }>;
}

