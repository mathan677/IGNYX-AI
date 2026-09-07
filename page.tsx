"use client";

import { useEffect, useRef, useState } from "react";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";

import {
  Menu,
  Plus,
  Send,
  Paperclip,
  Zap,
  Copy,
  Check,
  Trash2,
  Pencil,
  Search,
  Bot,
  User,
  RefreshCw,
  Sparkles,
  Brain,
  Code2,
  Database,
  X,
  Loader2,
  ChevronDown,
} from "lucide-react";

type Message = {
  role: "user" | "assistant";
  content: string;
  id?: string;
};

type Conversation = {
  id: string;
  title: string;
  messages?: Message[];
};

const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

const QUICK_PROMPTS = [
  {
    icon: Brain,
    title: "Explain AI",
    prompt: "Explain Artificial Intelligence in a simple and detailed way.",
  },
  {
    icon: Code2,
    title: "Write Python",
    prompt: "Write a Python example and explain the code step by step.",
  },
  {
    icon: Database,
    title: "Explain RAG",
    prompt:
      "Explain Retrieval-Augmented Generation (RAG) with architecture, table, workflow and Python example.",
  },
  {
    icon: Bot,
    title: "AI Agents",
    prompt:
      "Explain AI Agents, tools, memory, planning and multi-agent systems.",
  },
];

function CodeBlock({
  language,
  children,
}: {
  language?: string;
  children: string;
}) {
  const [copied, setCopied] = useState(false);

  const copyCode = async () => {
    await navigator.clipboard.writeText(children);

    setCopied(true);

    setTimeout(() => {
      setCopied(false);
    }, 2000);
  };

  return (
    <div className="code-block">
      <div className="code-header">
        <div className="code-language">
          {language || "CODE"}
        </div>

        <button
          className="copy-button"
          onClick={copyCode}
        >
          {copied ? (
            <>
              <Check size={15} />
              Copied
            </>
          ) : (
            <>
              <Copy size={15} />
              Copy
            </>
          )}
        </button>
      </div>

      <pre>
        <code>{children}</code>
      </pre>
    </div>
  );
}

export default function Home() {
  const [sidebarOpen, setSidebarOpen] =
    useState(true);

  const [backendOnline, setBackendOnline] =
    useState(false);

  const [message, setMessage] =
    useState("");

  const [messages, setMessages] =
    useState<Message[]>([]);

  const [loading, setLoading] =
    useState(false);

  const [conversations, setConversations] =
    useState<Conversation[]>([]);

  const [activeConversation, setActiveConversation] =
    useState<string | null>(null);

  const [search, setSearch] =
    useState("");

  const [renameId, setRenameId] =
    useState<string | null>(null);

  const [renameValue, setRenameValue] =
    useState("");

  const messagesEndRef =
    useRef<HTMLDivElement>(null);

  /*
  ========================================
  SCROLL TO BOTTOM
  ========================================
  */

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({
      behavior: "smooth",
    });
  }, [messages, loading]);

  /*
  ========================================
  CHECK BACKEND
  ========================================
  */

  const checkBackend = async () => {
    try {
      const response = await fetch(
        `${API_URL}/health`
      );

      setBackendOnline(response.ok);
    } catch {
      setBackendOnline(false);
    }
  };

  /*
  ========================================
  LOAD CONVERSATIONS
  ========================================
  */

  const loadConversations = async () => {
    try {
      const response = await fetch(
        `${API_URL}/conversations`
      );

      if (!response.ok) return;

      const data = await response.json();

      if (Array.isArray(data)) {
        setConversations(data);
      } else if (Array.isArray(data.conversations)) {
        setConversations(data.conversations);
      }
    } catch (error) {
      console.log(
        "Conversation loading error:",
        error
      );
    }
  };

  /*
  ========================================
  INITIAL LOAD
  ========================================
  */

  useEffect(() => {
    checkBackend();

    loadConversations();

    const interval = setInterval(() => {
      checkBackend();
    }, 10000);

    return () => {
      clearInterval(interval);
    };
  }, []);

  /*
  ========================================
  CREATE NEW CHAT
  ========================================
  */

  const createNewChat = () => {
    setMessages([]);

    setActiveConversation(null);

    setMessage("");
  };

  /*
  ========================================
  SEND MESSAGE
  ========================================
  */

  const sendMessage = async (
    prompt?: string
  ) => {
    const finalMessage =
      prompt || message.trim();

    if (!finalMessage || loading) return;

    const userMessage: Message = {
      role: "user",
      content: finalMessage,
    };

    setMessages((prev) => [
      ...prev,
      userMessage,
    ]);

    setMessage("");

    setLoading(true);

    try {
      const response = await fetch(
        `${API_URL}/chat`,
        {
          method: "POST",

          headers: {
            "Content-Type":
              "application/json",
          },

          body: JSON.stringify({
            message: finalMessage,

            conversation_id:
              activeConversation,
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail ||
            data.error ||
            "Unable to generate response."
        );
      }

      const aiResponse =
        data.response ||
        data.message ||
        data.content ||
        data.answer ||
        "Unable to generate a response.";

      const assistantMessage: Message = {
        role: "assistant",
        content: aiResponse,
      };

      setMessages((prev) => [
        ...prev,
        assistantMessage,
      ]);

      if (
        data.conversation_id &&
        !activeConversation
      ) {
        setActiveConversation(
          data.conversation_id
        );
      }

      await loadConversations();
    } catch (error) {
      const errorMessage =
        error instanceof Error
          ? error.message
          : "Something went wrong.";

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `⚠️ **Error**\n\n${errorMessage}`,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  /*
  ========================================
  HANDLE ENTER
  ========================================
  */

  const handleKeyDown = (
    e: React.KeyboardEvent<HTMLTextAreaElement>
  ) => {
    if (
      e.key === "Enter" &&
      !e.shiftKey
    ) {
      e.preventDefault();

      sendMessage();
    }
  };

  /*
  ========================================
  OPEN CONVERSATION
  ========================================
  */

  const openConversation = async (
    conversation: Conversation
  ) => {
    setActiveConversation(
      conversation.id
    );

    if (conversation.messages) {
      setMessages(
        conversation.messages
      );
    }

    if (window.innerWidth < 900) {
      setSidebarOpen(false);
    }
  };

  /*
  ========================================
  DELETE CONVERSATION
  ========================================
  */

  const deleteConversation = async (
    id: string
  ) => {
    try {
      await fetch(
        `${API_URL}/conversations/${id}`,
        {
          method: "DELETE",
        }
      );

      if (activeConversation === id) {
        createNewChat();
      }

      loadConversations();
    } catch (error) {
      console.log(error);
    }
  };

  /*
  ========================================
  RENAME CONVERSATION
  ========================================
  */

  const saveRename = async (
    id: string
  ) => {
    if (!renameValue.trim()) {
      setRenameId(null);
      return;
    }

    try {
      await fetch(
        `${API_URL}/conversations/${id}`,
        {
          method: "PUT",

          headers: {
            "Content-Type":
              "application/json",
          },

          body: JSON.stringify({
            title: renameValue,
          }),
        }
      );

      setRenameId(null);

      setRenameValue("");

      loadConversations();
    } catch (error) {
      console.log(error);
    }
  };

  /*
  ========================================
  FILTER CONVERSATIONS
  ========================================
  */

  const filteredConversations =
    conversations.filter(
      (conversation) =>
        conversation.title
          ?.toLowerCase()
          .includes(
            search.toLowerCase()
          )
    );

  return (
    <main className="app">
      {/* ================================= */}
      {/* SIDEBAR */}
      {/* ================================= */}

      <aside
        className={`sidebar ${
          sidebarOpen ? "open" : "closed"
        }`}
      >
        {/* LOGO */}

        <div className="sidebar-logo">
          <div className="logo-icon">
            I
          </div>

          <div>
            <h1>IGNYX</h1>

            <span>
              Intelligent AI Assistant
            </span>
          </div>
        </div>

        {/* NEW CHAT */}

        <button
          className="new-chat-button"
          onClick={createNewChat}
        >
          <Plus size={21} />

          <span>New Chat</span>
        </button>

        {/* SEARCH */}

        <div className="search-box">
          <Search size={17} />

          <input
            placeholder="Search chats..."
            value={search}
            onChange={(e) =>
              setSearch(
                e.target.value
              )
            }
          />
        </div>

        {/* CONVERSATIONS */}

        <div className="conversation-header">
          <span>CONVERSATIONS</span>

          <button
            onClick={loadConversations}
          >
            <RefreshCw size={16} />
          </button>
        </div>

        <div className="conversation-list">
          {filteredConversations.map(
            (conversation) => (
              <div
                key={conversation.id}
                className={`conversation-item ${
                  activeConversation ===
                  conversation.id
                    ? "active"
                    : ""
                }`}
              >
                {renameId ===
                conversation.id ? (
                  <input
                    autoFocus
                    value={renameValue}
                    className="rename-input"
                    onChange={(e) =>
                      setRenameValue(
                        e.target.value
                      )
                    }
                    onKeyDown={(e) => {
                      if (
                        e.key === "Enter"
                      ) {
                        saveRename(
                          conversation.id
                        );
                      }
                    }}
                  />
                ) : (
                  <button
                    className="conversation-title"
                    onClick={() =>
                      openConversation(
                        conversation
                      )
                    }
                  >
                    <Sparkles
                      size={16}
                    />

                    <span>
                      {conversation.title ||
                        "New Conversation"}
                    </span>
                  </button>
                )}

                <div className="conversation-actions">
                  <button
                    onClick={() => {
                      setRenameId(
                        conversation.id
                      );

                      setRenameValue(
                        conversation.title
                      );
                    }}
                  >
                    <Pencil size={14} />
                  </button>

                  <button
                    onClick={() =>
                      deleteConversation(
                        conversation.id
                      )
                    }
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            )
          )}

          {filteredConversations.length ===
            0 && (
            <div className="empty-chats">
              No conversations yet
            </div>
          )}
        </div>

        {/* SIDEBAR FOOTER */}

        <div className="sidebar-footer">
          <div className="footer-avatar">
            N
          </div>

          <span>Powered by Gemini</span>
        </div>
      </aside>

      {/* ================================= */}
      {/* MAIN AREA */}
      {/* ================================= */}

      <section className="main-area">
        {/* HEADER */}

        <header className="top-header">
          <div className="header-left">
            <button
              className="menu-button"
              onClick={() =>
                setSidebarOpen(
                  !sidebarOpen
                )
              }
            >
              <Menu size={23} />
            </button>

            <div>
              <h2>IGNYX AI</h2>

              <div className="status">
                <span
                  className={
                    backendOnline
                      ? "status-dot online"
                      : "status-dot offline"
                  }
                />

                <span>
                  {backendOnline
                    ? "Online"
                    : "Backend Offline"}
                </span>
              </div>
            </div>
          </div>

          <button
            className="backend-button"
            onClick={checkBackend}
          >
            <span
              className={
                backendOnline
                  ? "backend-dot online"
                  : "backend-dot offline"
              }
            />

            Check Backend
          </button>
        </header>

        {/* CHAT */}

        <div className="chat-container">
          {messages.length === 0 ? (
            <div className="welcome-screen">
              <div className="welcome-icon">
                <Sparkles size={32} />
              </div>

              <h1>
                Hello, I&apos;m
                <span> IGNYX</span>
              </h1>

              <p>
                Your intelligent AI assistant
                for Artificial Intelligence,
                Data Science, Programming,
                Generative AI, RAG and
                AI Agents.
              </p>

              <div className="quick-prompts">
                {QUICK_PROMPTS.map(
                  (item) => {
                    const Icon =
                      item.icon;

                    return (
                      <button
                        key={item.title}
                        className="quick-card"
                        onClick={() =>
                          sendMessage(
                            item.prompt
                          )
                        }
                      >
                        <div className="quick-icon">
                          <Icon size={22} />
                        </div>

                        <span>
                          {item.title}
                        </span>

                        <small>
                          Ask IGNYX
                        </small>
                      </button>
                    );
                  }
                )}
              </div>
            </div>
          ) : (
            <div className="messages">
              {messages.map(
                (msg, index) => (
                  <div
                    key={index}
                    className={`message-row ${
                      msg.role
                    }`}
                  >
                    {msg.role ===
                      "assistant" && (
                      <div className="assistant-avatar">
                        <Bot size={18} />
                      </div>
                    )}

                    <div
                      className={`message-bubble ${
                        msg.role
                      }`}
                    >
                      {msg.role ===
                      "assistant" ? (
                        <ReactMarkdown
                          remarkPlugins={[
                            remarkGfm,
                          ]}
                          rehypePlugins={[
                            rehypeHighlight,
                          ]}
                          components={{
                            code({
                              className,
                              children,
                              ...props
                            }) {
                              const match =
                                /language-(\w+)/.exec(
                                  className ||
                                    ""
                                );

                              const code =
                                String(
                                  children
                                ).replace(
                                  /\n$/,
                                  ""
                                );

                              if (
                                className
                              ) {
                                return (
                                  <CodeBlock
                                    language={
                                      match?.[1]
                                    }
                                  >
                                    {code}
                                  </CodeBlock>
                                );
                              }

                              return (
                                <code
                                  className="inline-code"
                                  {...props}
                                >
                                  {children}
                                </code>
                              );
                            },

                            table({
                              children,
                            }) {
                              return (
                                <div className="table-wrapper">
                                  <table>
                                    {children}
                                  </table>
                                </div>
                              );
                            },
                          }}
                        >
                          {msg.content}
                        </ReactMarkdown>
                      ) : (
                        <p>
                          {msg.content}
                        </p>
                      )}
                    </div>

                    {msg.role ===
                      "user" && (
                      <div className="user-avatar">
                        <User size={17} />
                      </div>
                    )}
                  </div>
                )
              )}

              {loading && (
                <div className="message-row assistant">
                  <div className="assistant-avatar">
                    <Bot size={18} />
                  </div>

                  <div className="thinking">
                    <span />

                    <span />

                    <span />

                    <p>
                      IGNYX is thinking...
                    </p>
                  </div>
                </div>
              )}

              <div
                ref={messagesEndRef}
              />
            </div>
          )}
        </div>

        {/* INPUT */}

        <div className="input-area">
          <div className="input-box">
            <textarea
              value={message}
              placeholder="Ask anything..."
              onChange={(e) =>
                setMessage(
                  e.target.value
                )
              }
              onKeyDown={handleKeyDown}
              disabled={loading}
              rows={1}
            />

            <div className="input-actions">
              <button
                className="attachment-button"
              >
                <Paperclip size={20} />
              </button>

              <button
                className="magic-button"
              >
                <Zap size={19} />
              </button>

              <button
                className="send-button"
                onClick={() =>
                  sendMessage()
                }
                disabled={
                  !message.trim() ||
                  loading
                }
              >
                {loading ? (
                  <Loader2
                    size={19}
                    className="spin"
                  />
                ) : (
                  <>
                    Send

                    <Send size={17} />
                  </>
                )}
              </button>
            </div>
          </div>

          <div className="input-footer">
            Press Enter to send
            <span>•</span>
            Shift + Enter for new line
            <span>•</span>
            IGNYX can make mistakes
          </div>
        </div>
      </section>
    </main>
  );
}