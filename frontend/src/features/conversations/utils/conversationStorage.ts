// Conversation IDs are a convenience only; the server enforces ownership.
const key = "smartdesk-conversation";
export const conversationStorage = {
  read(): string | null {
    try {
      return localStorage.getItem(key);
    } catch {
      return null;
    }
  },
  write(id: string | null) {
    try {
      if (id) localStorage.setItem(key, id);
      else localStorage.removeItem(key);
    } catch {
      /* Storage can be blocked by browser policy. */
    }
  },
};
