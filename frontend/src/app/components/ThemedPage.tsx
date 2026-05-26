import type { ReactNode } from "react";
import GraphMeshBackground from "./GraphMeshBackground";

export default function ThemedPage({
  theme = "app",
  children,
  className = "",
  showMesh = true,
}: {
  theme?: "app" | "landing";
  children: ReactNode;
  className?: string;
  showMesh?: boolean;
}) {
  const themeClass = theme === "landing" ? "landing-theme" : "app-theme";

  return (
    <div className={`${themeClass} relative min-h-screen ${className}`.trim()}>
      {showMesh && <GraphMeshBackground density="light" />}
      <div className="relative z-10">{children}</div>
    </div>
  );
}
