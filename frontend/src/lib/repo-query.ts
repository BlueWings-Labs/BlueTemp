export function formatRepoKey(owner: string, repo: string): string {
  return `${owner}/${repo}`;
}

export function repoHref(path: string, owner: string | null, repo: string | null): string {
  if (!owner || !repo) return path;
  return `${path}?repo=${encodeURIComponent(formatRepoKey(owner, repo))}`;
}

const STORAGE_KEY = "bluewings-active-repo";

export function saveRepoToSession(owner: string, repo: string): void {
  if (typeof window === "undefined") return;
  sessionStorage.setItem(STORAGE_KEY, formatRepoKey(owner, repo));
}

export function loadRepoFromSession(): string | null {
  if (typeof window === "undefined") return null;
  return sessionStorage.getItem(STORAGE_KEY);
}
