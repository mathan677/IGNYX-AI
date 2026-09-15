"use client";

import { useEffect, useRef, useState } from "react";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ||
  "http://127.0.0.1:8000";

/* =========================================================
   TYPES
========================================================= */

type Source = {
  title: string;
  url: string;
};

type Message = {
  id: number;
  role: "user" | "assistant";
  content: string;
  createdAt: string;
  sources?: Source[];
};

type Conversation = {
  id: number;
  title: string;
  updatedAt: string;
  messages: Message[];
};

type Memory = {
  id: number;
  user_key?: string;
  category: string;
  key: string;
  value: string;
  importance: number;
  created_at?: string;
  updated_at?: string;
};

/* =========================================================
   ICONS
========================================================= */

function FlameIcon({
  size = 30,
  className = "",
}: {
  size?: number;
  className?: string;
}) {
  return (
    <img
      src="/ignyx-logo.png"
      alt="IGNYX AI"
      width={size}
      height={size}
      className={className}
      style={{
        width: `${size}px`,
        height: `${size}px`,
        objectFit: "contain",
        display: "block",
      }}
    />
  );
}

function SendIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none">
      <path
        d="M21 3L10.5 13.5"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
      <path
        d="M21 3L14.3 21L10.5 13.5L3 9.7L21 3Z"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function GlobeIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none">
      <circle
        cx="12"
        cy="12"
        r="8"
        stroke="currentColor"
        strokeWidth="1.8"
      />
      <path
        d="M4 12H20M12 4C14 6.2 15 8.8 15 12C15 15.2 14 17.8 12 20C10 17.8 9 15.2 9 12C9 8.8 10 6.2 12 4Z"
        stroke="currentColor"
        strokeWidth="1.8"
      />
    </svg>
  );
}

function PlusIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none">
      <path
        d="M12 5V19M5 12H19"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      />
    </svg>
  );
}

function CopyIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none">
      <rect
        x="9"
        y="9"
        width="10"
        height="10"
        rx="2"
        stroke="currentColor"
        strokeWidth="1.8"
      />
      <path
        d="M15 9V7C15 5.9 14.1 5 13 5H7C5.9 5 5 5.9 5 7V13C5 14.1 5.9 15 7 15H9"
        stroke="currentColor"
        strokeWidth="1.8"
      />
    </svg>
  );
}

function MenuIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none">
      <path
        d="M5 7H19M5 12H19M5 17H19"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
    </svg>
  );
}

function PaperClipIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none">
      <path
        d="M21.4 11.6L12.2 20.8C9.8 23.2 5.9 23.2 3.5 20.8C1.1 18.4 1.1 14.5 3.5 12.1L12.1 3.5C13.8 1.8 16.5 1.8 18.2 3.5C19.9 5.2 19.9 7.9 18.2 9.6L9.6 18.2C8.8 19 7.4 19 6.6 18.2C5.8 17.4 5.8 16 6.6 15.2L14.5 7.3"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
      />
    </svg>
  );
}

/* =========================================================
   HELPERS
========================================================= */

function generateId() {
  return Date.now() + Math.floor(Math.random() * 1000);
}

function getTime() {
  return new Intl.DateTimeFormat("en-IN", {
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date());
}

function formatBackendTime(value: unknown): string {
  if (!value) return "Just now";

  const date = new Date(String(value));

  if (Number.isNaN(date.getTime())) {
    return "Just now";
  }

  return new Intl.DateTimeFormat("en-IN", {
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function createTemporaryConversationId() {
  return -(Date.now() + Math.floor(Math.random() * 1000));
}

/*
  IMPORTANT:
  This converts ANY backend response into safe text.

  Fixes:
  Objects are not valid as React child
*/

function normalizeText(value: unknown): string {
  if (value === null || value === undefined) {
    return "";
  }

  if (typeof value === "string") {
    return value;
  }

  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }

  if (Array.isArray(value)) {
    return value.map(normalizeText).filter(Boolean).join("\n");
  }

  if (typeof value === "object") {
    const obj = value as Record<string, unknown>;

    if (typeof obj.content === "string") return obj.content;
    if (typeof obj.message === "string") return obj.message;
    if (typeof obj.answer === "string") return obj.answer;
    if (typeof obj.response === "string") return obj.response;
    if (typeof obj.text === "string") return obj.text;

    return JSON.stringify(value, null, 2);
  }

  return String(value);
}

function normalizeSources(value: unknown): Source[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value
    .map((item): Source | null => {
      if (!item || typeof item !== "object") {
        return null;
      }

      const obj = item as Record<string, unknown>;

      const title =
        typeof obj.title === "string"
          ? obj.title
          : typeof obj.name === "string"
            ? obj.name
            : "Source";

      const url =
        typeof obj.url === "string"
          ? obj.url
          : typeof obj.link === "string"
            ? obj.link
            : "";

      if (!url) {
        return null;
      }

      return {
        title,
        url,
      };
    })
    .filter((source): source is Source => source !== null);
}

/* =========================================================
   MARKDOWN + CODE + TABLE RENDERER
========================================================= */

type TableAlignment = "left" | "center" | "right";

function splitTableRow(line: string): string[] {
  let value = line.trim();
  if (value.startsWith("|")) value = value.slice(1);
  if (value.endsWith("|") && !value.endsWith("\\|")) {
    value = value.slice(0, -1);
  }

  const cells: string[] = [];
  let current = "";
  let escaped = false;

  for (const char of value) {
    if (escaped) {
      current += char;
      escaped = false;
      continue;
    }

    if (char === "\\") {
      current += char;
      escaped = true;
      continue;
    }

    if (char === "|") {
      cells.push(current.trim());
      current = "";
    } else {
      current += char;
    }
  }

  cells.push(current.trim());
  return cells.map((cell) => cell.replace(/\\\|/g, "|"));
}

function isTableSeparator(line: string): boolean {
  const cells = splitTableRow(line);
  return (
    cells.length > 0 &&
    cells.every((cell) => /^:?-{3,}:?$/.test(cell.trim()))
  );
}

function tableAlignment(value: string): TableAlignment {
  const trimmed = value.trim();
  if (trimmed.startsWith(":") && trimmed.endsWith(":")) return "center";
  if (trimmed.endsWith(":")) return "right";
  return "left";
}

const LANGUAGE_ALIASES: Record<string, string> = {
  js: "javascript",
  jsx: "javascript",
  ts: "typescript",
  tsx: "typescript",
  py: "python",
  sh: "bash",
  shell: "bash",
  zsh: "bash",
  ps: "powershell",
  ps1: "powershell",
  psd1: "powershell",
  yml: "yaml",
  md: "markdown",
  text: "text",
  plaintext: "text",
  plain: "text",
  html: "html",
  xml: "html",
  csharp: "c#",
  cs: "c#",
  cpp: "cpp",
};

const LANGUAGE_KEYWORDS: Record<string, Set<string>> = {
  javascript: new Set([
    "as", "async", "await", "break", "case", "catch", "class", "const",
    "continue", "debugger", "default", "delete", "do", "else", "export",
    "extends", "finally", "for", "from", "function", "get", "if", "import",
    "in", "instanceof", "let", "new", "of", "return", "set", "static",
    "super", "switch", "this", "throw", "try", "typeof", "var", "void",
    "while", "with", "yield", "true", "false", "null", "undefined",
  ]),
  typescript: new Set([
    "as", "async", "await", "break", "case", "catch", "class", "const",
    "continue", "debugger", "declare", "default", "delete", "do", "else",
    "enum", "export", "extends", "finally", "for", "from", "function", "if",
    "implements", "import", "in", "infer", "instanceof", "interface", "keyof",
    "let", "module", "namespace", "never", "new", "null", "of", "private",
    "protected", "public", "readonly", "return", "static", "super", "switch",
    "this", "throw", "try", "type", "typeof", "undefined", "unknown", "var",
    "void", "while", "with", "yield", "true", "false",
  ]),
  python: new Set([
    "and", "as", "assert", "async", "await", "break", "case", "class", "continue",
    "def", "del", "elif", "else", "except", "False", "finally", "for", "from",
    "global", "if", "import", "in", "is", "lambda", "match", "None", "nonlocal",
    "not", "or", "pass", "raise", "return", "True", "try", "while", "with", "yield",
  ]),
  bash: new Set([
    "if", "then", "else", "elif", "fi", "for", "while", "in", "do", "done", "case",
    "esac", "function", "select", "time", "until", "export", "local", "readonly", "return",
  ]),
  powershell: new Set([
    "begin", "break", "catch", "class", "continue", "data", "define", "do", "dynamicparam",
    "else", "elseif", "end", "exit", "filter", "finally", "for", "foreach", "from", "function",
    "if", "in", "param", "process", "return", "switch", "throw", "trap", "try", "until", "using",
    "while", "workflow", "true", "false", "null", "and", "or", "not", "xor",
  ]),
  sql: new Set([
    "select", "from", "where", "and", "or", "not", "insert", "into", "values", "update", "set",
    "delete", "create", "alter", "drop", "table", "view", "index", "join", "inner", "left", "right",
    "full", "outer", "on", "as", "group", "by", "order", "having", "limit", "offset", "distinct",
    "union", "all", "case", "when", "then", "else", "end", "null", "is", "like", "between", "exists",
    "primary", "key", "foreign", "references", "constraint", "database", "schema",
  ]),
  json: new Set(["true", "false", "null"]),
  java: new Set([
    "abstract", "assert", "boolean", "break", "byte", "case", "catch", "char", "class", "const", "continue",
    "default", "do", "double", "else", "enum", "extends", "final", "finally", "float", "for", "if", "implements",
    "import", "instanceof", "int", "interface", "long", "native", "new", "package", "private", "protected", "public",
    "return", "short", "static", "strictfp", "super", "switch", "synchronized", "this", "throw", "throws", "transient",
    "try", "void", "volatile", "while", "true", "false", "null",
  ]),
  "c#": new Set([
    "abstract", "as", "base", "bool", "break", "byte", "case", "catch", "char", "checked", "class", "const",
    "continue", "decimal", "default", "delegate", "do", "double", "else", "enum", "event", "explicit", "extern",
    "false", "finally", "fixed", "float", "for", "foreach", "goto", "if", "implicit", "in", "int", "interface",
    "internal", "is", "lock", "long", "namespace", "new", "null", "object", "operator", "out", "override", "params",
    "private", "protected", "public", "readonly", "ref", "return", "sbyte", "sealed", "short", "sizeof", "stackalloc",
    "static", "string", "struct", "switch", "this", "throw", "true", "try", "typeof", "uint", "ulong", "unchecked",
    "unsafe", "ushort", "using", "virtual", "void", "volatile", "while",
  ]),
};

function normalizeLanguage(language: string): string {
  const cleaned = language.trim().toLowerCase().split(/\s+/)[0];
  return LANGUAGE_ALIASES[cleaned] ?? (cleaned || "text");
}

function highlightCodeLine(line: string, language: string): React.ReactNode[] {
  const lang = normalizeLanguage(language);
  const keywords = LANGUAGE_KEYWORDS[lang] ?? new Set<string>();
  const pattern = /\/\/.*$|<!--[\\s\\S]*?-->|#.*$|\/\*[\\s\\S]*?\*\/|'(?:\\\\.|[^'\\\\])*'|"(?:\\\\.|[^"\\\\])*"|`(?:\\\\.|[^`\\\\])*`|\b\d+(?:\.\d+)?\b|\b[A-Za-z_$][\w$-]*\b/g;
  const result: React.ReactNode[] = [];
  let lastIndex = 0;

  const pushText = (value: string, key: string) => {
    if (value) result.push(<span key={key}>{value}</span>);
  };

  let match: RegExpExecArray | null;
  while ((match = pattern.exec(line)) !== null) {
    const token = match[0];
    const index = match.index;
    pushText(line.slice(lastIndex, index), `text-${index}`);

    const lower = token.toLowerCase();
    let className = "syntax-token";

    if (/^(?:\/\/|#|<!--|\/\*)/.test(token)) {
      className = "syntax-comment";
    } else if (/^['"`]/.test(token)) {
      className = "syntax-string";
    } else if (/^\d/.test(token)) {
      className = "syntax-number";
    } else if (keywords.has(token) || keywords.has(lower)) {
      className = "syntax-keyword";
    } else if (/^[A-Za-z_$][\w$-]*$/.test(token) && /\s*\(/.test(line.slice(index + token.length))) {
      className = "syntax-function";
    } else if (
      lang === "json" &&
      /^\s*:/.test(line.slice(index + token.length))
    ) {
      className = "syntax-property";
    } else if (/^[@$][A-Za-z_]/.test(token)) {
      className = "syntax-variable";
    }

    result.push(
      <span key={`${className}-${index}`} className={className}>
        {token}
      </span>
    );
    lastIndex = index + token.length;
  }

  pushText(line.slice(lastIndex), "tail");
  return result.length > 0 ? result : [<span key="empty">{line}</span>];
}

function CodeBlock({
  code,
  language,
}: {
  code: string;
  language: string;
}) {
  const [copied, setCopied] = useState(false);
  const normalizedLanguage = normalizeLanguage(language);
  const displayLanguage = language.trim()
    ? language.trim()
    : "code";
  const lines = code.replace(/\r\n/g, "\n").split("\n");

  const copyCode = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1600);
    } catch (error) {
      console.warn("Code copy failed:", error);
    }
  };

  return (
    <div className="markdown-code-shell">
      <div className="markdown-code-toolbar">
        <span className="code-language-badge">
          {displayLanguage}
        </span>
        <button
          type="button"
          className="code-copy-button"
          onClick={copyCode}
          aria-label="Copy code"
        >
          {copied ? "✓ Copied" : "Copy"}
        </button>
      </div>

      <pre className={`markdown-code-block language-${normalizedLanguage}`}>
        <code>
          {lines.map((line, index) => (
            <span className="code-line" key={index}>
              <span className="code-line-number" aria-hidden="true">
                {index + 1}
              </span>
              <span className="code-line-content">
                {highlightCodeLine(line, normalizedLanguage)}
              </span>
            </span>
          ))}
        </code>
      </pre>
    </div>
  );
}

function renderInline(text: string): React.ReactNode[] {
  const pattern = /(\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)|`([^`]+)`|\*\*([^*]+)\*\*|__([^_]+)__|~~([^~]+)~~|(?<!\*)\*([^*\n]+)\*(?!\*)|(?<!_)_([^_\n]+)_(?!_))/g;
  const parts: React.ReactNode[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = pattern.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(<span key={`text-${match.index}`}>{text.slice(lastIndex, match.index)}</span>);
    }

    if (match[2] && match[3]) {
      parts.push(
        <a
          key={`link-${match.index}`}
          href={match[3]}
          target="_blank"
          rel="noopener noreferrer"
        >
          {match[2]}
        </a>
      );
    } else if (match[4] !== undefined) {
      parts.push(
        <code key={`inline-code-${match.index}`}>
          {match[4]}
        </code>
      );
    } else if (match[5] || match[6]) {
      parts.push(<strong key={`bold-${match.index}`}>{match[5] ?? match[6]}</strong>);
    } else if (match[7]) {
      parts.push(<del key={`strike-${match.index}`}>{match[7]}</del>);
    } else if (match[8] || match[9]) {
      parts.push(<em key={`italic-${match.index}`}>{match[8] ?? match[9]}</em>);
    }

    lastIndex = match.index + match[0].length;
  }

  if (lastIndex < text.length) {
    parts.push(<span key="tail">{text.slice(lastIndex)}</span>);
  }

  if (parts.length === 0) {
    return [<span key="plain">{text}</span>];
  }

  return parts;
}

function MarkdownTable({
  header,
  separator,
  rows,
}: {
  header: string[];
  separator: string[];
  rows: string[][];
}) {
  const alignments = header.map((_, index) =>
    tableAlignment(separator[index] ?? "---")
  );

  return (
    <div className="markdown-table-wrap" role="region" aria-label="Markdown table" tabIndex={0}>
      <table className="markdown-table">
        <thead>
          <tr>
            {header.map((cell, index) => (
              <th
                key={index}
                style={{ textAlign: alignments[index] }}
              >
                {renderInline(cell)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rowIndex) => (
            <tr key={rowIndex}>
              {header.map((_, columnIndex) => (
                <td
                  key={columnIndex}
                  style={{ textAlign: alignments[columnIndex] }}
                >
                  {renderInline(row[columnIndex] ?? "")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function MarkdownMessage({ content }: { content: string }) {
  const lines = content.replace(/\r\n/g, "\n").split("\n");
  const elements: React.ReactNode[] = [];
  let unorderedItems: Array<{ text: string; checked?: boolean }> = [];
  let orderedItems: string[] = [];
  let codeLines: string[] = [];
  let codeLanguage = "";
  let insideCodeBlock = false;

  const flushUnorderedList = () => {
    if (!unorderedItems.length) return;
    elements.push(
      <ul key={`unordered-${elements.length}`}>
        {unorderedItems.map((item, index) => (
          <li key={index} className={item.checked !== undefined ? "task-list-item" : undefined}>
            {item.checked !== undefined && (
              <span className="task-checkbox" aria-hidden="true">
                {item.checked ? "✓" : ""}
              </span>
            )}
            {renderInline(item.text)}
          </li>
        ))}
      </ul>
    );
    unorderedItems = [];
  };

  const flushOrderedList = () => {
    if (!orderedItems.length) return;
    elements.push(
      <ol key={`ordered-${elements.length}`}>
        {orderedItems.map((item, index) => (
          <li key={index}>{renderInline(item)}</li>
        ))}
      </ol>
    );
    orderedItems = [];
  };

  const flushLists = () => {
    flushUnorderedList();
    flushOrderedList();
  };

  const flushCodeBlock = () => {
    elements.push(
      <CodeBlock
        key={`code-${elements.length}`}
        code={codeLines.join("\n")}
        language={codeLanguage}
      />
    );
    codeLines = [];
    codeLanguage = "";
    insideCodeBlock = false;
  };

  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index];
    const trimmed = line.trim();

    if (trimmed.startsWith("```")) {
      flushLists();
      if (!insideCodeBlock) {
        insideCodeBlock = true;
        codeLanguage = trimmed.slice(3).trim();
      } else {
        flushCodeBlock();
      }
      continue;
    }

    if (insideCodeBlock) {
      codeLines.push(line);
      continue;
    }

    /* GFM tables: header + separator + data rows. */
    if (
      index + 1 < lines.length &&
      trimmed.includes("|") &&
      isTableSeparator(lines[index + 1].trim())
    ) {
      flushLists();
      const header = splitTableRow(line);
      const separator = splitTableRow(lines[index + 1]);
      const rows: string[][] = [];
      let tableIndex = index + 2;

      while (tableIndex < lines.length) {
        const next = lines[tableIndex].trim();
        if (!next || !next.includes("|")) break;
        rows.push(splitTableRow(next));
        tableIndex += 1;
      }

      elements.push(
        <MarkdownTable
          key={`table-${index}`}
          header={header}
          separator={separator}
          rows={rows}
        />
      );

      index = tableIndex - 1;
      continue;
    }

    const taskMatch = trimmed.match(/^[-*+]\s+\[([ xX])\]\s+(.+)$/);
    if (taskMatch) {
      flushOrderedList();
      unorderedItems.push({
        text: taskMatch[2],
        checked: taskMatch[1].toLowerCase() === "x",
      });
      continue;
    }

    if (trimmed.startsWith("- ") || trimmed.startsWith("* ") || trimmed.startsWith("+ ")) {
      flushOrderedList();
      unorderedItems.push({ text: trimmed.slice(2) });
      continue;
    }

    const orderedMatch = trimmed.match(/^\d+[.)]\s+(.+)$/);
    if (orderedMatch) {
      flushUnorderedList();
      orderedItems.push(orderedMatch[1]);
      continue;
    }

    flushLists();

    if (!trimmed) {
      elements.push(
        <div key={`space-${index}`} className="markdown-space" aria-hidden="true" />
      );
      continue;
    }

    if (/^#{1,6}\s+/.test(trimmed)) {
      const heading = trimmed.match(/^(#{1,6})\s+(.+)$/)!;
      const level = heading[1].length;
      const headingText = renderInline(heading[2]);

      if (level === 1) elements.push(<h1 key={index}>{headingText}</h1>);
      else if (level === 2) elements.push(<h2 key={index}>{headingText}</h2>);
      else if (level === 3) elements.push(<h3 key={index}>{headingText}</h3>);
      else if (level === 4) elements.push(<h4 key={index}>{headingText}</h4>);
      else if (level === 5) elements.push(<h5 key={index}>{headingText}</h5>);
      else elements.push(<h6 key={index}>{headingText}</h6>);
      continue;
    }

    if (trimmed.startsWith(">")) {
      elements.push(
        <blockquote key={index}>
          {renderInline(trimmed.replace(/^>\s?/, ""))}
        </blockquote>
      );
      continue;
    }

    if (/^([-*_])(?:\s*\1){2,}$/.test(trimmed)) {
      elements.push(<hr key={index} />);
      continue;
    }

    /* Simple bare URL support. */
    const bareUrlMatch = trimmed.match(/^(https?:\/\/\S+)$/);
    if (bareUrlMatch) {
      elements.push(
        <p key={index}>
          <a href={bareUrlMatch[1]} target="_blank" rel="noopener noreferrer">
            {bareUrlMatch[1]}
          </a>
        </p>
      );
      continue;
    }

    elements.push(<p key={index}>{renderInline(trimmed)}</p>);
  }

  if (insideCodeBlock) {
    flushCodeBlock();
  }
  flushLists();

  return <div className="markdown-content">{elements}</div>;
}

/* =========================================================
   THINKING LOADER
========================================================= */

function ThinkingLoader() {
  return (
    <div className="thinking-row">
      <div className="thinking-avatar">
        <FlameIcon size={25} />
      </div>

      <div className="thinking-card">
        <div className="thinking-orb">
          <div className="orb-core" />
          <div className="orb-ring ring-one" />
          <div className="orb-ring ring-two" />
        </div>

        <div className="thinking-text">
          <strong>INGTAING</strong>

          <div className="thinking-dots">
            <span />
            <span />
            <span />
          </div>
        </div>
      </div>
    </div>
  );
}

/* =========================================================
   APP
========================================================= */

export default function Home() {
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const [memoryOpen, setMemoryOpen] = useState(false);
  const [memories, setMemories] = useState<Memory[]>([]);
  const [memoryLoading, setMemoryLoading] = useState(false);
  const [memoryError, setMemoryError] = useState("");
  const [memorySearch, setMemorySearch] = useState("");
  const [editingMemoryId, setEditingMemoryId] = useState<number | null>(null);
  const [memoryDraft, setMemoryDraft] = useState({ value: "", category: "general", importance: "0.5" });

  const [webSearch, setWebSearch] = useState(true);

  const [input, setInput] = useState("");

  const [loading, setLoading] = useState(false);

  const [copiedId, setCopiedId] = useState<number | null>(null);

  const [conversations, setConversations] =
    useState<Conversation[]>([]);

  const [activeConversationId, setActiveConversationId] =
    useState<number | null>(null);

  const [loadingConversations, setLoadingConversations] =
    useState(false);

  const [loadingConversation, setLoadingConversation] =
    useState(false);

  const chatEndRef = useRef<HTMLDivElement | null>(null);

  const inputRef = useRef<HTMLTextAreaElement | null>(null);

  const mountedRef = useRef(true);

  const activeConversation =
    conversations.find(
      (conversation) =>
        conversation.id === activeConversationId
    ) || null;

  /* =======================================================
     LIFECYCLE
  ======================================================= */

  useEffect(() => {
    mountedRef.current = true;

    return () => {
      mountedRef.current = false;
    };
  }, []);

  /* =======================================================
     LOAD LOCAL HISTORY FIRST
  ======================================================= */

  useEffect(() => {
    const saved =
      localStorage.getItem(
        "ignyx-conversations"
      );

    if (!saved) return;

    try {
      const parsed = JSON.parse(saved);

      if (!Array.isArray(parsed)) return;

      const safeConversations: Conversation[] =
        parsed
          .map(
            (item): Conversation | null => {
              const id = Number(item?.id);

              if (!Number.isFinite(id)) {
                return null;
              }

              return {
                id,
                title:
                  normalizeText(
                    item?.title
                  ) ||
                  "New Conversation",
                updatedAt:
                  normalizeText(
                    item?.updatedAt
                  ) ||
                  "Just now",
                messages:
                  Array.isArray(
                    item?.messages
                  )
                    ? item.messages
                        .map(
                          (
                            message: any
                          ) => ({
                            id:
                              Number(
                                message?.id
                              ) ||
                              generateId(),
                            role:
                              message?.role ===
                              "assistant"
                                ? "assistant"
                                : "user",
                            content:
                              normalizeText(
                                message?.content
                              ),
                            createdAt:
                              normalizeText(
                                message?.createdAt
                              ) ||
                              getTime(),
                            sources:
                              normalizeSources(
                                message?.sources
                              ),
                          })
                        )
                    : [],
              };
            }
          )
          .filter(
            (
              conversation
            ): conversation is Conversation =>
              conversation !== null
          );

      setConversations(
        safeConversations
      );

      if (
        safeConversations.length > 0
      ) {
        setActiveConversationId(
          (current) =>
            current ??
            safeConversations[0].id
        );
      }
    } catch {
      console.warn(
        "Could not load local conversation history."
      );
    }
  }, []);

  /* =======================================================
     SYNC CONVERSATIONS FROM BACKEND
  ======================================================= */

  useEffect(() => {
    let cancelled = false;

    const loadBackendConversations =
      async () => {
        setLoadingConversations(true);

        try {
          const response =
            await fetch(
              `${API_BASE}/conversations`,
              {
                method: "GET",
                headers: {
                  Accept:
                    "application/json",
                },
                cache: "no-store",
              }
            );

          if (!response.ok) {
            throw new Error(
              `Backend returned HTTP ${response.status}.`
            );
          }

          const data =
            await response.json();

          if (
            cancelled ||
            !Array.isArray(data)
          ) {
            return;
          }

          const backendConversations: Conversation[] =
            data
              .map((item: any) => ({
                id: Number(item?.id),
                title:
                  normalizeText(
                    item?.title
                  ) ||
                  "New Conversation",
                updatedAt:
                  formatBackendTime(
                    item?.updated_at
                  ),
                messages: [],
              }))
              .filter(
                (conversation) =>
                  Number.isFinite(
                    conversation.id
                  )
              );

          setConversations(
            (previous) => {
              const localById =
                new Map(
                  previous.map(
                    (conversation) => [
                      conversation.id,
                      conversation,
                    ]
                  )
                );

              const merged =
                backendConversations.map(
                  (
                    backendConversation
                  ) => {
                    const local =
                      localById.get(
                        backendConversation.id
                      );

                    return local
                      ? {
                          ...backendConversation,
                          title:
                            local.title ||
                            backendConversation.title,
                          messages:
                            local.messages,
                          updatedAt:
                            backendConversation.updatedAt ||
                            local.updatedAt,
                        }
                      : backendConversation;
                  }
                );

              const temporary =
                previous.filter(
                  (conversation) =>
                    conversation.id < 0
                );

              return [
                ...temporary,
                ...merged,
              ];
            }
          );

          setActiveConversationId(
            (current) => {
              if (
                current !== null &&
                current < 0
              ) {
                return current;
              }

              if (
                current !== null &&
                backendConversations.some(
                  (conversation) =>
                    conversation.id ===
                    current
                )
              ) {
                return current;
              }

              return (
                backendConversations[0]
                  ?.id ??
                current
              );
            }
          );
        } catch (error) {
          console.warn(
            "Backend conversation sync unavailable:",
            error
          );
        } finally {
          if (!cancelled) {
            setLoadingConversations(
              false
            );
          }
        }
      };

    void loadBackendConversations();

    return () => {
      cancelled = true;
    };
  }, []);

  /* =======================================================
     LOAD ACTIVE BACKEND CONVERSATION
  ======================================================= */

  useEffect(() => {
    if (
      activeConversationId ===
        null ||
      activeConversationId < 0
    ) {
      return;
    }

    const existingConversation =
      conversations.find(
        (conversation) =>
          conversation.id ===
          activeConversationId
      );

    if (
      existingConversation &&
      existingConversation.messages
        .length > 0
    ) {
      return;
    }

    let cancelled = false;

    const loadConversation =
      async () => {
        setLoadingConversation(true);

        try {
          const response =
            await fetch(
              `${API_BASE}/conversations/${activeConversationId}`,
              {
                method: "GET",
                headers: {
                  Accept:
                    "application/json",
                },
                cache: "no-store",
              }
            );

          if (
            response.status ===
            404
          ) {
            return;
          }

          if (!response.ok) {
            throw new Error(
              `Backend returned HTTP ${response.status}.`
            );
          }

          const data =
            await response.json();

          if (
            cancelled ||
            !data
          ) {
            return;
          }

          const backendMessages: Message[] =
            Array.isArray(
              data?.messages
            )
              ? data.messages.map(
                  (message: any) => ({
                    id:
                      Number(
                        message?.id
                      ) ||
                      generateId(),
                    role:
                      message?.role ===
                      "assistant"
                        ? "assistant"
                        : "user",
                    content:
                      normalizeText(
                        message?.content
                      ),
                    createdAt:
                      formatBackendTime(
                        message?.created_at
                      ),
                    sources:
                      normalizeSources(
                        message?.sources
                      ),
                  })
                )
              : [];

          setConversations(
            (previous) =>
              previous.map(
                (conversation) =>
                  conversation.id ===
                  activeConversationId
                    ? {
                        ...conversation,
                        title:
                          normalizeText(
                            data?.title
                          ) ||
                          conversation.title,
                        updatedAt:
                          formatBackendTime(
                            data?.updated_at
                          ),
                        messages:
                          backendMessages,
                      }
                    : conversation
              )
          );
        } catch (error) {
          console.warn(
            "Could not load conversation:",
            error
          );
        } finally {
          if (!cancelled) {
            setLoadingConversation(
              false
            );
          }
        }
      };

    void loadConversation();

    return () => {
      cancelled = true;
    };
  }, [
    activeConversationId,
  ]);

  /* =======================================================
     SAVE LOCAL HISTORY
  =======================================================

  useEffect(() => {
    try {
      if (conversations.length === 0) {
        localStorage.removeItem(
          "ignyx-conversations"
        );
        return;
      }

      localStorage.setItem(
        "ignyx-conversations",
        JSON.stringify(
          conversations
        )
      );
    } catch (error) {
      console.warn(
        "Could not save conversation history:",
        error
      );
    }
  }, [conversations]);

  /* =======================================================
     AUTO SCROLL
  ======================================================= */

  useEffect(() => {
    requestAnimationFrame(() => {
      chatEndRef.current?.scrollIntoView(
        {
          behavior:
            loading ||
            loadingConversation
              ? "auto"
              : "smooth",
          block: "end",
        }
      );
    });
  }, [
    activeConversation?.messages
      .length,
    loading,
    loadingConversation,
  ]);

  /* =======================================================
     CREATE CONVERSATION
  ======================================================= */

  const createConversation = () => {
    const conversation: Conversation = {
      id: createTemporaryConversationId(),
      title: "New Conversation",
      updatedAt: "Just now",
      messages: [],
    };

    setConversations((previous) => [
      conversation,
      ...previous,
    ]);

    setActiveConversationId(conversation.id);

    setInput("");

    return conversation.id;
  };

  /* =======================================================
     UPDATE CONVERSATION
  ======================================================= */

  const updateConversation = (
    conversationId: number,
    updater: (conversation: Conversation) => Conversation
  ) => {
    setConversations((previous) =>
      previous.map((conversation) =>
        conversation.id === conversationId
          ? updater(conversation)
          : conversation
      )
    );
  };

  /* =======================================================
     BACKEND REQUEST
  ======================================================= */

  async function askBackend(
    message: string,
    conversationId: number
  ) {
    const controller =
      new AbortController();

    const timeoutId =
      window.setTimeout(
        () => controller.abort(),
        120000
      );

    try {
      const response =
        await fetch(
          `${API_BASE}/chat`,
          {
            method: "POST",
            headers: {
              "Content-Type":
                "application/json",
              Accept:
                "application/json",
            },
            body: JSON.stringify({
              message,
              conversation_id:
                Number(
                  conversationId
                ),
              web_search:
                webSearch,
            }),
            signal:
              controller.signal,
            cache: "no-store",
          }
        );

      let data: any = null;

      try {
        data =
          await response.json();
      } catch {
        data = null;
      }

      if (data?.error === true) {
        const errorType =
          data?.type ??
          data?.error_type ??
          "api_error";

        const errorMessage =
          data?.message ??
          data?.detail?.message ??
          (typeof data?.detail === "string"
            ? data.detail
            : "IGNYX could not complete the request.");

        throw new Error(
          JSON.stringify({
            type: errorType,
            message: errorMessage,
            status: response.status,
          })
        );
      }

      if (!response.ok) {
        const detail =
          data?.detail;

        const errorType =
          data?.type ??
          detail?.type ??
          (response.status === 503
            ? "ai_busy"
            : "api_error");

        const errorMessage =
          data?.message ??
          detail?.message ??
          (typeof detail ===
          "string"
            ? detail
            : `Backend returned HTTP ${response.status}.`);

        throw new Error(
          JSON.stringify({
            type: errorType,
            message:
              errorMessage,
            status:
              response.status,
          })
        );
      }

      return data;
    } catch (error) {
      if (
        error instanceof
          DOMException &&
        error.name ===
          "AbortError"
      ) {
        throw new Error(
          JSON.stringify({
            type: "timeout",
            message:
              "IGNYX is taking longer than expected. Please try again.",
          })
        );
      }

      if (
        error instanceof
        TypeError
      ) {
        throw new Error(
          JSON.stringify({
            type:
              "backend_offline",
            message:
              "IGNYX could not connect to the AI backend.",
          })
        );
      }

      throw error;
    } finally {
      window.clearTimeout(
        timeoutId
      );
    }
  }

  /* =======================================================
     SEND MESSAGE
  ======================================================= */

  const sendMessage = async () => {
    const text = input.trim();

    if (!text || loading) {
      return;
    }

    let conversationId =
      activeConversationId;

    if (conversationId === null) {
      conversationId =
        createConversation();
    }

    const localConversationId =
      conversationId;

    const userMessage: Message = {
      id: generateId(),
      role: "user",
      content: text,
      createdAt: getTime(),
    };

    setInput("");

    updateConversation(
      localConversationId,
      (conversation) => ({
        ...conversation,
        title:
          conversation.messages
              .length === 0
            ? text.slice(0, 42)
            : conversation.title,
        updatedAt: "Just now",
        messages: [
          ...conversation.messages,
          userMessage,
        ],
      })
    );

    requestAnimationFrame(() => {
      inputRef.current?.focus();
    });

    setLoading(true);

    try {
      const data =
        await askBackend(
          text,
          localConversationId
        );

      const backendConversationId =
        Number(
          data?.conversation_id
        );

      const finalConversationId =
        Number.isFinite(
          backendConversationId
        )
          ? backendConversationId
          : localConversationId;

      const answer =
        normalizeText(
          data?.response ??
            data?.answer ??
            data?.message ??
            data?.content ??
            data?.text ??
            data
        ) ||
        "IGNYX did not return a response.";

      const sources =
        normalizeSources(
          data?.sources ??
            data?.references ??
            data?.citations ??
            data?.links
        );

      const assistantMessage:
        Message = {
        id: generateId(),
        role: "assistant",
        content: answer,
        createdAt: getTime(),
        sources,
      };

      setConversations(
        (previous) => {
          const sourceConversation =
            previous.find(
              (conversation) =>
                conversation.id ===
                localConversationId
            );

          if (!sourceConversation) {
            return previous;
          }

          const reconciled:
            Conversation = {
            ...sourceConversation,
            id: finalConversationId,
            updatedAt: "Just now",
            messages: [
              ...sourceConversation.messages,
              assistantMessage,
            ],
          };

          const remaining =
            previous.filter(
              (conversation) =>
                conversation.id !==
                  localConversationId &&
                conversation.id !==
                  finalConversationId
            );

          return [
            reconciled,
            ...remaining,
          ];
        }
      );

      setActiveConversationId(
        finalConversationId
      );
    } catch (error) {
      let errorType =
        "api_error";
      let errorMessageText =
        "IGNYX could not complete the request.";

      if (
        error instanceof
        Error
      ) {
        try {
          const parsed =
            JSON.parse(
              error.message
            );

          errorType =
            parsed?.type ??
            errorType;
          errorMessageText =
            parsed?.message ??
            errorMessageText;
        } catch {
          errorMessageText =
            error.message;
        }
      }

      let content = "";

      if (
        errorType ===
        "backend_offline"
      ) {
        content = `## Connection Error

IGNYX could not connect to the AI backend.

**Backend URL:** \`${API_BASE}\`

Make sure your FastAPI server is running.

### Start backend

\`\`\`powershell
python server.py
\`\`\``;
      } else if (
        errorType ===
        "ai_quota_exceeded"
      ) {
        content = `## Gemini AI Quota Exhausted

${errorMessageText}

IGNYX is still connected to the backend, but the configured Gemini free-tier quota has been exhausted. Please wait for the quota to reset before trying again.

**Available without Gemini:** Calculator, conversation history, memory management, and other backend features that do not require a new Gemini generation.`;
      } else if (
        errorType ===
        "ai_busy"
      ) {
        content = `## IGNYX AI Is Busy

${errorMessageText}

Please try again in a moment.`;
      } else if (
        errorType ===
        "web_search_error"
      ) {
        content = `## Web Search Unavailable

${errorMessageText}

IGNYX can continue using its AI knowledge without web search.`;
      } else if (
        errorType ===
        "timeout"
      ) {
        content = `## Request Taking Longer

${errorMessageText}

You can try sending the message again.`;
      } else {
        content = `## Request Error

${errorMessageText}`;
      }

      const errorMessage:
        Message = {
        id: generateId(),
        role: "assistant",
        createdAt: getTime(),
        content,
      };

      updateConversation(
        localConversationId,
        (conversation) => ({
          ...conversation,
          messages: [
            ...conversation.messages,
            errorMessage,
          ],
        })
      );

      console.error(
        "IGNYX request error:",
        error
      );
    } finally {
      if (
        mountedRef.current
      ) {
        setLoading(false);
      }
    }
  };

  /* =======================================================
     KEYBOARD
  ======================================================= */

  const handleKeyDown = (
    event: React.KeyboardEvent<HTMLTextAreaElement>
  ) => {
    if (
      event.key === "Enter" &&
      !event.shiftKey
    ) {
      event.preventDefault();

      sendMessage();
    }
  };

  /* =======================================================
     COPY
  ======================================================= */

  const copyMessage = async (
    message: Message
  ) => {
    try {
      await navigator.clipboard.writeText(
        message.content
      );

      setCopiedId(message.id);

      setTimeout(() => {
        setCopiedId(null);
      }, 1800);
    } catch (error) {
      console.warn(
        "Copy failed:",
        error
      );
    }
  };

  /* =======================================================
     MEMORY UI
  ======================================================= */

  const normalizeMemory = (item: any): Memory | null => {
    const id = Number(item?.id);
    const key = normalizeText(item?.key);
    const value = normalizeText(item?.value);

    if (!Number.isFinite(id) || !key) return null;

    return {
      id,
      user_key: normalizeText(item?.user_key) || undefined,
      category: normalizeText(item?.category) || "general",
      key,
      value,
      importance: Math.max(0, Math.min(1, Number(item?.importance ?? 0.5) || 0.5)),
      created_at: item?.created_at,
      updated_at: item?.updated_at,
    };
  };

  const loadMemories = async () => {
    setMemoryLoading(true);
    setMemoryError("");

    try {
      const response = await fetch(`${API_BASE}/memory`, {
        method: "GET",
        headers: { Accept: "application/json" },
        cache: "no-store",
      });

      let data: any = null;
      try {
        data = await response.json();
      } catch {
        data = null;
      }

      if (!response.ok) {
        const detail = data?.detail;
        const message =
          data?.message ??
          (typeof detail === "string" ? detail : detail?.message) ??
          `Backend returned HTTP ${response.status}.`;
        throw new Error(message);
      }

      const rawItems = Array.isArray(data)
        ? data
        : Array.isArray(data?.memories)
          ? data.memories
          : Array.isArray(data?.items)
            ? data.items
            : [];

      const normalized = rawItems
        .map(normalizeMemory)
        .filter((item): item is Memory => item !== null);

      setMemories(normalized);
    } catch (error) {
      console.error("Could not load memories:", error);
      setMemoryError(
        error instanceof Error
          ? error.message
          : "Could not load memories from the backend."
      );
    } finally {
      setMemoryLoading(false);
    }
  };

  const openMemoryPanel = () => {
    setMemoryOpen(true);
    setEditingMemoryId(null);
    void loadMemories();
  };

  const closeMemoryPanel = () => {
    setMemoryOpen(false);
    setEditingMemoryId(null);
    setMemorySearch("");
    setMemoryError("");
  };

  const startMemoryEdit = (memory: Memory) => {
    setEditingMemoryId(memory.id);
    setMemoryDraft({
      value: memory.value,
      category: memory.category,
      importance: String(memory.importance),
    });
  };

  const cancelMemoryEdit = () => {
    setEditingMemoryId(null);
    setMemoryDraft({ value: "", category: "general", importance: "0.5" });
  };

  const saveMemoryEdit = async (memoryId: number) => {
    const value = memoryDraft.value.trim();
    const category = memoryDraft.category.trim() || "general";
    const importanceNumber = Math.max(0, Math.min(1, Number(memoryDraft.importance) || 0.5));

    if (!value) {
      setMemoryError("Memory value cannot be empty.");
      return;
    }

    setMemoryLoading(true);
    setMemoryError("");

    try {
      const response = await fetch(`${API_BASE}/memory/${memoryId}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify({
          value,
          category,
          importance: importanceNumber,
          user_key: "default_user",
        }),
      });

      let data: any = null;
      try {
        data = await response.json();
      } catch {
        data = null;
      }

      if (!response.ok) {
        const detail = data?.detail;
        const message =
          data?.message ??
          (typeof detail === "string" ? detail : detail?.message) ??
          `Backend returned HTTP ${response.status}.`;
        throw new Error(message);
      }

      setEditingMemoryId(null);
      await loadMemories();
    } catch (error) {
      console.error("Could not update memory:", error);
      setMemoryError(
        error instanceof Error
          ? error.message
          : "Could not update this memory."
      );
      setMemoryLoading(false);
    }
  };

  const deleteMemory = async (memoryId: number) => {
    const confirmed = window.confirm("Delete this memory from IGNYX?");
    if (!confirmed) return;

    setMemoryLoading(true);
    setMemoryError("");

    try {
      const response = await fetch(`${API_BASE}/memory/${memoryId}`, {
        method: "DELETE",
        headers: { Accept: "application/json" },
      });

      let data: any = null;
      try {
        data = await response.json();
      } catch {
        data = null;
      }

      if (!response.ok) {
        const detail = data?.detail;
        const message =
          data?.message ??
          (typeof detail === "string" ? detail : detail?.message) ??
          `Backend returned HTTP ${response.status}.`;
        throw new Error(message);
      }

      setMemories((previous) => previous.filter((memory) => memory.id !== memoryId));
      if (editingMemoryId === memoryId) cancelMemoryEdit();
    } catch (error) {
      console.error("Could not delete memory:", error);
      setMemoryError(
        error instanceof Error
          ? error.message
          : "Could not delete this memory."
      );
    } finally {
      setMemoryLoading(false);
    }
  };

  const filteredMemories = memories.filter((memory) => {
    const query = memorySearch.trim().toLowerCase();
    if (!query) return true;
    return [memory.key, memory.value, memory.category]
      .join(" ")
      .toLowerCase()
      .includes(query);
  });

  /* =======================================================
     DELETE CONVERSATION
  ======================================================= */

  const deleteConversation = (
    conversationId: number
  ) => {
    setConversations((previous) => {
      const updated = previous.filter(
        (conversation) =>
          conversation.id !== conversationId
      );

      if (
        activeConversationId === conversationId
      ) {
        setActiveConversationId(
          updated.length > 0
            ? updated[0].id
            : null
        );
      }

      return updated;
    });
  };

  /* =======================================================
     RENDER
  ======================================================= */

  return (
    <main className="ignyx-app">
      {memoryOpen && (
        <div
          className="memory-modal-backdrop"
          role="presentation"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) closeMemoryPanel();
          }}
        >
          <section
            className="memory-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="memory-modal-title"
          >
            <div className="memory-modal-header">
              <div>
                <span className="memory-eyebrow">LONG-TERM MEMORY</span>
                <h2 id="memory-modal-title">IGNYX Memory</h2>
                <p>Things IGNYX has learned and saved for future conversations.</p>
              </div>
              <button
                type="button"
                className="memory-close-button"
                onClick={closeMemoryPanel}
                aria-label="Close memory"
              >
                ×
              </button>
            </div>

            <div className="memory-toolbar">
              <input
                type="search"
                value={memorySearch}
                onChange={(event) => setMemorySearch(event.target.value)}
                placeholder="Search memories..."
                aria-label="Search memories"
              />
              <button
                type="button"
                className="memory-refresh-button"
                onClick={() => void loadMemories()}
                disabled={memoryLoading}
              >
                {memoryLoading ? "Loading..." : "↻ Refresh"}
              </button>
            </div>

            {memoryError && (
              <div className="memory-error" role="alert">
                {memoryError}
              </div>
            )}

            <div className="memory-summary">
              <span>{filteredMemories.length} {filteredMemories.length === 1 ? "memory" : "memories"}</span>
              <span>Stored locally in your IGNYX backend</span>
            </div>

            <div className="memory-list">
              {memoryLoading && memories.length === 0 ? (
                <div className="memory-empty">Loading memories...</div>
              ) : filteredMemories.length === 0 ? (
                <div className="memory-empty">
                  {memorySearch.trim() ? "No matching memories found." : "IGNYX has not saved any memories yet."}
                </div>
              ) : (
                filteredMemories.map((memory) => (
                  <article key={memory.id} className="memory-card">
                    <div className="memory-card-top">
                      <div>
                        <span className="memory-category">{memory.category}</span>
                        <h3>{memory.key}</h3>
                      </div>
                      <div className="memory-actions">
                        <button
                          type="button"
                          onClick={() => startMemoryEdit(memory)}
                          disabled={memoryLoading}
                        >
                          Edit
                        </button>
                        <button
                          type="button"
                          className="danger"
                          onClick={() => void deleteMemory(memory.id)}
                          disabled={memoryLoading}
                        >
                          Delete
                        </button>
                      </div>
                    </div>

                    {editingMemoryId === memory.id ? (
                      <div className="memory-edit-form">
                        <label>
                          Category
                          <input
                            value={memoryDraft.category}
                            maxLength={50}
                            onChange={(event) =>
                              setMemoryDraft((previous) => ({
                                ...previous,
                                category: event.target.value,
                              }))
                            }
                          />
                        </label>
                        <label>
                          Value
                          <textarea
                            value={memoryDraft.value}
                            maxLength={1000}
                            rows={4}
                            onChange={(event) =>
                              setMemoryDraft((previous) => ({
                                ...previous,
                                value: event.target.value,
                              }))
                            }
                          />
                        </label>
                        <label>
                          Importance: {Number(memoryDraft.importance || 0.5).toFixed(2)}
                          <input
                            type="range"
                            min="0"
                            max="1"
                            step="0.05"
                            value={memoryDraft.importance}
                            onChange={(event) =>
                              setMemoryDraft((previous) => ({
                                ...previous,
                                importance: event.target.value,
                              }))
                            }
                          />
                        </label>
                        <div className="memory-edit-actions">
                          <button type="button" onClick={cancelMemoryEdit}>Cancel</button>
                          <button
                            type="button"
                            className="primary"
                            onClick={() => void saveMemoryEdit(memory.id)}
                            disabled={memoryLoading}
                          >
                            {memoryLoading ? "Saving..." : "Save"}
                          </button>
                        </div>
                      </div>
                    ) : (
                      <>
                        <p className="memory-value">{memory.value}</p>
                        <div className="memory-meta">
                          <span>Importance {(memory.importance * 100).toFixed(0)}%</span>
                          {memory.updated_at && <span>Updated {formatBackendTime(memory.updated_at)}</span>}
                        </div>
                      </>
                    )}
                  </article>
                ))
              )}
            </div>

            <div className="memory-modal-footer">
              <span>Memory is automatically learned from useful preferences and facts.</span>
              <button type="button" onClick={closeMemoryPanel}>Done</button>
            </div>
          </section>
        </div>
      )}

      <div className="space-background">
        <div className="planet planet-left" />

        <div className="planet planet-right" />

        <div className="purple-cloud cloud-one" />

        <div className="purple-cloud cloud-two" />

        <div className="stars" />
      </div>

      <div
        className={`app-shell ${
          sidebarOpen ? "" : "sidebar-hidden"
        }`}
      >
        {/* =============================================
            SIDEBAR
        ============================================== */}

        <aside className="sidebar">
          <div className="brand-block">
            <div className="brand-flame">
              <FlameIcon size={56} />
            </div>

            <div>
              <h1>IGNYX AI</h1>

              <p>INTELLIGENCE WITHOUT LIMITS</p>
            </div>
          </div>

          <button
            type="button"
            className="new-chat-button"
            onClick={createConversation}
          >
            <span className="new-chat-icon">
              <PlusIcon />
            </span>

            <span>New Chat</span>
          </button>

          <nav className="navigation">
            <button
              type="button"
              className="nav-item active"
            >
              <span>⌂</span>
              Home
            </button>

            <button
              type="button"
              className="nav-item"
            >
              <span>◉</span>
              Explore
            </button>

            <button
              type="button"
              className="nav-item"
            >
              <span>▱</span>
              Library
            </button>

            <button
              type="button"
              className="nav-item"
            >
              <span>⌘</span>
              AI Tools
            </button>
          </nav>

          <div className="recent-section">
            <div className="recent-header">
              <span>RECENT CHATS</span>
            </div>

            <div className="conversation-list">
              {conversations.length === 0 && (
                <div className="empty-history">
                  No conversations yet
                </div>
              )}

              {conversations.map(
                (conversation) => (
                  <div
                    key={conversation.id}
                    className={`conversation-row ${
                      activeConversationId ===
                      conversation.id
                        ? "selected"
                        : ""
                    }`}
                  >
                    <button
                      type="button"
                      className="conversation-select"
                      onClick={() =>
                        setActiveConversationId(
                          conversation.id
                        )
                      }
                      aria-current={
                        activeConversationId ===
                        conversation.id
                          ? "page"
                          : undefined
                      }
                    >
                      <span className="conversation-icon">
                        ◇
                      </span>

                      <span className="conversation-text">
                        <strong>
                          {conversation.title}
                        </strong>

                        <small>
                          {conversation.updatedAt}
                        </small>
                      </span>
                    </button>

                    <button
                      type="button"
                      className="conversation-delete"
                      aria-label="Delete conversation"
                      onClick={() =>
                        deleteConversation(
                          conversation.id
                        )
                      }
                    >
                      ×
                    </button>
                  </div>
                )
              )}
            </div>
          </div>

          <div className="user-card">
            <div className="user-avatar">
              M
            </div>

            <div className="user-info">
              <strong>Mathan M</strong>

              <span>Free Plan</span>
            </div>

            <span className="online-dot" />
          </div>
        </aside>

        {/* =============================================
            MAIN AREA
        ============================================== */}

        <section className="main-area">
          {/* HEADER */}

          <header className="topbar">
            <div className="topbar-left">
              <button
                type="button"
                className="menu-button"
                onClick={() =>
                  setSidebarOpen(
                    (previous) => !previous
                  )
                }
              >
                <MenuIcon />
              </button>

              <div className="mini-brand">
                <div className="mini-flame">
                  <FlameIcon size={27} />
                </div>

                <div>
                  <strong>IGNYX AI</strong>

                  <small>
                    Powered by Gemini 3 Flash
                  </small>
                </div>

                <span className="status-badge">
                  <span />
                  ONLINE
                </span>
              </div>
            </div>

            <div className="topbar-right">
              <div className="ai-capabilities">
                AI · Search · Analyze · Create
              </div>

              <button
                type="button"
                className="settings-button"
                onClick={openMemoryPanel}
                aria-label="Open IGNYX memory"
                title="Memory"
              >
                ⚙
              </button>
            </div>
          </header>

          {/* ===========================================
              CHAT AREA
          ============================================ */}

          <div className="chat-layout">
            <div
              className="chat-scroll"
              aria-live="polite"
              aria-busy={
                loading ||
                loadingConversation
              }
            >
              {!activeConversation ||
              activeConversation.messages.length ===
                0 ? (
                <div className="welcome-screen">
                  <div className="welcome-flame">
                    <FlameIcon size={100} />
                  </div>

                  <h2>
                    Intelligence without limits.
                  </h2>

                  <p>
                    Ask anything. Search the web.
                    Analyze complex information.
                    Create with AI.
                  </p>

                  <div className="suggestion-grid">
                    <button
                      type="button"
                      onClick={() =>
                        setInput(
                          "What is the latest AI news?"
                        )
                      }
                    >
                      <span>◎</span>

                      <strong>
                        Latest AI News
                      </strong>

                      <small>
                        Search current AI
                        developments
                      </small>
                    </button>

                    <button
                      type="button"
                      onClick={() =>
                        setInput(
                          "Analyze the latest technology trends"
                        )
                      }
                    >
                      <span>✦</span>

                      <strong>
                        Analyze
                      </strong>

                      <small>
                        Deep intelligence and
                        insights
                      </small>
                    </button>

                    <button
                      type="button"
                      onClick={() =>
                        setInput(
                          "Help me improve my resume"
                        )
                      }
                    >
                      <span>◇</span>

                      <strong>
                        Create
                      </strong>

                      <small>
                        Generate ideas and
                        content
                      </small>
                    </button>
                  </div>
                </div>
              ) : (
                <div className="messages">
                  {activeConversation.messages.map(
                    (message) => (
                      <div
                        key={message.id}
                        className={`message-row ${
                          message.role === "user"
                            ? "user-row"
                            : "assistant-row"
                        }`}
                      >
                        {message.role ===
                          "assistant" && (
                          <div className="assistant-avatar">
                            <FlameIcon size={31} />
                          </div>
                        )}

                        <div className="message-stack">
                          <div className="message-meta">
                            <strong>
                              {message.role ===
                              "user"
                                ? "You"
                                : "IGNYX AI"}
                            </strong>

                            <span>
                              {message.createdAt}
                            </span>
                          </div>

                          <div
                            className={`message-bubble ${
                              message.role ===
                              "user"
                                ? "user-bubble"
                                : "assistant-bubble"
                            }`}
                          >
                            {message.role ===
                            "assistant" ? (
                              <MarkdownMessage
                                content={
                                  message.content
                                }
                              />
                            ) : (
                              <p className="user-text">
                                {message.content}
                              </p>
                            )}

                            {message.role ===
                              "assistant" && (
                              <div className="message-actions">
                                <button
                                  type="button"
                                  onClick={() =>
                                    copyMessage(
                                      message
                                    )
                                  }
                                >
                                  <span className="copy-icon">
                                    <CopyIcon />
                                  </span>

                                  {copiedId ===
                                  message.id
                                    ? "Copied"
                                    : "Copy"}
                                </button>
                              </div>
                            )}

                            {message.sources &&
                              message.sources.length >
                                0 && (
                                <div className="sources-section">
                                  <div className="sources-title">
                                    Sources
                                  </div>

                                  <div className="source-list">
                                    {message.sources.map(
                                      (
                                        source,
                                        sourceIndex
                                      ) => (
                                        <a
                                          key={`${source.url}-${sourceIndex}`}
                                          href={source.url}
                                          target="_blank"
                                          rel="noopener noreferrer"
                                          className="source-card"
                                        >
                                          <span>
                                            ◉
                                          </span>

                                          <div>
                                            <strong>
                                              {
                                                source.title
                                              }
                                            </strong>

                                            <small>
                                              {
                                                source.url
                                              }
                                            </small>
                                          </div>
                                        </a>
                                      )
                                    )}
                                  </div>
                                </div>
                              )}
                          </div>
                        </div>

                        {message.role ===
                          "user" && (
                          <div className="user-message-avatar">
                            M
                          </div>
                        )}
                      </div>
                    )
                  )}

                  {loading && <ThinkingLoader />}

                  <div ref={chatEndRef} />
                </div>
              )}
            </div>

            {/* ===========================================
                INPUT
            ============================================ */}

            <div className="composer-wrapper">
              <div className="composer">
                <button
                  type="button"
                  className="attach-button"
                  aria-label="Attach file"
                >
                  <PaperClipIcon />
                </button>

                <textarea
                  ref={inputRef}
                  value={input}
                  onChange={(event) => {
                    setInput(
                      event.target.value
                    );

                    const target =
                      event.currentTarget;

                    target.style.height =
                      "auto";

                    target.style.height =
                      `${Math.min(
                        target.scrollHeight,
                        140
                      )}px`;
                  }}
                  onKeyDown={handleKeyDown}
                  placeholder="Ask anything..."
                  rows={1}
                  disabled={loading}
                  aria-label="Message IGNYX AI"
                />

                <div className="composer-actions">
                  <button
                    type="button"
                    className={`web-button ${
                      webSearch ? "enabled" : ""
                    }`}
                    onClick={() =>
                      setWebSearch(
                        (previous) => !previous
                      )
                    }
                  >
                    <span className="web-icon">
                      <GlobeIcon />
                    </span>

                    Web Search
                  </button>

                  <button
                    type="button"
                    className="send-button"
                    disabled={
                      !input.trim() || loading
                    }
                    onClick={sendMessage}
                  >
                    <SendIcon />
                  </button>
                </div>
              </div>

              <div className="composer-footer">
                <div>
                  <span
                    className={
                      webSearch
                        ? "web-status active"
                        : "web-status"
                    }
                  >
                    <GlobeIcon />
                  </span>

                  Web Search{" "}
                  {webSearch ? "ON" : "OFF"}

                  <span className="keyboard-tip">
                    Shift + Enter for new line
                  </span>
                </div>

                <span>
                  IGNYX can make mistakes.
                  Verify important information.
                </span>
              </div>
            </div>
          </div>

          {/* FOOTER */}

          <footer className="app-footer">
            <FlameIcon size={20} />

            <span>IGNYX AI</span>

            <span className="footer-star">✦</span>

            <span>
              INTELLIGENCE WITHOUT LIMITS
            </span>
          </footer>
        </section>
      </div>

      <style jsx>{`
        .memory-modal-backdrop {
          position: fixed;
          inset: 0;
          z-index: 1000;
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 24px;
          background: rgba(8, 4, 20, 0.72);
          backdrop-filter: blur(18px);
          -webkit-backdrop-filter: blur(18px);
        }
        .memory-modal {
          width: min(860px, 100%);
          max-height: min(820px, calc(100vh - 48px));
          display: flex;
          flex-direction: column;
          overflow: hidden;
          border: 1px solid rgba(255,255,255,0.14);
          border-radius: 24px;
          background: linear-gradient(145deg, rgba(29,19,51,0.96), rgba(13,9,27,0.97));
          box-shadow: 0 30px 100px rgba(0,0,0,0.55), 0 0 60px rgba(168,76,255,0.16);
          color: #fff;
        }
        .memory-modal-header {
          display: flex;
          align-items: flex-start;
          justify-content: space-between;
          gap: 20px;
          padding: 28px 30px 18px;
          border-bottom: 1px solid rgba(255,255,255,0.08);
        }
        .memory-eyebrow {
          font-size: 11px;
          letter-spacing: 0.18em;
          color: #bd8bff;
          font-weight: 700;
        }
        .memory-modal-header h2 {
          margin: 7px 0 5px;
          font-size: 26px;
        }
        .memory-modal-header p {
          margin: 0;
          color: rgba(255,255,255,0.62);
          font-size: 13px;
        }
        .memory-close-button {
          width: 38px;
          height: 38px;
          border: 1px solid rgba(255,255,255,0.12);
          border-radius: 12px;
          background: rgba(255,255,255,0.05);
          color: #fff;
          font-size: 24px;
          cursor: pointer;
        }
        .memory-toolbar {
          display: flex;
          gap: 10px;
          padding: 18px 30px 10px;
        }
        .memory-toolbar input {
          flex: 1;
          min-width: 0;
          height: 44px;
          padding: 0 14px;
          border: 1px solid rgba(255,255,255,0.1);
          border-radius: 12px;
          outline: none;
          background: rgba(255,255,255,0.055);
          color: #fff;
        }
        .memory-toolbar input:focus {
          border-color: rgba(196, 118, 255, 0.55);
        }
        .memory-refresh-button, .memory-modal-footer button, .memory-actions button, .memory-edit-actions button {
          border: 1px solid rgba(255,255,255,0.12);
          border-radius: 11px;
          background: rgba(255,255,255,0.055);
          color: rgba(255,255,255,0.88);
          padding: 0 14px;
          min-height: 40px;
          cursor: pointer;
        }
        .memory-refresh-button {
          height: 44px;
          white-space: nowrap;
        }
        .memory-refresh-button:disabled, .memory-actions button:disabled, .memory-edit-actions button:disabled {
          opacity: 0.5;
          cursor: default;
        }
        .memory-summary {
          display: flex;
          justify-content: space-between;
          gap: 12px;
          padding: 0 30px 12px;
          color: rgba(255,255,255,0.48);
          font-size: 12px;
        }
        .memory-error {
          margin: 0 30px 12px;
          padding: 11px 13px;
          border-radius: 12px;
          background: rgba(255, 72, 109, 0.1);
          border: 1px solid rgba(255, 72, 109, 0.22);
          color: #ff9bb1;
          font-size: 13px;
        }
        .memory-list {
          flex: 1;
          min-height: 0;
          overflow-y: auto;
          padding: 0 30px 18px;
        }
        .memory-card {
          padding: 17px;
          margin-bottom: 10px;
          border: 1px solid rgba(255,255,255,0.09);
          border-radius: 16px;
          background: rgba(255,255,255,0.035);
        }
        .memory-card-top {
          display: flex;
          align-items: flex-start;
          justify-content: space-between;
          gap: 16px;
        }
        .memory-category {
          display: inline-flex;
          padding: 4px 8px;
          border-radius: 999px;
          background: rgba(181, 113, 255, 0.13);
          color: #d0a9ff;
          font-size: 10px;
          letter-spacing: 0.08em;
          text-transform: uppercase;
        }
        .memory-card h3 {
          margin: 8px 0 0;
          font-size: 15px;
          word-break: break-word;
        }
        .memory-actions {
          display: flex;
          gap: 7px;
          flex-shrink: 0;
        }
        .memory-actions button {
          min-height: 34px;
          font-size: 12px;
        }
        .memory-actions button.danger {
          color: #ff9aac;
        }
        .memory-value {
          margin: 12px 0 10px;
          color: rgba(255,255,255,0.78);
          line-height: 1.6;
          white-space: pre-wrap;
          word-break: break-word;
        }
        .memory-meta {
          display: flex;
          justify-content: space-between;
          gap: 10px;
          color: rgba(255,255,255,0.42);
          font-size: 11px;
        }
        .memory-empty {
          padding: 64px 20px;
          text-align: center;
          color: rgba(255,255,255,0.45);
        }
        .memory-edit-form {
          display: grid;
          gap: 12px;
          margin-top: 14px;
        }
        .memory-edit-form label {
          display: grid;
          gap: 7px;
          color: rgba(255,255,255,0.58);
          font-size: 11px;
        }
        .memory-edit-form input, .memory-edit-form textarea {
          width: 100%;
          box-sizing: border-box;
          border: 1px solid rgba(255,255,255,0.1);
          border-radius: 10px;
          background: rgba(0,0,0,0.14);
          color: #fff;
          padding: 10px 11px;
          outline: none;
          font: inherit;
        }
        .memory-edit-form input[type=range] {
          padding: 0;
          accent-color: #be7aff;
        }
        .memory-edit-actions {
          display: flex;
          justify-content: flex-end;
          gap: 8px;
        }
        .memory-edit-actions .primary, .memory-modal-footer button {
          background: linear-gradient(135deg, rgba(149, 63, 255, 0.85), rgba(231, 103, 255, 0.72));
          border-color: rgba(229, 168, 255, 0.3);
          color: #fff;
        }
        .memory-modal-footer {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 14px;
          padding: 14px 30px 20px;
          border-top: 1px solid rgba(255,255,255,0.08);
          color: rgba(255,255,255,0.4);
          font-size: 11px;
        }
        .memory-modal-footer button {
          min-width: 76px;
        }
        @media (max-width: 680px) {
          .memory-modal-backdrop { padding: 10px; }
          .memory-modal { max-height: calc(100vh - 20px); border-radius: 18px; }
          .memory-modal-header, .memory-toolbar, .memory-list, .memory-modal-footer { padding-left: 16px; padding-right: 16px; }
          .memory-summary { padding-left: 16px; padding-right: 16px; }
          .memory-error { margin-left: 16px; margin-right: 16px; }
          .memory-toolbar { flex-direction: column; }
          .memory-refresh-button { width: 100%; }
          .memory-card-top { flex-direction: column; }
          .memory-actions { width: 100%; }
          .memory-actions button { flex: 1; }
          .memory-meta, .memory-modal-footer { align-items: flex-start; flex-direction: column; }
        }
      `}</style>
    </main>
  );
}