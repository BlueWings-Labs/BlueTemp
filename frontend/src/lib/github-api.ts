const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export interface RepoInfo {
  name: string;
  description: string | null;
  language: string | null;
  stars: number;
  forks: number;
  open_issues: number;
  topics: string[];
  default_branch: string;
  created_at: string;
  updated_at: string;
  url: string;
}

export interface ListItem {
  number: number;
  title: string;
  state: string;
  author: string;
  created_at: string;
  updated_at?: string;
  merged_at?: string | null;
  closed_at?: string | null;
  labels: { name: string; color: string }[];
  comments?: number;
  url: string;
}

export interface Contributor {
  login: string;
  contributions: number;
  avatar: string;
  url: string;
}

function mapLabels(labels: string[] | { name: string; color: string }[]): ListItem["labels"] {
  if (!labels.length) return [];
  if (typeof labels[0] === "string") {
    return (labels as string[]).map((name) => ({ name, color: "30363d" }));
  }
  return labels as ListItem["labels"];
}

export function getRepoInfo(owner: string, repo: string) {
  return apiGet<RepoInfo>(`/repo/${owner}/${repo}`);
}

type ApiListItem = Omit<ListItem, "labels"> & { labels: string[] };

export async function getPullRequests(owner: string, repo: string): Promise<ListItem[]> {
  const data = await apiGet<ApiListItem[]>(`/repo/${owner}/${repo}/pulls`);
  return data.map((item) => ({ ...item, labels: mapLabels(item.labels) }));
}

export async function getIssues(owner: string, repo: string): Promise<ListItem[]> {
  const data = await apiGet<ApiListItem[]>(`/repo/${owner}/${repo}/issues`);
  return data.map((item) => ({ ...item, labels: mapLabels(item.labels) }));
}

export async function getContributors(owner: string, repo: string): Promise<Contributor[]> {
  const data = await apiGet<Omit<Contributor, "avatar">[]>(`/repo/${owner}/${repo}/contributors`);
  return data.map((c) => ({
    ...c,
    avatar: `https://github.com/${c.login}.png?s=64`,
  }));
}

export function getPRFullDetail(owner: string, repo: string, prNumber: number) {
  return apiGet<import("../app/components/ItemDetailPanel").PRFullDetail>(
    `/repo/${owner}/${repo}/pulls/${prNumber}/full`,
  );
}

export function getIssueFullDetail(owner: string, repo: string, issueNumber: number) {
  return apiGet<import("../app/components/ItemDetailPanel").IssueFullDetail>(
    `/repo/${owner}/${repo}/issues/${issueNumber}/full`,
  );
}
