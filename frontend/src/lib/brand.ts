export const BRAND = {
  name: "BlueWings",
  tagline: "GitHub Repository Intelligence",
  logoSrc: "/icon.png",
  loadingSrc: "/icon.webm",
  colors: {
    deep: "#1e40af",
    royal: "#2563eb",
    mid: "#3b82f6",
    sky: "#38bdf8",
    light: "#7dd3fc",
    pale: "#e0f2fe",
  },
} as const;

export const WORKFLOW = [
  {
    step: 1,
    slug: "explorer",
    href: "/explorer",
    title: "Repository Explorer",
    short: "Explorer",
    description: "Browse pull requests, issues, and contributors with full detail panels.",
    icon: "◎",
  },
  {
    step: 2,
    slug: "dependencies",
    href: "/dependencies",
    title: "Dependency Graph",
    short: "Dependencies",
    description: "Map import relationships across your codebase with an interactive graph.",
    icon: "⑂",
  },
  {
    step: 3,
    slug: "intelligence",
    href: "/intelligence",
    title: "Repository Intelligence",
    short: "Intelligence",
    description: "Evolution, hot files, onboarding paths, and migration insights powered by AI.",
    icon: "◇",
  },
  {
    step: 4,
    slug: "context-studio",
    href: "/context-studio",
    title: "Context Studio",
    short: "Context",
    description:
      "Export ICA-ready JSON-LD schema, project docs, and facts so agents remember your codebase.",
    icon: "⬡",
  },
  {
    step: 5,
    slug: "agent",
    href: "/agent",
    title: "AI Agent",
    short: "Agent",
    description: "Chat with tools that query GitHub and analyze your repository in real time.",
    icon: "✦",
  },
] as const;

export type WorkflowSlug = (typeof WORKFLOW)[number]["slug"];
