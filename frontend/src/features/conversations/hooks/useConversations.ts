import { useEffect, useRef, useState } from "react";
import { authenticate } from "../../auth/services/authentication";
import { conversationApi } from "../services/conversationApi";
import { conversationStorage } from "../utils/conversationStorage";
import { sendMessage } from "../services/messageStream";
import type {
  Conversation,
  Draft,
  Message,
} from "../../../models/supportModels";

import { errorMessage } from "../utils/errorMessage";

/** Owns workspace state and serializes writes; components only render and emit actions. */
export function useConversations() {
  const [email, setEmail] = useState("");
  const [ready, setReady] = useState(false);
  const [error, setError] = useState("");
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [active, setActive] = useState<Conversation | null>(null);
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState("");
  const writeInFlight = useRef(false);
  const selectionVersion = useRef(0);
  const mounted = useRef(false);

  useEffect(() => {
    let cancelled = false;
    mounted.current = true;
    (async () => {
      try {
        const identity = await authenticate();
        const list = await conversationApi.list();
        if (cancelled) return;
        setEmail(identity);
        setConversations(list);
        const previous = conversationStorage.read();
        if (previous && list.some((c) => c.id === previous)) {
          const conversation = await conversationApi.get(previous);
          if (cancelled) return;
          setActive(conversation);
        } else {
          conversationStorage.write(null);
        }
        setReady(true);
      } catch (e) {
        if (!cancelled) setError(errorMessage(e));
      }
    })();
    return () => {
      cancelled = true;
      mounted.current = false;
      selectionVersion.current++;
    };
  }, []);

  async function open(id: string) {
    if (writeInFlight.current || !ready) return;
    const version = ++selectionVersion.current;
    setBusy(true);
    setError("");
    try {
      const conversation = await conversationApi.get(id);
      if (!mounted.current || version !== selectionVersion.current) return;
      setActive(conversation);
      conversationStorage.write(id);
    } catch (e) {
      if (mounted.current && version === selectionVersion.current)
        setError(errorMessage(e));
    } finally {
      if (mounted.current && version === selectionVersion.current)
        setBusy(false);
    }
  }

  async function refresh(id: string) {
    const [conversation, list] = await Promise.all([
      conversationApi.get(id),
      conversationApi.list(),
    ]);
    if (!mounted.current) return;
    setActive(conversation);
    setConversations(list);
  }

  async function runWrite(operation: () => Promise<void>) {
    if (writeInFlight.current || busy || !ready) return;
    writeInFlight.current = true;
    ++selectionVersion.current;
    setBusy(true);
    setError("");
    try {
      await operation();
    } catch (e) {
      if (mounted.current) setError(errorMessage(e));
    } finally {
      writeInFlight.current = false;
      if (mounted.current) {
        setBusy(false);
        setProgress("");
      }
    }
  }

  async function send(text: string) {
    if (!text.trim()) return;
    await runWrite(async () => {
      const conversation = active ?? (await conversationApi.create());
      if (!mounted.current) return;
      conversationStorage.write(conversation.id);
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
      await sendMessage(conversation.id, text, (value) => {
        if (mounted.current) setProgress(value);
      });
      await refresh(conversation.id);
    });
  }

  async function approval(
    action: "confirm" | "edit" | "cancel",
    draft?: Draft,
  ) {
    if (
      !active?.response?.pending_approval ||
      active.response.draft_version == null
    )
      return;
    const id = active.id;
    const version = active.response.draft_version;
    await runWrite(async () => {
      await conversationApi.approve(id, {
        action,
        draft,
        version,
        request_id: crypto.randomUUID(),
      });
      await refresh(id);
    });
  }

  function startNew() {
    if (writeInFlight.current || busy || !ready) return;
    ++selectionVersion.current;
    setActive(null);
    setError("");
    conversationStorage.write(null);
  }
  return {
    email,
    ready,
    error,
    conversations,
    active,
    busy,
    progress,
    open,
    send,
    approval,
    startNew,
  };
}
