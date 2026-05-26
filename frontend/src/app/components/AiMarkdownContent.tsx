"use client";

import type { Components } from "react-markdown";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

const markdownComponents: Components = {
  h2: ({ children }) => (
    <h2 className="ai-md-h2">
      <span className="ai-md-h2-accent" aria-hidden />
      {children}
    </h2>
  ),
  h3: ({ children }) => <h3 className="ai-md-h3">{children}</h3>,
  h4: ({ children }) => <h4 className="ai-md-h4">{children}</h4>,
  p: ({ children }) => <p className="ai-md-p">{children}</p>,
  ul: ({ children }) => <ul className="ai-md-ul">{children}</ul>,
  ol: ({ children }) => <ol className="ai-md-ol">{children}</ol>,
  li: ({ children }) => <li className="ai-md-li">{children}</li>,
  strong: ({ children }) => <strong className="ai-md-strong">{children}</strong>,
  em: ({ children }) => <em className="ai-md-em">{children}</em>,
  blockquote: ({ children }) => (
    <blockquote className="ai-md-blockquote">{children}</blockquote>
  ),
  hr: () => <hr className="ai-md-hr" />,
  a: ({ href, children }) => (
    <a href={href} className="ai-md-link" target="_blank" rel="noopener noreferrer">
      {children}
    </a>
  ),
  table: ({ children }) => (
    <div className="ai-md-table-wrap">
      <table className="ai-md-table">{children}</table>
    </div>
  ),
  thead: ({ children }) => <thead className="ai-md-thead">{children}</thead>,
  tbody: ({ children }) => <tbody>{children}</tbody>,
  tr: ({ children }) => <tr className="ai-md-tr">{children}</tr>,
  th: ({ children }) => <th className="ai-md-th">{children}</th>,
  td: ({ children }) => <td className="ai-md-td">{children}</td>,
  code: ({ className, children, ...props }) => {
    const inline = !className;
    if (inline) {
      return (
        <code className="ai-md-code-inline" {...props}>
          {children}
        </code>
      );
    }
    return (
      <code className={`ai-md-code-block ${className ?? ""}`} {...props}>
        {children}
      </code>
    );
  },
  pre: ({ children }) => <pre className="ai-md-pre">{children}</pre>,
};

export default function AiMarkdownContent({
  content,
  size = "md",
}: {
  content: string;
  size?: "sm" | "md";
}) {
  return (
    <div className={`ai-markdown ${size === "sm" ? "ai-markdown-sm" : ""}`}>
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
        {content}
      </ReactMarkdown>
    </div>
  );
}
