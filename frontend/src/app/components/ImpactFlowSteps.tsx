"use client";

/** Visual guide: Ask → Answer → Graph */
export default function ImpactFlowSteps({
  activeStep = 0,
  loading,
}: {
  activeStep?: 0 | 1 | 2;
  loading?: boolean;
}) {
  const steps = [
    { num: 1, title: "Choose a topic", sub: "Right panel" },
    { num: 2, title: "Read AI answer", sub: "Chat below" },
    { num: 3, title: "Explore graph", sub: "Center, under map" },
  ];

  return (
    <div className="px-4 py-3">
      <div className="flex items-stretch gap-1">
        {steps.map((step, i) => {
          const isActive = activeStep === i;
          const isDone = activeStep > i;
          return (
            <div key={step.num} className="flex min-w-0 flex-1 items-center gap-1">
              <div
                className={`flex min-w-0 flex-1 flex-col rounded-xl border px-2.5 py-2 transition-all duration-500 ${
                  isActive
                    ? "border-[var(--brand-royal)] bg-[var(--brand-pale)] shadow-sm"
                    : isDone
                      ? "border-emerald-200 bg-emerald-50/80"
                      : "border-[var(--app-border)] bg-white/80"
                } ${loading && isActive ? "animate-pulse-ring" : ""}`}
              >
                <span
                  className={`flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-bold transition-colors ${
                    isActive
                      ? "bg-[var(--brand-royal)] text-white"
                      : isDone
                        ? "bg-emerald-500 text-white"
                        : "bg-[var(--app-elevated)] text-[var(--app-muted)]"
                  }`}
                >
                  {isDone ? "✓" : step.num}
                </span>
                <span className="mt-1 truncate text-[11px] font-semibold text-[var(--app-heading)]">
                  {step.title}
                </span>
                <span className="truncate text-[9px] text-[var(--app-muted)]">{step.sub}</span>
              </div>
              {i < steps.length - 1 && (
                <svg
                  className="h-4 w-6 shrink-0 text-[var(--brand-mid)] opacity-60"
                  viewBox="0 0 24 8"
                  aria-hidden
                >
                  <line
                    x1="0"
                    y1="4"
                    x2="20"
                    y2="4"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeDasharray="4 4"
                    className={loading && isActive ? "animate-[flow-line_1s_linear_infinite]" : ""}
                    style={{ strokeDashoffset: 0 }}
                  />
                  <polygon points="20,1 24,4 20,7" fill="currentColor" />
                </svg>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
