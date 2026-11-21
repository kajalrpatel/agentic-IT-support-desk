import { useEffect, useState } from "react";
import type { Draft, Reply } from "../../../models/supportModels";

export function useTicketDraft(reply: Reply) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<Draft | null>(reply.draft);
  useEffect(() => {
    setDraft(reply.draft);
    setEditing(false);
  }, [reply]);
  function update<K extends keyof Draft>(field: K, value: Draft[K]) {
    setDraft((current) => (current ? { ...current, [field]: value } : null));
  }
  function discardEdits() {
    setDraft(reply.draft);
    setEditing(false);
  }
  return {
    editing,
    draft,
    update,
    discardEdits,
    startEditing: () => setEditing(true),
  };
}
