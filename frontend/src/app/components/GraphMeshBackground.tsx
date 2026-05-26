type Density = "light" | "medium";

/** Subtle static network — background only, no distracting motion */
const EDGES: { x1: number; y1: number; x2: number; y2: number }[] = [
  { x1: 100, y1: 100, x2: 320, y2: 80 },
  { x1: 320, y1: 80, x2: 520, y2: 140 },
  { x1: 520, y1: 140, x2: 720, y2: 90 },
  { x1: 720, y1: 90, x2: 1000, y2: 120 },
  { x1: 320, y1: 80, x2: 380, y2: 280 },
  { x1: 520, y1: 140, x2: 560, y2: 320 },
  { x1: 120, y1: 400, x2: 380, y2: 280 },
  { x1: 380, y1: 280, x2: 560, y2: 320 },
  { x1: 560, y1: 320, x2: 800, y2: 420 },
  { x1: 800, y1: 420, x2: 1000, y2: 380 },
];

const NODES: { cx: number; cy: number }[] = [
  { cx: 100, cy: 100 },
  { cx: 320, cy: 80 },
  { cx: 520, cy: 140 },
  { cx: 720, cy: 90 },
  { cx: 1000, cy: 120 },
  { cx: 380, cy: 280 },
  { cx: 560, cy: 320 },
  { cx: 120, cy: 400 },
  { cx: 800, cy: 420 },
  { cx: 1000, cy: 380 },
];

export default function GraphMeshBackground({
  density = "light",
  className = "",
}: {
  density?: Density;
  className?: string;
}) {
  const opacity = density === "medium" ? 1 : 0.85;

  return (
    <div
      className={`pointer-events-none absolute inset-0 overflow-hidden ${className}`.trim()}
      aria-hidden
    >
      <svg
        className="h-full w-full text-[var(--brand-royal)]"
        viewBox="0 0 1100 500"
        preserveAspectRatio="xMidYMid slice"
        style={{ opacity }}
      >
        {EDGES.map((e, i) => (
          <line
            key={i}
            x1={e.x1}
            y1={e.y1}
            x2={e.x2}
            y2={e.y2}
            stroke="currentColor"
            strokeOpacity={0.06}
            strokeWidth={1}
          />
        ))}
        {NODES.map((n, i) => (
          <circle
            key={i}
            cx={n.cx}
            cy={n.cy}
            r={2.5}
            fill="currentColor"
            fillOpacity={0.12}
          />
        ))}
      </svg>
    </div>
  );
}
