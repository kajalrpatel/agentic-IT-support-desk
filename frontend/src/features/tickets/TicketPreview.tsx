import { useEffect, useState } from "react";
import type { Draft, Reply } from "../../api/client";

export function TicketPreview({
  reply,
  busy,
  onAction,
}: {
  reply: Reply;
  busy: boolean;
  onAction: (action: "confirm" | "edit" | "cancel", draft?: Draft) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<Draft | null>(reply.draft);
  useEffect(() => {
    setDraft(reply.draft);
    setEditing(false);
  }, [reply]);
  if (!draft) return null;
  const update = (field: keyof Draft, value: string) =>
    setDraft({ ...draft, [field]: value });
  return (
    <section className="ticket-preview" aria-label="Ticket preview">
      <div className="preview-heading">
        <span className="eyebrow">REVIEW BEFORE SENDING</span>
        <span className="badge">Draft {reply.draft_version}</span>
      </div>
      <h3>{editing ? "Edit your ticket" : draft.summary}</h3>
      {editing ? (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            onAction("edit", draft);
          }}
        >
          <label>
            Summary
            <input
              required
              minLength={3}
              maxLength={200}
              value={draft.summary}
              onChange={(e) => update("summary", e.target.value)}
            />
          </label>
          <label>
            Description
            <textarea
              required
              minLength={10}
              maxLength={5000}
              value={draft.description}
              onChange={(e) => update("description", e.target.value)}
            />
          </label>
          <div className="form-row">
            <label>
              Category
              <select
                value={draft.category}
                onChange={(e) => update("category", e.target.value)}
              >
                <option>IT</option>
                <option>HR</option>
              </select>
            </label>
            <label>
              Priority
              <select
                value={draft.priority}
                onChange={(e) => update("priority", e.target.value)}
              >
                {["Low", "Medium", "High", "Critical"].map((p) => (
                  <option key={p}>{p}</option>
                ))}
              </select>
            </label>
          </div>
          <button disabled={busy} className="primary" type="submit">
            Save and review
          </button>
          <button type="button" onClick={() => setEditing(false)}>
            Discard edits
          </button>
        </form>
      ) : (
        <>
          <p>{draft.description}</p>
          <dl>
            <dt>Employee</dt>
            <dd>{draft.email}</dd>
            <dt>Category</dt>
            <dd>{draft.category}</dd>
            <dt>Priority</dt>
            <dd>{draft.priority}</dd>
          </dl>
          <div className="actions">
            <button
              className="primary"
              disabled={busy}
              onClick={() => onAction("confirm")}
            >
              Confirm & create ticket
            </button>
            <button disabled={busy} onClick={() => setEditing(true)}>
              Edit
            </button>
            <button disabled={busy} onClick={() => onAction("cancel")}>
              Cancel
            </button>
          </div>
        </>
      )}
    </section>
  );
}
