"""Query router: referensi langsung -> lookup DB; selain itu -> pencarian hybrid."""
from dataclasses import dataclass, field

from src.retrieval.expand import expand
from src.retrieval.hybrid import Hit, search
from src.retrieval.ref_parser import Ref, parse
from src.retrieval.store import chunks_for_refs


@dataclass
class Retrieval:
    query: str
    route: str                      # 'ref' | 'semantic'
    hits: list[Hit]
    refs: list[Ref] = field(default_factory=list)
    surah_filter: int | None = None
    bm25_query: str | None = None

    def ayat_keys(self) -> list[tuple[int, int]]:
        """Pasangan (surah, ayat) unik sesuai urutan relevansi (chunk tafsir dihitung ke ayatnya)."""
        return list(dict.fromkeys((h.surah_no, h.ayat_no) for h in self.hits))


def retrieve(query: str, k: int = 8, mode: str = "hybrid",
             use_synonyms: bool = True, use_llm_expand: bool = True) -> Retrieval:
    parsed = parse(query)
    if parsed.refs:
        return Retrieval(query, "ref", chunks_for_refs(parsed.refs), refs=parsed.refs)

    bm25_query = expand(query, use_llm=use_llm_expand) if use_synonyms else query
    hits = search(query, k=k, mode=mode, surah_no=parsed.surah_filter, bm25_query=bm25_query)
    return Retrieval(query, "semantic", hits, surah_filter=parsed.surah_filter, bm25_query=bm25_query)
