import Image from "next/image";
import Link from "next/link";
import { BRAND } from "@/lib/brand";

export default function Logo({
  size = "md",
  showText = true,
  href = "/",
  className = "",
}: {
  size?: "sm" | "md" | "lg" | "xl";
  showText?: boolean;
  href?: string;
  className?: string;
}) {
  const sizes = {
    sm: { img: 28, text: "text-sm" },
    md: { img: 36, text: "text-base" },
    lg: { img: 48, text: "text-lg" },
    xl: { img: 72, text: "text-2xl" },
  };
  const s = sizes[size];

  const inner = (
    <span className={`inline-flex items-center gap-2.5 ${className}`.trim()}>
      <Image
        src={BRAND.logoSrc}
        alt={`${BRAND.name} logo`}
        width={s.img}
        height={s.img}
        className="shrink-0 object-contain"
        priority={size === "xl" || size === "lg"}
      />
      {showText && (
        <span className="flex flex-col leading-none">
          <span className={`font-semibold tracking-tight ${s.text}`}>{BRAND.name}</span>
          {size !== "sm" && (
            <span className="mt-0.5 text-[10px] font-medium uppercase tracking-[0.2em] text-[var(--app-muted)]">
              IBM Intelligence
            </span>
          )}
        </span>
      )}
    </span>
  );

  if (href) {
    return (
      <Link href={href} className="transition opacity-95 hover:opacity-100">
        {inner}
      </Link>
    );
  }
  return inner;
}
