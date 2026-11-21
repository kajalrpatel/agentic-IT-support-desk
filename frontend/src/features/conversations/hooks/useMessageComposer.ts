import { useState } from "react";
export function useMessageComposer({
  ready,
  busy,
  send,
}: {
  ready: boolean;
  busy: boolean;
  send: (text: string) => void;
}) {
  const [input, setInput] = useState("");
  function submit() {
    if (!ready || busy || !input.trim()) return;
    send(input);
    setInput("");
  }
  return { input, setInput, submit };
}
