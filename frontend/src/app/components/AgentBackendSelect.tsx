"use client";

import {
  backendLabel,
  getStoredBackend,
  setStoredBackend,
  type AgentBackend,
} from "@/lib/agent-backend";

export default function AgentBackendSelect({
  value,
  onChange,
  icaAvailable,
  localAvailable,
  compact,
}: {
  value: AgentBackend;
  onChange: (b: AgentBackend) => void;
  icaAvailable: boolean;
  localAvailable: boolean;
  compact?: boolean;
}) {
  function pick(b: AgentBackend) {
    setStoredBackend(b);
    onChange(b);
  }

  const options: { id: AgentBackend; disabled?: boolean }[] = [
    { id: "auto" },
    { id: "ica", disabled: !icaAvailable },
    { id: "local", disabled: !localAvailable },
  ];

  return (
    <div className={compact ? "flex flex-wrap items-center gap-1.5" : "flex flex-col gap-1"}>
      {!compact && (
        <span className="text-[10px] font-medium text-[var(--app-muted)]">AI backend</span>
      )}
      <div className="flex flex-wrap gap-1">
        {options.map((opt) => (
          <button
            key={opt.id}
            type="button"
            disabled={opt.disabled}
            onClick={() => pick(opt.id)}
            title={backendLabel(opt.id)}
            className={`rounded-full border px-2.5 py-1 text-[10px] font-medium transition ${
              value === opt.id
                ? "border-[var(--brand-mid)] bg-[var(--brand-pale)] text-[var(--brand-deep)]"
                : "border-[var(--app-border)] bg-white text-[var(--app-muted)] hover:border-[var(--brand-mid)]"
            } ${opt.disabled ? "cursor-not-allowed opacity-40" : ""}`}
          >
            {opt.id === "ica" ? "ICA" : opt.id === "local" ? "Local" : "Auto"}
          </button>
        ))}
      </div>
    </div>
  );
}

/** Hook-friendly initial value from localStorage */
export function initialBackend(): AgentBackend {
  return getStoredBackend();
}
