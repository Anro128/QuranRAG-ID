"""Ekspansi query: kamus sinonim (selalu) + DeepSeek (opsional, bila API key tersedia).

Hasil ekspansi hanya dipakai untuk BM25; pencarian dense memakai query asli
agar maknanya tidak terdilusi.
"""
import json
import re
from functools import lru_cache

from src.config import DEEPSEEK_API_KEY, RESOURCES


@lru_cache(maxsize=1)
def _groups() -> list[list[str]]:
    return json.loads((RESOURCES / "sinonim.json").read_text(encoding="utf-8"))["grup"]


def expand_synonyms(query: str) -> list[str]:
    """Tambahkan istilah baku (anggota pertama grup) bila query hanya memakai variannya.

    Menambahkan seluruh anggota grup terbukti mendilusi BM25, jadi hanya istilah baku
    Kemenag yang ditambahkan, misalnya "sholat" -> "salat", "bunga" -> "riba".
    """
    q = f" {' '.join(re.findall(r'[a-z0-9-]+', query.lower()))} "
    extra: list[str] = []
    for canonical, *variants in _groups():
        if f" {canonical} " not in q and any(f" {v} " in q for v in variants):
            extra.append(canonical)
    return extra


EXPAND_PROMPT = """Anda membantu mesin pencari ayat Al-Qur'an terjemahan Kemenag (bahasa Indonesia).
Berikan maksimal 8 kata kunci atau frasa pendek yang kemungkinan muncul di terjemahan atau tafsir
ayat yang relevan dengan pertanyaan berikut. Tulis dalam satu baris, dipisah koma, tanpa penjelasan.

Pertanyaan: {query}"""


@lru_cache(maxsize=512)
def expand_llm(query: str) -> tuple[str, ...]:
    if not DEEPSEEK_API_KEY:
        return ()
    from src.generation.llm import complete  # impor lambat: modul generation opsional di sini

    try:
        text = complete(EXPAND_PROMPT.format(query=query), max_tokens=80, temperature=0.0)
    except Exception:
        return ()
    terms = [t.strip(" .\"'") for t in text.replace("\n", ",").split(",")]
    return tuple(t for t in terms if 1 < len(t) < 40)[:8]


def expand(query: str, use_llm: bool = True) -> str:
    """Kembalikan query untuk BM25: query asli + sinonim (+ kata kunci LLM)."""
    parts = [query, *expand_synonyms(query)]
    if use_llm:
        parts.extend(expand_llm(query))
    return " ".join(parts)
