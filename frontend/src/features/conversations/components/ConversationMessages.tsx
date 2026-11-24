import { TicketCard } from "../../tickets/components/TicketCard";
import { BookOpen, Headphones } from "lucide-react";
import { useConversationScroll } from "../hooks/useConversationScroll";
import type { Conversation, Draft } from "../../../models/supportModels";
import { TicketPreview } from "../../tickets/components/TicketPreview";
export function ConversationMessages({
  active,
  email,
  busy,
  send,
  approval,
}: {
  active: Conversation;
  email: string;
  busy: boolean;
  send: (text: string) => void;
  approval: (action: "confirm" | "edit" | "cancel", draft?: Draft) => void;
}) {
  const bottom = useConversationScroll(active);
  return (
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
            {m.response?.tickets.map((ticket) => (
              <TicketCard
                key={ticket.id}
                ticket={ticket}
                busy={busy}
                send={send}
              />
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
  );
}
