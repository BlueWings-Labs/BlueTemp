export type AgentBackend = "ica" | "local" | "auto";

const STORAGE_KEY = "bluewings-agent-backend";

export function getStoredBackend(): AgentBackend {
  if (typeof window === "undefined") return "auto";
  const v = localStorage.getItem(STORAGE_KEY);
  if (v === "ica" || v === "local" || v === "auto") return v;
  return "auto";
}

export function setStoredBackend(backend: AgentBackend): void {
  localStorage.setItem(STORAGE_KEY, backend);
}

export function backendLabel(backend: AgentBackend): string {
  switch (backend) {
    case "ica":
      return "ICA Agent (MCP workflow)";
    case "local":
      return "Local LLM + tools";
    default:
      return "Auto (ICA if configured)";
  }
}
