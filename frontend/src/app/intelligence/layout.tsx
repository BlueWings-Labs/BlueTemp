import { Suspense } from "react";
import LoadingIndicator from "@/app/components/LoadingIndicator";

export default function IntelligenceLayout({ children }: { children: React.ReactNode }) {
  return (
    <Suspense fallback={<LoadingIndicator layout="fullscreen" message="Loading intelligence…" size="xl" />}>
      {children}
    </Suspense>
  );
}
