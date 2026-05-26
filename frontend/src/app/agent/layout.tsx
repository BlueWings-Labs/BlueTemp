import { Suspense } from "react";
import LoadingIndicator from "@/app/components/LoadingIndicator";

export default function AgentLayout({ children }: { children: React.ReactNode }) {
  return (
    <Suspense fallback={<LoadingIndicator layout="fullscreen" message="Loading agent…" size="xl" />}>
      {children}
    </Suspense>
  );
}
