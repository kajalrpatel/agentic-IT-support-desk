import { readServerEvents } from "../../../api/eventStream";
import { base } from "../../../config/runtime";
import { authorizationHeaders } from "../../../api/client";
import type { Reply } from "../../../models/supportModels";
export async function sendMessage(
  id: string,
  text: string,
  progress: (text: string) => void,
): Promise<Reply> {
  const response = await fetch(
    `${base}/conversations/${encodeURIComponent(id)}/stream`,
    {
      method: "POST",
      headers: authorizationHeaders(),
      body: JSON.stringify({ text, request_id: crypto.randomUUID() }),
    },
  );
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(
      typeof data.detail === "string"
        ? data.detail
        : "Unable to send the message.",
    );
  }
  if (!response.body)
    throw new Error(
      "Streaming is unavailable. Reload your conversation to check its status.",
    );
  let result: Reply | undefined;
  for await (const event of readServerEvents(response.body)) {
    if (!["progress", "error", "result"].includes(event.kind)) continue;
    const data = JSON.parse(event.data);
    if (event.kind === "progress" && typeof data.text === "string")
      progress(data.text);
    if (event.kind === "error")
      throw new Error(
        typeof data.detail === "string"
          ? data.detail
          : "Unable to finish this request.",
      );
    if (event.kind === "result") result = data;
  }
  if (!result)
    throw new Error(
      "Connection interrupted. Reload this conversation before retrying to avoid duplicate submissions.",
    );
  return result;
}
