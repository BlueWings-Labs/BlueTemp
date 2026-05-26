"use client";

import type { ReactNode } from "react";
import Avatar from "./ui/Avatar";

function fmtDate(iso: string) {
  return new Date(iso).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function BodyBlock({ body }: { body: string | null | undefined }) {
  if (!body?.trim()) {
    return <p className="text-xs italic text-[var(--app-faint)]">No description.</p>;
  }
  return (
    <pre className="whitespace-pre-wrap font-sans text-xs leading-relaxed text-[var(--app-text)]">
      {body}
    </pre>
  );
}

function Section({ title, count, children }: { title: string; count?: number; children: ReactNode }) {
  return (
    <div className="border-t border-[var(--app-border)] px-3 py-2.5">
      <h4 className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-[var(--app-muted)]">
        {title}
        {count !== undefined && (
          <span className="ml-1.5 rounded bg-[var(--app-elevated)] px-1.5 py-px text-[var(--app-faint)]">
            {count}
          </span>
        )}
      </h4>
      {children}
    </div>
  );
}

function CommentRow({
  author,
  body,
  created_at,
  meta,
}: {
  author: string;
  body: string;
  created_at: string;
  meta?: string;
}) {
  return (
    <div className="mb-2 flex gap-2 rounded-lg border border-[var(--app-border)] bg-[var(--app-elevated)] p-2 last:mb-0">
      <Avatar src={`https://github.com/${author}.png?s=20`} alt={author} size="xs" />
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5">
          <span className="text-[10px] font-medium text-[var(--brand-royal)]">{author}</span>
          <span className="text-[9px] text-[var(--app-faint)]">{fmtDate(created_at)}</span>
          {meta && <span className="text-[9px] text-[var(--app-faint)]">{meta}</span>}
        </div>
        <p className="mt-1 whitespace-pre-wrap text-xs text-[var(--app-text)]">{body}</p>
      </div>
    </div>
  );
}

export interface PRFullDetail {
  detail: {
    number: number;
    title: string;
    state: string;
    author: string;
    body: string | null;
    created_at: string;
    merged_at: string | null;
    draft: boolean;
    labels: string[];
    assignees: string[];
    reviewers: string[];
    commits: number;
    additions: number;
    deletions: number;
    changed_files: number;
    base: string;
    head: string;
    url: string;
  };
  reviews: { reviewer: string; state: string; body: string | null; submitted_at: string }[];
  inline_comments: { author: string; body: string; path: string; line: number | null; created_at: string }[];
  discussion_comments: { author: string; body: string; created_at: string; url: string }[];
  commits: { sha: string; author: string; message: string; date: string }[];
  files: { filename: string; status: string; additions: number; deletions: number; changes: number; patch: string | null }[];
}

export interface IssueFullDetail {
  detail: {
    number: number;
    title: string;
    state: string;
    author: string;
    body: string | null;
    created_at: string;
    closed_at: string | null;
    labels: string[];
    assignees: string[];
    comments: number;
    url: string;
  };
  comments: { author: string; body: string; created_at: string; url: string }[];
  events: { event: string; actor: string | null; created_at: string; label: string | null }[];
}

export function PRDetailPanel({ data }: { data: PRFullDetail }) {
  const d = data.detail;

  return (
    <div className="border-t border-[var(--app-border)] bg-[var(--app-elevated)]/80">
      <Section title="Description">
        <BodyBlock body={d.body} />
        <div className="mt-2 flex flex-wrap gap-2 text-[10px] text-[var(--app-muted)]">
          <span>+{d.additions} / −{d.deletions}</span>
          <span>·</span>
          <span>{d.changed_files} files</span>
          <span>·</span>
          <span>{d.commits} commits</span>
          <span>·</span>
          <span>{d.base} ← {d.head}</span>
        </div>
      </Section>

      {data.commits.length > 0 && (
        <Section title="Commits" count={data.commits.length}>
          <ul className="space-y-1">
            {data.commits.map((c) => (
              <li key={c.sha} className="text-[10px] text-[var(--app-muted)]">
                <span className="font-medium text-[var(--brand-royal)]">{c.sha}</span> {c.message}
              </li>
            ))}
          </ul>
        </Section>
      )}

      {data.files.length > 0 && (
        <Section title="File changes" count={data.files.length}>
          {data.files.map((f) => (
            <div key={f.filename} className="mb-2 overflow-hidden rounded-lg border border-[var(--app-border)] last:mb-0">
              <div className="flex items-center justify-between gap-2 border-b border-[var(--app-border)] bg-white px-2 py-1">
                <span className="truncate font-mono text-[10px] text-[var(--app-heading)]">
                  {f.filename}
                </span>
                <span className="shrink-0 text-[9px] text-[var(--app-muted)]">
                  {f.status} +{f.additions} −{f.deletions}
                </span>
              </div>
              {f.patch && (
                <pre className="max-h-48 overflow-auto bg-[var(--app-elevated)] p-2 font-mono text-[9px] leading-relaxed text-[var(--app-text)]">
                  {f.patch.length > 3000 ? `${f.patch.slice(0, 3000)}\n… (truncated)` : f.patch}
                </pre>
              )}
            </div>
          ))}
        </Section>
      )}

      {data.reviews.length > 0 && (
        <Section title="Reviews" count={data.reviews.length}>
          {data.reviews.map((r, i) => (
            <CommentRow
              key={`${r.reviewer}-${r.submitted_at}-${i}`}
              author={r.reviewer}
              body={r.body || `Review: ${r.state}`}
              created_at={r.submitted_at}
              meta={r.state}
            />
          ))}
        </Section>
      )}

      {data.inline_comments.length > 0 && (
        <Section title="Inline review comments" count={data.inline_comments.length}>
          {data.inline_comments.map((c, i) => (
            <CommentRow
              key={`${c.path}-${c.line}-${i}`}
              author={c.author}
              body={c.body}
              created_at={c.created_at}
              meta={`${c.path}${c.line ? `:${c.line}` : ""}`}
            />
          ))}
        </Section>
      )}

      {data.discussion_comments.length > 0 && (
        <Section title="Discussion" count={data.discussion_comments.length}>
          {data.discussion_comments.map((c, i) => (
            <CommentRow
              key={`${c.author}-${c.created_at}-${i}`}
              author={c.author}
              body={c.body}
              created_at={c.created_at}
            />
          ))}
        </Section>
      )}

      <div className="border-t border-[var(--app-border)] px-3 py-2 text-right">
        <a
          href={d.url}
          target="_blank"
          rel="noreferrer"
          className="text-[10px] font-medium text-[var(--brand-royal)] hover:underline"
        >
          Open on GitHub ↗
        </a>
      </div>
    </div>
  );
}

export function IssueDetailPanel({ data }: { data: IssueFullDetail }) {
  const d = data.detail;

  return (
    <div className="border-t border-[var(--app-border)] bg-[var(--app-elevated)]/80">
      <Section title="Description">
        <BodyBlock body={d.body} />
      </Section>

      {data.events.length > 0 && (
        <Section title="Timeline" count={data.events.length}>
          <ul className="space-y-1">
            {data.events.map((e, i) => (
              <li key={`${e.event}-${e.created_at}-${i}`} className="text-[10px] text-[var(--app-muted)]">
                <span className="font-medium text-[var(--app-heading)]">{e.event}</span>
                {e.actor && <span> by {e.actor}</span>}
                {e.label && <span className="text-[var(--brand-royal)]"> → {e.label}</span>}
                <span className="text-[var(--app-faint)]"> · {fmtDate(e.created_at)}</span>
              </li>
            ))}
          </ul>
        </Section>
      )}

      {data.comments.length > 0 && (
        <Section title="Comments" count={data.comments.length}>
          {data.comments.map((c, i) => (
            <CommentRow
              key={`${c.author}-${c.created_at}-${i}`}
              author={c.author}
              body={c.body}
              created_at={c.created_at}
            />
          ))}
        </Section>
      )}

      <div className="border-t border-[var(--app-border)] px-3 py-2 text-right">
        <a
          href={d.url}
          target="_blank"
          rel="noreferrer"
          className="text-[10px] font-medium text-[var(--brand-royal)] hover:underline"
        >
          Open on GitHub ↗
        </a>
      </div>
    </div>
  );
}
