/**
 * Parses a GitHub repo URL or "owner/repo" shorthand.
 * Supports github.com and github.ibm.com (GitHub Enterprise).
 *
 * Returns { owner, repo, host } or null if unparseable.
 *   host: "github.com" | "github.ibm.com"
 */

export type ParsedRepo = {
  owner: string;
  repo: string;
  /** Normalized host — use this to pass github_host to API calls */
  host: "github.com" | "github.ibm.com";
};

const KNOWN_HOSTS = ["github.ibm.com", "github.com"] as const;
type KnownHost = (typeof KNOWN_HOSTS)[number];

function normalizeHost(hostname: string): KnownHost {
  // Check most-specific first (ibm before com) to avoid substring collision
  for (const h of KNOWN_HOSTS) {
    if (hostname === h || hostname.endsWith(`.${h}`)) return h;
  }
  return "github.com"; // fallback for bare owner/repo input
}

export function parseRepoUrl(input: string): ParsedRepo | null {
  try {
    const cleaned = input.trim().replace(/\/$/, "");

    // ── URL form: https://github.com/… or https://github.ibm.com/… ──────────
    if (cleaned.includes("/")) {
      const withScheme = cleaned.startsWith("http")
        ? cleaned
        : `https://${cleaned}`;
      try {
        const url = new URL(withScheme);
        const parts = url.pathname.split("/").filter(Boolean);
        if (parts.length >= 2) {
          return {
            owner: parts[0],
            repo: parts[1].replace(/\.git$/, ""),
            host: normalizeHost(url.hostname),
          };
        }
      } catch {
        // Not a valid URL — fall through to owner/repo split below
      }
    }

    // ── Bare shorthand: owner/repo ────────────────────────────────────────────
    const [owner, repo] = cleaned.split("/");
    if (owner && repo) {
      return { owner, repo: repo.replace(/\.git$/, ""), host: "github.com" };
    }
  } catch {
    /* ignore */
  }
  return null;
}