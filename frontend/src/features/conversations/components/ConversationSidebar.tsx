import { Headphones, MessageSquare, Plus } from "lucide-react";
import type { NavigationProps } from "../models/navigationModels";
export function ConversationSidebar({
  conversations,
  active,
  busy,
  onNew,
  onOpen,
  email,
}: NavigationProps & { email: string }) {
  return (
    <aside className="sidebar">
      <a href="/" className="brand">
        <span className="brand-mark">
          <Headphones size={23} />
        </span>
        <span>
          SmartDesk<span className="brand-sub">EMPLOYEE SUPPORT</span>
        </span>
      </a>
      <button className="new-chat" disabled={busy} onClick={onNew}>
        <Plus size={17} />
        New conversation
      </button>
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
            onClick={() => onOpen(c.id)}
          >
            <MessageSquare size={14} />
            <span>{c.title}</span>
          </button>
        ))}
        {!conversations.length && (
          <p className="empty-history">Your conversations will appear here.</p>
        )}
      </div>
      <div className="profile">
        <div className="avatar">{email ? email[0].toUpperCase() : "U"}</div>
        <div>
          <strong>Employee account</strong>
          <span>{email.split("@")[0] || "Connecting…"}</span>
        </div>
      </div>
    </aside>
  );
}
