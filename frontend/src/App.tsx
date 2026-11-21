import { CircleHelp } from "lucide-react";
import { WorkspaceHeader } from "./app/components/WorkspaceHeader";
import { useConversations } from "./features/conversations/hooks/useConversations";
import { ConversationSidebar } from "./features/conversations/components/ConversationSidebar";
import { ConversationNavigation } from "./features/conversations/components/ConversationNavigation";
import { ConversationWelcome } from "./features/conversations/components/ConversationWelcome";
import { ConversationMessages } from "./features/conversations/components/ConversationMessages";
import { MessageComposer } from "./features/conversations/components/MessageComposer";
export default function App() {
  const chat = useConversations();
  const navigation = {
    conversations: chat.conversations,
    active: chat.active,
    busy: chat.busy,
    onNew: chat.startNew,
    onOpen: chat.open,
  };
  return (
    <div className="app-shell">
      <ConversationSidebar {...navigation} email={chat.email} />
      <main>
        <WorkspaceHeader />
        <ConversationNavigation {...navigation} />
        <div className="chat-area">
          {chat.active?.messages.length ? (
            <ConversationMessages
              active={chat.active}
              email={chat.email}
              busy={chat.busy}
              send={chat.send}
              approval={chat.approval}
            />
          ) : (
            <ConversationWelcome
              ready={chat.ready}
              busy={chat.busy}
              send={chat.send}
            />
          )}
          {chat.busy && (
            <div className="progress" role="status">
              <span className="pulse" />
              {chat.progress || "Working on your request..."}
            </div>
          )}
          {chat.error && (
            <div className="error" role="alert">
              <CircleHelp size={18} />
              <span>{chat.error}</span>
              {chat.active && (
                <button
                  disabled={chat.busy}
                  onClick={() => chat.open(chat.active!.id)}
                >
                  Reload conversation
                </button>
              )}
            </div>
          )}
        </div>
        <MessageComposer
          key={chat.active?.id || "new"}
          ready={chat.ready}
          busy={chat.busy}
          send={chat.send}
        />
      </main>
    </div>
  );
}
