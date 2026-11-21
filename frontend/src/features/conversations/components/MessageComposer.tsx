import { ArrowUp } from "lucide-react";
import { useMessageComposer } from "../hooks/useMessageComposer";
export function MessageComposer({
  ready,
  busy,
  send,
}: {
  ready: boolean;
  busy: boolean;
  send: (text: string) => void;
}) {
  const { input, setInput, submit } = useMessageComposer({ ready, busy, send });
  return (
    <footer className="composer-wrap">
      <form
        className="composer"
        onSubmit={(e) => {
          e.preventDefault();
          submit();
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
            if (
              e.key === "Enter" &&
              !e.shiftKey &&
              !e.nativeEvent.isComposing
            ) {
              e.preventDefault();
              submit();
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
  );
}
