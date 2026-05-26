import { Suspense } from "react";

export default function ContextStudioLayout({ children }: { children: React.ReactNode }) {
  return <Suspense fallback={null}>{children}</Suspense>;
}
