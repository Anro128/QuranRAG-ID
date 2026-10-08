"""Pipeline RAG: retrieve -> susun konteks -> DeepSeek (streaming) -> validasi sitasi.

Pemakaian:
    turn = prepare("ayat tentang sabar")
    for delta in turn.stream():
        print(delta, end="")
    final = turn.finalize()
"""
from collections.abc import Iterator
from dataclasses import dataclass, field

from src.generation.citation_validator import Validated, validate
from src.generation.llm import stream_chat
from src.generation.prompts import OFF_TOPIC_MARKER, SYSTEM_PROMPT, build_context, build_user_message
from src.retrieval.router import Retrieval, retrieve
from src.retrieval.store import Ayat, get_ayat

NOT_FOUND = "Tidak ditemukan dalam sumber yang tersedia. Coba ubah kata kunci atau sebutkan surah/ayat tertentu."
OFF_TOPIC_FALLBACK = "Maaf, saya hanya dapat menjawab pertanyaan seputar Al-Qur'an."
EMPTY_ANSWER = "Maaf, AI tidak menghasilkan jawaban kali ini. Silakan kirim ulang pertanyaan Anda; ayat yang ditemukan tetap ditampilkan di bawah."
MAX_HISTORY_MESSAGES = 4


@dataclass
class Turn:
    query: str
    retrieval: Retrieval
    ayat: list[Ayat]
    messages: list[dict]
    raw: str = ""
    off_topic: bool = False  # LLM menilai pertanyaan di luar Al-Qur'an/Islam (penanda OFF_TOPIC_MARKER)
    validated: Validated | None = field(default=None)

    @property
    def allowed(self) -> set[tuple[int, int]]:
        # jawaban di luar topik tidak boleh mengutip ayat apa pun
        return set() if self.off_topic else {(a.surah_no, a.ayat_no) for a in self.ayat}

    def stream(self) -> Iterator[str]:
        """Teruskan jawaban LLM, kecuali penanda di luar topik di awal jawaban yang ditahan lalu dibuang."""
        if not self.ayat:
            self.raw = NOT_FOUND
            yield NOT_FOUND
            return

        parts: list[str] = []
        head, decided = "", False
        for delta in stream_chat(self.messages):
            if decided:
                parts.append(delta)
                yield delta
                continue
            head += delta
            stripped = head.lstrip()
            if stripped.startswith(OFF_TOPIC_MARKER):
                self.off_topic, decided = True, True
                rest = stripped[len(OFF_TOPIC_MARKER):].lstrip()
            elif not OFF_TOPIC_MARKER.startswith(stripped):
                decided, rest = True, head
            else:
                continue  # masih bisa jadi awal penanda: tahan dulu
            if rest:
                parts.append(rest)
                yield rest
        if not decided and head.strip():  # jawaban berakhir saat masih tertahan
            self.off_topic = head.strip() == OFF_TOPIC_MARKER
            if not self.off_topic:
                parts.append(head)
                yield head
        self.raw = "".join(parts)

    def finalize(self) -> Validated:
        if not self.raw.strip():
            self.raw = OFF_TOPIC_FALLBACK if self.off_topic else EMPTY_ANSWER
        self.validated = validate(self.raw, self.allowed)
        return self.validated


def prepare(query: str, history: list[dict] | None = None, k: int = 10, use_llm_expand: bool = True) -> Turn:
    result = retrieve(query, k=k, use_llm_expand=use_llm_expand)
    ayat = get_ayat(result.ayat_keys())
    context = build_context(ayat, result.hits)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages += (history or [])[-MAX_HISTORY_MESSAGES:]
    messages.append({"role": "user", "content": build_user_message(query, context)})
    return Turn(query=query, retrieval=result, ayat=ayat, messages=messages)
