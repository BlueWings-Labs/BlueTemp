import type { AgentBackend } from "./agent-backend";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ToolCallLog {
  name: string;
  arguments: Record<string, unknown>;
}

export interface AgentChatResponse {
  message: string;
  tool_calls: ToolCallLog[];
  model: string;
  provider?: string;
  backend?: string;
  session_id?: string;
}

export interface AgentStatus {
  llm_configured: boolean;
  provider: string | null;
  model: string | null;
  gemini_configured?: boolean;
  groq_configured?: boolean;
  ollama_reachable?: boolean;
  grok_configured: boolean;
  openai_configured: boolean;
  github_token_set: boolean;
  free_options?: string[];
  ica_configured?: boolean;
  default_backend?: AgentBackend;
  backends_available?: { ica: boolean; local: boolean };
  ica?: { configured: boolean; flow_id?: string | null };
}

export async function getAgentStatus(): Promise<AgentStatus> {
  const res = await fetch(`${API_BASE}/agent/status`);
  if (!res.ok) throw new Error("Failed to load agent status");
  return res.json();
}

export async function sendAgentMessage(
  messages: ChatMessage[],
  owner?: string,
  repo?: string,
  options?: {
    backend?: AgentBackend;
    sessionId?: string;
  },
): Promise<AgentChatResponse> {
  const res = await fetch(`${API_BASE}/agent/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      messages,
      owner: owner || null,
      repo: repo || null,
      backend: options?.backend ?? "auto",
      session_id: options?.sessionId ?? null,
    }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.detail ?? data.error ?? `Agent request failed (${res.status})`);
  }
  return data;
}
