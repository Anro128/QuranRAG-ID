import { useEffect, useRef, useState } from "react";
import { getHealth, streamChat, UnauthorizedError } from "../api";
import type { AssistantMessage, Health, Message } from "../types";
import { AssistantBubble } from "./AssistantBubble";
import { Logo, MenuIcon, PlusIcon, SendIcon, StopIcon } from "./Icons";
import { Sidebar } from "./Sidebar";

let counter = 0;
const newId = () => `m${Date.now()}-${counter++}`;

interface Props {
  username: string;
  onLogout: () => void;
  onSessionExpired: () => void;
}

/** Riwayat chat sengaja hanya disimpan di state komponen: hilang saat chat baru, refresh, atau logout. */
export function Workspace({ username, onLogout, onSessionExpired }: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [health, setHealth] = useState<Health | null>(null);
  const [healthError, setHealthError] = useState(false);
  const [showTafsir, setShowTafsir] = useState(true);
  const [useLlmExpand, setUseLlmExpand] = useState(true);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    getHealth().then(setHealth).catch(() => setHealthError(true));
    return () => abortRef.current?.abort();
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages.length]);

  const patch = (id: string, fn: (m: AssistantMessage) => Partial<AssistantMessage>) =>
    setMessages((prev) => prev.map((m) => (m.id === id && m.role === "assistant" ? { ...m, ...fn(m) } : m)));

  async function send(text: string) {
    const query = text.trim();
    if (!query || busy) return;
    setSidebarOpen(false);

    const history = messages
      .filter((m) => m.role === "user" || (m.status === "done" && m.content))
      .map((m) => ({ role: m.role, content: m.content }));
    const assistantId = newId();
    setMessages((prev) => [
      ...prev,
      { id: newId(), role: "user", content: query },
      { id: assistantId, role: "assistant", content: "", status: "searching", ayat: [], cited: [], invalid: [], ai: false },
    ]);
    setInput("");
    setBusy(true);

    const controller = new AbortController();
    abortRef.current = controller;
    try {
      await streamChat(
        { query, history, use_llm_expand: useLlmExpand },
        (e) => {
          switch (e.event) {
            case "retrieval":
              patch(assistantId, () => ({ ayat: e.data.ayat, status: "streaming" }));
              break;
            case "delta":
              patch(assistantId, (m) => ({ content: m.content + e.data.text }));
              break;
            case "final":
              patch(assistantId, () => ({
                content: e.data.text,
                cited: e.data.cited,
                invalid: e.data.invalid,
                ai: e.data.ai,
                status: "done",
              }));
              break;
            case "error":
              patch(assistantId, () => ({ content: "", error: e.data.message, status: "error" }));
              break;
          }
        },
        controller.signal,
      );
    } catch (err) {
      if (err instanceof UnauthorizedError) {
        onSessionExpired();
        return;
      }
      if (!controller.signal.aborted) {
        patch(assistantId, () => ({ error: `Tidak dapat terhubung ke server (${(err as Error).message})`, status: "error" }));
      }
    } finally {
      patch(assistantId, (m) => (m.status === "searching" || m.status === "streaming" ? { status: "done" } : {}));
      setBusy(false);
      abortRef.current = null;
    }
  }

  function newChat() {
    abortRef.current?.abort();
    setMessages([]);
    setInput("");
    setSidebarOpen(false);
    inputRef.current?.focus();
  }

  function handleLogout() {
    abortRef.current?.abort();
    onLogout();
  }

  const firstQuestion = messages.find((m) => m.role === "user")?.content;

  return (
    <div className="app-shell">
      <Sidebar
        open={sidebarOpen}
        username={username}
        llmConfigured={!!health?.llm_configured}
        showTafsir={showTafsir}
        useLlmExpand={useLlmExpand}
        busy={busy}
        onClose={() => setSidebarOpen(false)}
        onNewChat={newChat}
        onAsk={send}
        onShowTafsir={setShowTafsir}
        onUseLlmExpand={setUseLlmExpand}
        onLogout={handleLogout}
      />

      <div className="main">
        <header className="main-head">
          <button type="button" className="icon-btn only-mobile" onClick={() => setSidebarOpen(true)} aria-label="Buka menu">
            <MenuIcon />
          </button>
          <span className="chat-title">{firstQuestion ?? "Chat baru"}</span>
          {messages.length > 0 && (
            <button type="button" className="icon-btn only-mobile" onClick={newChat} aria-label="Chat baru">
              <PlusIcon />
            </button>
          )}
        </header>

        <div className="main-scroll">
          <div className="column">
            {healthError && (
              <div className="banner error">Backend tidak dapat dihubungi. Jalankan: uvicorn src.api:app --port 8000</div>
            )}
            {health && !health.llm_configured && (
              <div className="banner warn">DEEPSEEK_API_KEY belum diisi. Aplikasi berjalan sebagai mesin pencari ayat saja.</div>
            )}

            {messages.length === 0 ? (
              <div className="empty">
                <Logo size={56} className="empty-logo" />
                <h2>Assalamu'alaikum, {username}</h2>
                <p>Tanyakan tema, kisah, atau sebut ayat tertentu. Setiap jawaban menyertakan ayat sumbernya.</p>
              </div>
            ) : (
              <div className="chat">
                {messages.map((m) =>
                  m.role === "user" ? (
                    <div key={m.id} className="bubble user">
                      {m.content}
                    </div>
                  ) : (
                    <AssistantBubble key={m.id} message={m} showTafsir={showTafsir} />
                  ),
                )}
              </div>
            )}
            <div ref={bottomRef} />
          </div>
        </div>

        <div className="composer-wrap">
          <form
            className="composer column"
            onSubmit={(e) => {
              e.preventDefault();
              send(input);
            }}
          >
            <textarea
              ref={inputRef}
              value={input}
              rows={1}
              maxLength={1000}
              placeholder="Tanyakan sesuatu tentang Al-Qur'an…"
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  send(input);
                }
              }}
            />
            {busy ? (
              <button type="button" className="primary with-icon" onClick={() => abortRef.current?.abort()}>
                <StopIcon size={18} /> Stop
              </button>
            ) : (
              <button type="submit" className="primary with-icon" disabled={!input.trim()}>
                Kirim <SendIcon size={18} />
              </button>
            )}
          </form>
          <p className="footnote">Jawaban AI bisa keliru. Selalu periksa ayat dan tafsir yang dikutip.</p>
        </div>
      </div>
    </div>
  );
}
