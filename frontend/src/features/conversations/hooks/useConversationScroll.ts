import { useEffect, useRef } from "react";
import type { Conversation } from "../../../models/supportModels";
export function useConversationScroll(conversation: Conversation) {
  const bottom = useRef<HTMLDivElement>(null);
  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth" });
  }, [conversation]);
  return bottom;
}
