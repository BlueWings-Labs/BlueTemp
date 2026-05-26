"use client";

import { useState } from "react";
import type { FileTreeNode } from "@/lib/dependency-api";

function TreeRow({
  node,
  depth,
  selected,
  onSelect,
}: {
  node: FileTreeNode;
  depth: number;
  selected: string | null;
  onSelect: (path: string) => void;
}) {
  const [open, setOpen] = useState(depth < 2);
  const isDir = node.type === "directory";
  const path = node.path ?? "";

  if (isDir) {
    return (
      <div>
        <button
          type="button"
          onClick={() => setOpen((o) => !o)}
          className="flex w-full items-center gap-1 py-0.5 text-[10px] font-medium text-[var(--app-muted)] hover:text-[var(--app-heading)]"
          style={{ paddingLeft: depth * 10 }}
        >
          <span className="w-3 text-[8px]">{open ? "▾" : "▸"}</span>
          <span>{node.name || "root"}</span>
        </button>
        {open &&
          node.children?.map((ch, i) => (
            <TreeRow
              key={`${path}-${ch.name}-${i}`}
              node={ch}
              depth={depth + 1}
              selected={selected}
              onSelect={onSelect}
            />
          ))}
      </div>
    );
  }

  return (
    <button
      type="button"
      onClick={() => path && onSelect(path)}
      className={`flex w-full items-center gap-1 py-0.5 text-[10px] transition ${
        selected === path
          ? "bg-[var(--brand-pale)] font-medium text-[var(--brand-deep)]"
          : "text-[var(--app-text)] hover:bg-[var(--app-elevated)]"
      }`}
      style={{ paddingLeft: depth * 10 + 14 }}
    >
      <span className="text-[var(--app-faint)]">◇</span>
      <span className="truncate">{node.name}</span>
    </button>
  );
}

export default function FileTreePanel({
  tree,
  selected,
  onSelect,
}: {
  tree: FileTreeNode;
  selected: string | null;
  onSelect: (path: string) => void;
}) {
  return (
    <aside className="card flex max-h-[min(72vh,640px)] flex-col overflow-hidden lg:self-start">
      <h3 className="border-b border-[var(--app-border)] px-3 py-2 text-[10px] font-semibold uppercase tracking-wider text-[var(--app-muted)]">
        File tree
      </h3>
      <div className="flex-1 overflow-y-auto px-1 py-2">
        {tree.children?.map((ch, i) => (
          <TreeRow key={i} node={ch} depth={0} selected={selected} onSelect={onSelect} />
        ))}
      </div>
    </aside>
  );
}
