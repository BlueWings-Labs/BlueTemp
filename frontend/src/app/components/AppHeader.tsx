"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import Logo from "./Logo";
import { WORKFLOW } from "@/lib/brand";

export default function AppHeader() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-50 border-b border-[var(--app-border)] bg-white/90 shadow-sm backdrop-blur-xl">
      <div className="mx-auto flex h-14 max-w-6xl items-center gap-4 px-4 sm:px-6">
        <Logo size="sm" href="/platform" />

        <nav className="ml-1 hidden items-center gap-1 md:flex">
          <Link
            href="/platform"
            className={`rounded-lg px-3 py-1.5 text-xs font-medium transition ${
              pathname === "/platform"
                ? "bg-[var(--app-elevated)] text-[var(--app-heading)]"
                : "text-[var(--app-muted)] hover:text-[var(--app-heading)]"
            }`}
          >
            Platform
          </Link>
          {WORKFLOW.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={`rounded-lg px-3 py-1.5 text-xs font-medium transition ${
                pathname === item.href
                  ? "bg-[var(--brand-pale)] text-[var(--brand-deep)]"
                  : "text-[var(--app-muted)] hover:bg-[var(--app-elevated)] hover:text-[var(--app-heading)]"
              }`}
            >
              {item.short}
            </Link>
          ))}
        </nav>

        <div className="ml-auto flex items-center gap-2">
          <Link
            href="/"
            className="rounded-lg border border-[var(--app-border)] px-3 py-1.5 text-xs font-medium text-[var(--app-muted)] transition hover:border-[var(--brand-mid)] hover:text-[var(--app-heading)]"
          >
            Home
          </Link>
        </div>
      </div>
    </header>
  );
}
