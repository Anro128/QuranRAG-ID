import type { Ayat, Health } from "./types";

export interface ChatRequest {
  query: string;
  history: { role: "user" | "assistant"; content: string }[];
  use_llm_expand: boolean;
}

export type ChatEvent =
  | { event: "retrieval"; data: { route: string; refs: string[]; surah_filter: number | null; ayat: Ayat[] } }
  | { event: "delta"; data: { text: string } }
  | {
      event: "final";
      data: { text: string; cited: [number, number][]; invalid: string[]; ai: boolean; off_topic?: boolean };
    }
  | { event: "error"; data: { message: string; status?: number | null } };

/** Dilempar bila sesi tidak valid/kedaluwarsa (HTTP 401) agar UI kembali ke halaman login. */
export class UnauthorizedError extends Error {}

async function errorMessage(res: Response): Promise<string> {
  try {
    const body = await res.json();
    if (typeof body.detail === "string") return body.detail;
  } catch {
    /* bukan JSON */
  }
  return `Server membalas HTTP ${res.status}`;
}

export async function getHealth(): Promise<Health> {
  const res = await fetch("/api/health");
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function getMe(): Promise<string | null> {
  const res = await fetch("/api/auth/me");
  if (res.status === 401) return null;
  if (!res.ok) throw new Error(await errorMessage(res));
  return (await res.json()).username;
}

export async function login(username: string, password: string): Promise<string> {
  const res = await fetch("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!res.ok) throw new Error(await errorMessage(res));
  return (await res.json()).username;
}

export async function logout(): Promise<void> {
  await fetch("/api/auth/logout", { method: "POST" });
}

/** POST /api/chat lalu baca Server-Sent Events dari body response. */
export async function streamChat(
  body: ChatRequest,
  onEvent: (e: ChatEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
  if (res.status === 401) throw new UnauthorizedError(await errorMessage(res));
  if (!res.ok || !res.body) throw new Error(await errorMessage(res));

  const reader = res.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += value;
    let sep: number;
    while ((sep = buffer.indexOf("\n\n")) >= 0) {
      const raw = buffer.slice(0, sep);
      buffer = buffer.slice(sep + 2);
      let event = "message";
      let data = "";
      for (const line of raw.split("\n")) {
        if (line.startsWith("event: ")) event = line.slice(7).trim();
        else if (line.startsWith("data: ")) data += line.slice(6);
      }
      if (data) onEvent({ event, data: JSON.parse(data) } as ChatEvent);
    }
  }
}
