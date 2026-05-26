"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import Logo from "../components/Logo";
import ThemedPage from "../components/ThemedPage";
import { WORKFLOW } from "@/lib/brand";
import { parseRepoUrl } from "@/lib/parse-repo";
import { repoHref } from "@/lib/repo-query";

export default function PlatformPage() {
  const router = useRouter();
  const [repo, setRepo] = useState("");

  const parsedRepo = parseRepoUrl(repo);

  function startWorkflow() {
    router.push(repoHref("/explorer", parsedRepo?.owner ?? null, parsedRepo?.repo ?? null));
  }

  return (
    <ThemedPage theme="app">
      <header className="border-b border-[var(--landing-border)] bg-white/90 backdrop-blur-md">
        <div className="mx-auto flex h-14 max-w-5xl items-center justify-between px-4 sm:px-6">
          <Logo size="sm" href="/" />
          <Link
            href="/"
            className="text-xs font-medium text-[var(--landing-muted)] hover:text-[var(--brand-royal)]"
          >
            ← Back to home
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-4 py-12 sm:px-6 sm:py-16">
        <div className="text-center">
          <div className="flex justify-center">
            <Logo size="lg" href="/" showText className="flex-col !items-center !gap-3 text-center" />
          </div>
          <h1 className="mt-8 text-3xl font-bold tracking-tight text-[var(--landing-text)]">
            Platform dashboard
          </h1>
          <p className="mx-auto mt-3 max-w-xl text-[var(--landing-muted)]">
            Follow the sequence below — each step builds on the last. Enter a repository to begin
            at Explorer, or open any module directly.
          </p>
        </div>

        <form
          className="card-landing mx-auto mt-10 max-w-xl p-2"
          onSubmit={(e) => {
            e.preventDefault();
            startWorkflow();
          }}
        >
          <div className="flex flex-col gap-2 sm:flex-row">
            <input
              type="text"
              value={repo}
              onChange={(e) => setRepo(e.target.value)}
              placeholder="owner/repo or github.com/…"
              className="input-field-light flex-1"
            />
            <button type="submit" className="btn-primary shrink-0 sm:px-8">
              Start at Explorer
            </button>
          </div>
          <p className="px-2 pb-1 pt-2 text-center text-[10px] text-[var(--landing-muted)]">
            Optional — saves time on the first step
          </p>
        </form>

        <div className="mt-14 space-y-4">
          {WORKFLOW.map((item) => (
            <article
              key={item.slug}
              className="card-landing flex flex-col gap-4 p-6 sm:flex-row sm:items-center sm:justify-between"
            >
              <div className="flex gap-4">
                <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-[var(--brand-royal)] text-sm font-semibold text-white">
                  {String(item.step).padStart(2, "0")}
                </span>
                <div>
                  <h2 className="text-lg font-semibold text-[var(--landing-text)]">
                    {item.title}
                  </h2>
                  <p className="mt-1 max-w-xl text-sm text-[var(--landing-muted)]">
                    {item.description}
                  </p>
                </div>
              </div>
              <Link
                href={repoHref(item.href, parsedRepo?.owner ?? null, parsedRepo?.repo ?? null)}
                className="btn-primary shrink-0 self-start sm:self-center"
              >
                Open {item.short}
              </Link>
            </article>
          ))}
        </div>

        <p className="mt-12 text-center text-xs text-[var(--landing-muted)]">
          API: <code className="text-[var(--brand-royal)]">localhost:8000</code> · MCP tools
          available for dependency graphs
        </p>
      </main>
    </ThemedPage>
  );
}
