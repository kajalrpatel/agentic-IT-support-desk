import { Plus } from "lucide-react";
import type { NavigationProps } from "../models/navigationModels";
export function ConversationNavigation({
  conversations,
  active,
  busy,
  onNew,
  onOpen,
}: NavigationProps) {
  return (
    <nav className="mobile-navigation" aria-label="Conversation navigation">
      <button disabled={busy} onClick={onNew}>
        <Plus size={16} />
        New conversation
      </button>
      <select
        aria-label="Previous conversations"
        disabled={busy}
        value={active?.id || ""}
        onChange={(e) => {
          if (e.target.value) onOpen(e.target.value);
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
  );
}
