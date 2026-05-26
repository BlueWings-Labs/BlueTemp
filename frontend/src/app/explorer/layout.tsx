import { Suspense } from "react";
import LoadingIndicator from "@/app/components/LoadingIndicator";

export default function ExplorerLayout({ children }: { children: React.ReactNode }) {
  return (
    <Suspense fallback={<LoadingIndicator layout="fullscreen" message="Loading explorer…" size="xl" />}>
      {children}
    </Suspense>
  );
}
