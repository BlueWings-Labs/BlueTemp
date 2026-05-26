import { BRAND } from "@/lib/brand";

const VIDEO_SIZES = {
  xs: "h-5 w-5",
  sm: "h-8 w-8",
  md: "h-12 w-12",
  lg: "h-16 w-16",
  xl: "h-24 w-24",
} as const;

type Size = keyof typeof VIDEO_SIZES;
type Layout = "inline" | "centered" | "fullscreen";

export default function LoadingIndicator({
  message,
  size = "md",
  layout = "centered",
  className = "",
}: {
  message?: string;
  size?: Size;
  layout?: Layout;
  className?: string;
}) {
  const video = (
    <video
      src={BRAND.loadingSrc}
      autoPlay
      loop
      muted
      playsInline
      aria-hidden
      className={`shrink-0 object-contain ${VIDEO_SIZES[size]}`}
    />
  );

  if (layout === "inline") {
    return (
      <span
        className={`inline-flex items-center gap-2 ${className}`.trim()}
        role="status"
        aria-live="polite"
        aria-busy="true"
      >
        {video}
        {message && <span className="text-xs text-[var(--app-muted)]">{message}</span>}
      </span>
    );
  }

  const layoutClass =
    layout === "fullscreen"
      ? "app-theme flex min-h-screen flex-col items-center justify-center gap-3 bg-[var(--app-base)]"
      : "flex flex-col items-center justify-center gap-3 py-8";

  return (
    <div
      className={`${layoutClass} ${className}`.trim()}
      role="status"
      aria-live="polite"
      aria-busy="true"
    >
      {video}
      {message && <p className="text-center text-xs text-[var(--app-muted)]">{message}</p>}
    </div>
  );
}
