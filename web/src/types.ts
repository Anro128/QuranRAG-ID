export interface Ayat {
  surah_no: number;
  ayat_no: number;
  nama_surah: string;
  juz: number;
  teks_arab: string;
  terjemahan: string;
  tafsir: string | null;
  label: string;
}

export interface UserMessage {
  id: string;
  role: "user";
  content: string;
}

export interface AssistantMessage {
  id: string;
  role: "assistant";
  content: string;
  status: "searching" | "streaming" | "done" | "error";
  ayat: Ayat[];
  cited: [number, number][];
  invalid: string[];
  ai: boolean;
  error?: string;
}

export type Message = UserMessage | AssistantMessage;

export interface Health {
  status: string;
  llm_configured: boolean;
  model: string;
}
