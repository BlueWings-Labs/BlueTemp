import { Suspense, type ReactNode } from "react";
import AppHeader from "./AppHeader";
import WorkflowRail from "./WorkflowRail";
import ThemedPage from "./ThemedPage";
import type { WorkflowSlug } from "@/lib/brand";

const SHELL_CLASS = "mx-auto w-full max-w-6xl px-4 py-8 sm:px-6";

export default function AppShell({
  workflow,
  children,
}: {
  workflow: WorkflowSlug;
  children: ReactNode;
}) {
  return (
    <ThemedPage theme="app">
      <Suspense fallback={null}>
        <AppHeader />
      </Suspense>
      <main className={SHELL_CLASS}>
        <Suspense fallback={null}>
          <WorkflowRail active={workflow} />
        </Suspense>
        {children}
      </main>
    </ThemedPage>
  );
}
