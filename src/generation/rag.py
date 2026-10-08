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
from src.generation.prompts import SYSTEM_PROMPT, build_context, build_user_message
from src.retrieval.router import Retrieval, retrieve
from src.retrieval.store import Ayat, get_ayat

NOT_FOUND = "Tidak ditemukan dalam sumber yang tersedia. Coba ubah kata kunci atau sebutkan surah/ayat tertentu."
MAX_HISTORY_MESSAGES = 4


@dataclass
class Turn:
    query: str
    retrieval: Retrieval
    ayat: list[Ayat]
    messages: list[dict]
    raw: str = ""
    validated: Validated | None = field(default=None)

    @property
    def allowed(self) -> set[tuple[int, int]]:
        return {(a.surah_no, a.ayat_no) for a in self.ayat}

    def stream(self) -> Iterator[str]:
        if not self.ayat:
            self.raw = NOT_FOUND
            yield NOT_FOUND
            return
        parts = []
        for delta in stream_chat(self.messages):
            parts.append(delta)
            yield delta
        self.raw = "".join(parts)

    def finalize(self) -> Validated:
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
