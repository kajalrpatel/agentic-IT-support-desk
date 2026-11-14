import { UserManager, WebStorageStateStore } from "oidc-client-ts";
import type { components } from "./generated";

export type Draft = components["schemas"]["Draft"];
export type Citation = components["schemas"]["Citation"];
export type Ticket = Required<components["schemas"]["TicketView"]>;
export type Reply = Omit<
  Required<components["schemas"]["ChatResponse"]>,
  "tickets"
> & { tickets: Ticket[] };
export type Message = {
  id: number;
  role: string;
  content: string;
  response: Reply | null;
};
export type Conversation = Omit<
  components["schemas"]["ConversationView"],
  "messages" | "response"
> & { messages: Message[]; response: Reply | null };
declare global {
  interface Window {
    SMARTDESK_CONFIG: {
      apiBase: string;
      oidcAuthority: string;
      oidcClientId: string;
      oidcScope: string;
    };
  }
}
const config = window.SMARTDESK_CONFIG;
const base = config.apiBase + "/api/v1";
let token = "";

export async function authenticate(): Promise<string> {
  const settings = await fetch(base + "/auth/config").then((r) => r.json());
  if (settings.mode === "demo") {
    const response = await fetch(base + "/auth/demo", { method: "POST" });
    if (!response.ok)
      throw new Error("Could not start the local demo session.");
    const data = await response.json();
    token = data.token;
    return data.email;
  }
  if (!config.oidcAuthority || !config.oidcClientId)
    throw new Error(
      "Sign-in is not configured. Ask your administrator to configure the identity provider.",
    );
  const manager = new UserManager({
    authority: config.oidcAuthority,
    client_id: config.oidcClientId,
    redirect_uri: window.location.origin + "/auth/callback",
    response_type: "code",
    scope: config.oidcScope,
    userStore: new WebStorageStateStore({ store: window.sessionStorage }),
  });
  if (window.location.pathname === "/auth/callback") {
    await manager.signinRedirectCallback();
    window.history.replaceState({}, "", "/");
  }
  const user = await manager.getUser();
  if (!user || user.expired) {
    await manager.signinRedirect();
    throw new Error("Redirecting to sign in…");
  }
  token = user.access_token;
  return (await api<{ email: string }>("/me")).email;
}

export async function api<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(base + path, {
    method: body === undefined ? "GET" : "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(
      typeof data.detail === "string"
        ? data.detail
        : `Request failed (${response.status}).`,
    );
  }
  return response.json();
}

export async function sendMessage(
  id: string,
  text: string,
  progress: (text: string) => void,
): Promise<Reply> {
  const response = await fetch(`${base}/conversations/${id}/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ text, request_id: crypto.randomUUID() }),
  });
  if (!response.ok) {
    const data = await response.json();
    throw new Error(data.detail || "Unable to send the message.");
  }
  if (!response.body)
    throw new Error(
      "Streaming is unavailable. Reload your conversation to check its status.",
    );
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let result: Reply | undefined;
  while (true) {
    const { value, done } = await reader.read();
    buffer += decoder.decode(value, { stream: !done });
    let boundary: number;
    while ((boundary = buffer.indexOf("\n\n")) !== -1) {
      const event = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);
      const kind = event
        .split("\n")
        .find((l) => l.startsWith("event:"))
        ?.slice(6)
        .trim();
      const raw = event
        .split("\n")
        .filter((l) => l.startsWith("data:"))
        .map((l) => l.slice(5).trim())
        .join("\n");
      if (!raw) continue;
      const data = JSON.parse(raw);
      if (kind === "progress") progress(data.text);
      if (kind === "error") throw new Error(data.detail);
      if (kind === "result") result = data;
    }
    if (done) break;
  }
  if (!result)
    throw new Error(
      "Connection interrupted. Reload this conversation before retrying to avoid duplicate submissions.",
    );
  return result;
}
