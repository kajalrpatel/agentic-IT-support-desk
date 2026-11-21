import type { components } from "../api/generated";
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
