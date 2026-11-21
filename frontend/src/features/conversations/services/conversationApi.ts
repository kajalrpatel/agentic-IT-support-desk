import { api } from "../../../api/client";
import type { Conversation, Draft, Reply } from "../../../models/supportModels";
export const conversationApi = {
  list: () => api<Conversation[]>("/conversations"),
  get: (id: string) =>
    api<Conversation>(`/conversations/${encodeURIComponent(id)}`),
  create: () => api<Conversation>("/conversations", {}),
  approve: (
    id: string,
    body: {
      action: "confirm" | "edit" | "cancel";
      draft?: Draft;
      version: number;
      request_id: string;
    },
  ) => api<Reply>(`/conversations/${encodeURIComponent(id)}/approval`, body),
};
