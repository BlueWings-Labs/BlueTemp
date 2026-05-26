type AvatarSize = "xs" | "sm" | "md";

const sizes: Record<AvatarSize, string> = {
  xs: "h-5 w-5",
  sm: "h-6 w-6",
  md: "h-7 w-7",
};

const px: Record<AvatarSize, number> = {
  xs: 20,
  sm: 24,
  md: 28,
};

export function avatarUrl(src: string, size: AvatarSize = "xs") {
  const sep = src.includes("?") ? "&" : "?";
  return `${src}${sep}s=${px[size]}`;
}

export default function Avatar({
  src,
  alt,
  size = "xs",
  className = "",
}: {
  src?: string;
  alt: string;
  size?: AvatarSize;
  className?: string;
}) {
  if (!src) {
    return (
      <span
        className={`${sizes[size]} shrink-0 rounded-full border border-[var(--app-border)] bg-[var(--app-elevated)] flex items-center justify-center text-[9px] font-medium text-[var(--app-muted)] ${className}`}
        aria-hidden
      >
        {alt.slice(0, 1).toUpperCase()}
      </span>
    );
  }

  return (
    <img
      src={avatarUrl(src, size)}
      alt={alt}
      width={px[size]}
      height={px[size]}
      loading="lazy"
      decoding="async"
      className={`${sizes[size]} shrink-0 rounded-full border border-[var(--app-border)] object-cover ${className}`}
    />
  );
}
