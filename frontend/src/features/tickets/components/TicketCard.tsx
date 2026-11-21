import { Ticket as TicketIcon } from "lucide-react";
import type { Ticket } from "../../../models/supportModels";
export function TicketCard({
  ticket: t,
  busy,
  send,
}: {
  ticket: Ticket;
  busy: boolean;
  send: (text: string) => void;
}) {
  return (
    <div className="ticket-card" key={t.id}>
      <TicketIcon size={18} />
      <div>
        <button
          className="ticket-select"
          disabled={busy}
          onClick={() => send(`Show details for ticket ${t.id}`)}
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
  );
}
