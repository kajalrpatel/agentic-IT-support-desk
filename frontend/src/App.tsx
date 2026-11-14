import { useEffect, useRef, useState } from "react";
import {
  ArrowUp,
  BookOpen,
  CheckCheck,
  ChevronRight,
  CircleHelp,
  Headphones,
  LifeBuoy,
  MessageSquare,
  Plus,
  ShieldCheck,
  Ticket as TicketIcon,
} from "lucide-react";
import { api, authenticate, sendMessage } from "./api/client";
import type { Conversation, Draft, Message, Reply } from "./api/client";
import { TicketPreview } from "./features/tickets/TicketPreview";

const suggestions = [
  {
    icon: BookOpen,
    title: "Find a policy",
    text: "What is the policy for compensatory time off?",
    hint: "Leave, benefits & company guidelines",
  },
  {
    icon: LifeBuoy,
    title: "Get IT help",
    text: "How do I reset my password?",
    hint: "Accounts, devices & getting connected",
  },
  {
    icon: TicketIcon,
    title: "Check a ticket",
    text: "What is the status of my tickets?",
    hint: "Follow up on an existing request",
  },
];

export default function App() {
  const [email, setEmail] = useState("");
  const [ready, setReady] = useState(false);
  const [error, setError] = useState("");
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [active, setActive] = useState<Conversation | null>(null);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState("");
  const bottom = useRef<HTMLDivElement>(null);
  const initialized = useRef(false);
  async function refreshList() {
    setConversations(await api<Conversation[]>("/conversations"));
  }
  async function open(id: string) {
    setError("");
    try {
      setActive(await api<Conversation>(`/conversations/${id}`));
      localStorage.setItem("smartdesk-conversation", id);
    } catch (e) {
      setError((e as Error).message);
    }
  }
  useEffect(() => {
    if (initialized.current) return;
    initialized.current = true;
    (async () => {
      try {
        setEmail(await authenticate());
        await refreshList();
        const previous = localStorage.getItem("smartdesk-conversation");
        if (previous) await open(previous);
        setReady(true);
      } catch (e) {
        setError((e as Error).message);
      }
    })();
  }, []);
  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth" });
  }, [active, progress]);
  async function send(text: string) {
    if (!text.trim() || busy || !ready) return;
    setBusy(true);
    setError("");
    setInput("");
    try {
      let conversation = active;
      if (!conversation) {
        conversation = await api<Conversation>("/conversations", {});
        localStorage.setItem("smartdesk-conversation", conversation.id);
      }
      const pending: Message = {
        id: Date.now(),
        role: "user",
        content: text,
        response: null,
      };
      setActive({
        ...conversation,
        messages: [...conversation.messages, pending],
      });
      await sendMessage(conversation.id, text, setProgress);
      await open(conversation.id);
      await refreshList();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
      setProgress("");
    }
  }
  async function approval(
    action: "confirm" | "edit" | "cancel",
    draft?: Draft,
  ) {
    if (!active?.response || busy) return;
    setBusy(true);
    setError("");
    try {
      await api<Reply>(`/conversations/${active.id}/approval`, {
        action,
        draft,
        version: active.response.draft_version,
        request_id: crypto.randomUUID(),
      });
      await open(active.id);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a href="/" className="brand">
          <span className="brand-mark">
            <Headphones size={23} />
          </span>
          <span>
            SmartDesk<span className="brand-sub">EMPLOYEE SUPPORT</span>
          </span>
        </a>
        <button
          className="new-chat"
          disabled={busy}
          onClick={() => {
            setActive(null);
            setError("");
            localStorage.removeItem("smartdesk-conversation");
          }}
        >
          <Plus size={17} />
          New conversation
        </button>
        <div className="nav-label">YOUR WORKSPACE</div>
        <div className="nav-current">
          <MessageSquare size={17} />
          Conversations<span>{conversations.length}</span>
        </div>
        <div className="history">
          {conversations.map((c) => (
            <button
              disabled={busy}
              className={
                active?.id === c.id ? "history-item selected" : "history-item"
              }
              key={c.id}
              onClick={() => open(c.id)}
            >
              <MessageSquare size={14} />
              <span>{c.title}</span>
            </button>
          ))}
          {!conversations.length && (
            <p className="empty-history">
              Your conversations will appear here.
            </p>
          )}
        </div>
        <div className="sidebar-note">
          <ShieldCheck size={21} />
          <p>
            Support you can trust<span>Answers backed by company sources.</span>
          </p>
        </div>
        <div className="profile">
          <div className="avatar">{email ? email[0].toUpperCase() : "U"}</div>
          <div>
            <strong>Employee workspace</strong>
            <span>{email || "Connecting…"}</span>
          </div>
        </div>
      </aside>
      <main>
        <header className="topbar">
          <div>
            <span className="workspace-label">NOVATECH</span>
            <ChevronRight size={14} />
            <span>Support desk</span>
          </div>
          <span className="private-label">
            <ShieldCheck size={14} />
            Your employee workspace
          </span>
        </header>
        <nav className="mobile-navigation" aria-label="Conversation navigation">
          <button
            disabled={busy}
            onClick={() => {
              setActive(null);
              setError("");
              localStorage.removeItem("smartdesk-conversation");
            }}
          >
            <Plus size={16} />
            New conversation
          </button>
          <select
            aria-label="Previous conversations"
            disabled={busy}
            value={active?.id || ""}
            onChange={(e) => {
              if (e.target.value) open(e.target.value);
            }}
          >
            <option value="">Previous conversations</option>
            {conversations.map((c) => (
              <option key={c.id} value={c.id}>
                {c.title}
              </option>
            ))}
          </select>
        </nav>
        <div className="chat-area">
          {!active?.messages.length ? (
            <section className="welcome">
              <div className="welcome-icon">
                <Headphones size={31} />
                <span />
              </div>
              <span className="eyebrow">A LITTLE HELP GOES A LONG WAY</span>
              <h1>
                One desk.
                <br />
                Less getting stuck.
              </h1>
              <p>
                From a forgotten password to your next day off,
                <br className="desktop-break" /> find an answer or get the right
                support.
              </p>
              <div className="suggestions">
                {suggestions.map(({ icon: Icon, title, text, hint }) => (
                  <button
                    key={title}
                    disabled={!ready || busy}
                    onClick={() => send(text)}
                  >
                    <Icon size={22} />
                    <strong>
                      {title}
                      <ChevronRight size={16} />
                    </strong>
                    <span>{hint}</span>
                  </button>
                ))}
              </div>
              <div className="welcome-foot">
                <CheckCheck size={15} />
                Company sources. Clear answers. A human when you need one.
              </div>
            </section>
          ) : (
            <section className="messages" aria-label="Conversation">
              {active.messages.map((m) => (
                <article key={m.id} className={`message ${m.role}`}>
                  <div className="message-avatar">
                    {m.role === "assistant" ? (
                      <Headphones size={18} />
                    ) : (
                      (email[0] || "Y").toUpperCase()
                    )}
                  </div>
                  <div className="message-body">
                    <div className="message-label">
                      {m.role === "assistant" ? "SmartDesk" : "You"}
                      {m.role === "assistant" && <span>SUPPORT ASSISTANT</span>}
                    </div>
                    <p>{m.content}</p>
                    {m.response?.citations.length ? (
                      <div className="sources">
                        {m.response.citations.map((c, i) => (
                          <details key={c.id}>
                            <summary>
                              <BookOpen size={13} />[{i + 1}] {c.title}
                            </summary>
                            <p>{c.excerpt}</p>
                            <small>Source: {c.source}</small>
                          </details>
                        ))}
                      </div>
                    ) : null}
                    {m.response?.tickets.map((t) => (
                      <div className="ticket-card" key={t.id}>
                        <TicketIcon size={18} />
                        <div>
                          <button
                            className="ticket-select"
                            disabled={busy}
                            onClick={() =>
                              send(`Show details for ticket ${t.id}`)
                            }
                          >
                            {t.id} · {t.summary}
                          </button>
                          <span>{t.status}</span>
                          {t.comments?.map((c, i) => (
                            <p key={i}>{c}</p>
                          ))}
                        </div>
                        {/^https?:\/\//i.test(t.url) && (
                          <a href={t.url} target="_blank" rel="noreferrer">
                            Open ↗
                          </a>
                        )}
                      </div>
                    ))}
                  </div>
                </article>
              ))}
              {active.response?.pending_approval && (
                <TicketPreview
                  reply={active.response}
                  busy={busy}
                  onAction={approval}
                />
              )}
              <div ref={bottom} />
            </section>
          )}
          {busy && (
            <div className="progress" role="status">
              <span className="pulse" />
              {progress || "Working on your request…"}
            </div>
          )}
          {error && (
            <div className="error" role="alert">
              <CircleHelp size={18} />
              <span>{error}</span>
              {active && (
                <button disabled={busy} onClick={() => open(active.id)}>
                  Reload conversation
                </button>
              )}
            </div>
          )}
        </div>
        <footer className="composer-wrap">
          <form
            className="composer"
            onSubmit={(e) => {
              e.preventDefault();
              send(input);
            }}
          >
            <textarea
              aria-label="Message"
              placeholder="Ask about IT, HR, or an existing ticket…"
              rows={1}
              maxLength={4000}
              value={input}
              disabled={!ready || busy}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  send(input);
                }
              }}
            />
            <button
              className="send"
              aria-label="Send message"
              disabled={!input.trim() || busy || !ready}
            >
              <ArrowUp size={20} />
            </button>
          </form>
          <p>
            SmartDesk uses company guidance. Always review a ticket before it’s
            sent.
          </p>
        </footer>
      </main>
    </div>
  );
}
