import Link from "next/link";
import { WORKFLOW } from "@/lib/brand";

export default function StepFooter({ currentStep }: { currentStep: number }) {
  const prev = WORKFLOW.find((w) => w.step === currentStep - 1);
  const next = WORKFLOW.find((w) => w.step === currentStep + 1);

  return (
    <footer className="mt-10 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-[var(--app-border)] bg-[var(--app-elevated)] px-4 py-3">
      {prev ? (
        <Link
          href={prev.href}
          className="text-xs font-medium text-[var(--app-muted)] transition hover:text-[var(--brand-sky)]"
        >
          ← {prev.short}
        </Link>
      ) : (
        <Link href="/platform" className="text-xs text-[var(--app-muted)] hover:text-[var(--brand-sky)]">
          ← Platform
        </Link>
      )}
      {next ? (
        <Link href={next.href} className="btn-primary py-2 text-xs">
          Continue to {next.short} →
        </Link>
      ) : (
        <Link href="/platform" className="text-xs text-[var(--brand-sky)]">
          Back to dashboard
        </Link>
      )}
    </footer>
  );
}
