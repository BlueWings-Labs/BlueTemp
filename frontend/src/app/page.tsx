import Image from "next/image";
import Link from "next/link";
import Logo from "./components/Logo";
import ThemedPage from "./components/ThemedPage";
import { BRAND, WORKFLOW } from "@/lib/brand";

export default function LandingPage() {
  return (
    <ThemedPage theme="landing">
      {/* Nav */}
      <header className="sticky top-0 z-50 border-b border-[var(--landing-border)] bg-white/85 backdrop-blur-xl">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
          <Logo size="md" href="/" />
          <nav className="hidden items-center gap-8 text-sm font-medium text-[var(--landing-muted)] md:flex">
            <a href="#features" className="transition hover:text-[var(--brand-royal)]">
              Features
            </a>
            <a href="#workflow" className="transition hover:text-[var(--brand-royal)]">
              Workflow
            </a>
            <a href="#platform" className="transition hover:text-[var(--brand-royal)]">
              Platform
            </a>
          </nav>
          <Link href="/platform" className="btn-primary text-xs sm:text-sm">
            Enter platform
          </Link>
        </div>
      </header>

      {/* Hero */}
      <section className="relative overflow-hidden border-b border-[var(--landing-border)]">
        <div className="mx-auto max-w-6xl px-4 pb-24 pt-16 sm:px-6 sm:pt-24 lg:pb-32">
          <div className="grid items-center gap-12 lg:grid-cols-2 lg:gap-16">
            <div>
              <p className="mb-4 inline-flex items-center gap-2 rounded-full border border-[var(--brand-pale)] bg-[var(--brand-pale)] px-3 py-1 text-xs font-semibold text-[var(--brand-deep)]">
                <span className="h-1.5 w-1.5 rounded-full bg-[var(--brand-mid)]" />
                AI-powered repository intelligence
              </p>
              <h1 className="text-4xl font-bold leading-[1.1] tracking-tight text-[var(--landing-text)] sm:text-5xl lg:text-6xl">
                Understand any{" "}
                <span className="bg-gradient-to-r from-[var(--brand-deep)] to-[var(--brand-sky)] bg-clip-text text-transparent">
                  GitHub codebase
                </span>{" "}
                in minutes
              </h1>
              <p className="mt-6 max-w-lg text-lg leading-relaxed text-[var(--landing-muted)]">
                {BRAND.name} helps teams explore history, visualize dependencies, uncover
                architecture insights, and collaborate with an intelligent agent — all in one
                professional workspace.
              </p>
              <div className="mt-10 flex flex-wrap items-center gap-4">
                <Link href="/platform" className="btn-primary">
                  Launch platform
                  <span aria-hidden>→</span>
                </Link>
                <Link href="/explorer" className="btn-secondary">
                  Start with Explorer
                </Link>
              </div>
              <dl className="mt-12 grid grid-cols-3 gap-6 border-t border-[var(--landing-border)] pt-8">
                {[
                  { label: "Modules", value: "5" },
                  { label: "MCP ready", value: "Yes" },
                  { label: "Graph export", value: "JSON" },
                ].map((s) => (
                  <div key={s.label}>
                    <dt className="text-xs font-medium uppercase tracking-wider text-[var(--landing-muted)]">
                      {s.label}
                    </dt>
                    <dd className="mt-1 text-xl font-bold text-[var(--brand-deep)]">{s.value}</dd>
                  </div>
                ))}
              </dl>
            </div>
            <div className="relative flex justify-center lg:justify-end">
              <div className="rounded-3xl border border-[var(--landing-border)] bg-white p-10 shadow-xl shadow-slate-200/60">
                <Image
                  src={BRAND.logoSrc}
                  alt={BRAND.name}
                  width={280}
                  height={280}
                  className="mx-auto"
                  priority
                />
              </div>
              <div className="absolute -right-4 top-8 hidden rounded-xl border border-[var(--landing-border)] bg-white px-4 py-3 shadow-lg lg:block">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-[var(--landing-muted)]">
                  Dependency graph
                </p>
                <p className="mt-0.5 font-mono text-sm font-semibold text-[var(--brand-royal)]">
                  Interactive
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="border-t border-[var(--landing-border)] bg-[var(--landing-surface)] py-20">
        <div className="mx-auto max-w-6xl px-4 sm:px-6">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight text-[var(--landing-text)]">
              Everything you need to master a repo
            </h2>
            <p className="mt-3 text-[var(--landing-muted)]">
              Five integrated capabilities, from exploration and graphs to ICA agent context and AI chat.
            </p>
          </div>
          <div className="mt-14 grid gap-6 sm:grid-cols-2">
            {WORKFLOW.map((item) => (
              <article
                key={item.slug}
                className="card-landing group p-6 hover:border-[var(--brand-light)]"
              >
                <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-[var(--brand-royal)] to-[var(--brand-sky)] text-lg text-white shadow-md">
                  {item.icon}
                </span>
                <p className="mt-4 font-mono text-[10px] font-bold uppercase tracking-widest text-[var(--brand-mid)]">
                  Step {String(item.step).padStart(2, "0")}
                </p>
                <h3 className="mt-1 text-lg font-semibold text-[var(--landing-text)]">
                  {item.title}
                </h3>
                <p className="mt-2 text-sm leading-relaxed text-[var(--landing-muted)]">
                  {item.description}
                </p>
                <Link
                  href={item.href}
                  className="mt-4 inline-flex text-sm font-semibold text-[var(--brand-royal)] transition group-hover:gap-2"
                >
                  Open module →
                </Link>
              </article>
            ))}
          </div>
        </div>
      </section>

      {/* Workflow */}
      <section id="workflow" className="py-20">
        <div className="mx-auto max-w-6xl px-4 sm:px-6">
          <h2 className="text-center text-3xl font-bold text-[var(--landing-text)]">
            A professional workflow, step by step
          </h2>
          <ol className="mx-auto mt-14 max-w-3xl space-y-0">
            {WORKFLOW.map((item, i) => (
              <li key={item.slug} className="relative flex gap-6 pb-12 last:pb-0">
                {i < WORKFLOW.length - 1 && (
                  <span
                    className="absolute left-5 top-10 h-full w-px bg-[var(--app-border)]"
                    aria-hidden
                  />
                )}
                <span className="relative z-10 flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-[var(--brand-pale)] bg-white text-sm font-semibold text-[var(--brand-deep)] shadow-sm">
                  {item.step}
                </span>
                <div className="pt-1">
                  <h3 className="font-semibold text-[var(--landing-text)]">{item.title}</h3>
                  <p className="mt-1 text-sm text-[var(--landing-muted)]">{item.description}</p>
                </div>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* CTA */}
      <section
        id="platform"
        className="relative isolate border-t border-[var(--landing-border)] bg-gradient-to-br from-[var(--brand-deep)] to-[var(--brand-mid)] py-20 text-white"
      >
        <div className="mx-auto max-w-3xl px-4 text-center sm:px-6">
          <Image
            src={BRAND.logoSrc}
            alt=""
            width={64}
            height={64}
            className="mx-auto brightness-0 invert"
          />
          <h2 className="mt-6 text-3xl font-bold">Ready to enter the platform?</h2>
          <p className="mt-3 text-blue-100">
            Start at the dashboard, pick your repository, and move through Explorer → Dependencies
            → Intelligence → Agent.
          </p>
          <Link
            href="/platform"
            className="mt-8 inline-flex rounded-xl bg-white px-8 py-3 text-sm font-bold text-[var(--brand-deep)] shadow-xl transition hover:bg-[var(--brand-pale)]"
          >
            Enter BlueWings platform
          </Link>
        </div>
      </section>

      <footer className="border-t border-[var(--landing-border)] py-10">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 px-4 sm:flex-row sm:px-6">
          <Logo size="sm" href="/" />
          <p className="text-xs text-[var(--landing-muted)]">
            © {new Date().getFullYear()} {BRAND.name}. Repository intelligence for modern teams.
          </p>
        </div>
      </footer>
    </ThemedPage>
  );
}
