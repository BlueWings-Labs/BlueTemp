import type { ReactNode } from "react";

export default function PageHero({
  step,
  title,
  description,
  children,
}: {
  step: number;
  title: string;
  description: string;
  children?: ReactNode;
}) {
  return (
    <header className="mb-8 border-b border-[var(--app-border)] pb-6">
      <p className="mb-2 text-[10px] font-semibold uppercase tracking-[0.2em] text-[var(--brand-royal)]">
        Step {String(step).padStart(2, "0")}
      </p>
      <h1 className="text-2xl font-semibold tracking-tight text-[var(--app-heading)] sm:text-3xl">
        {title}
      </h1>
      <p className="mt-2 max-w-2xl text-sm leading-relaxed text-[var(--app-muted)]">
        {description}
      </p>
      {children && <div className="mt-5">{children}</div>}
    </header>
  );
}
