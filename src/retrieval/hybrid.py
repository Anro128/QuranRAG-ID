"""Pencarian dense (LanceDB), BM25, dan gabungan keduanya dengan Reciprocal Rank Fusion."""
import json
import sqlite3
from dataclasses import dataclass
from functools import lru_cache

import bm25s
import lancedb

from src.config import BM25_DIR, DB_PATH, LANCE_TABLE, LANCEDB_DIR
from src.index.bm25_index import IDS_FILE, tokenize
from src.index.embed import embed_query

RRF_K = 60


@dataclass
class Hit:
    chunk_id: int
    tipe: str
    surah_no: int
    ayat_no: int
    teks: str
    score: float


@lru_cache(maxsize=1)
def _lance_table():
    return lancedb.connect(str(LANCEDB_DIR)).open_table(LANCE_TABLE)


@lru_cache(maxsize=1)
def _bm25():
    retriever = bm25s.BM25.load(str(BM25_DIR))
    ids = json.loads(IDS_FILE.read_text(encoding="utf-8"))
    return retriever, ids


def _where(tipe: str | None, surah_no: int | None) -> str | None:
    clauses = []
    if tipe in ("ayat", "tafsir"):
        clauses.append(f"tipe = '{tipe}'")
    if surah_no is not None:
        clauses.append(f"surah_no = {int(surah_no)}")
    return " AND ".join(clauses) or None


def dense_search(query: str, k: int = 30, tipe: str | None = None, surah_no: int | None = None) -> list[tuple[int, float]]:
    q = _lance_table().search(embed_query(query)).metric("cosine").limit(k)
    if where := _where(tipe, surah_no):
        q = q.where(where, prefilter=True)
    return [(int(r["id"]), 1.0 - float(r["_distance"])) for r in q.to_list()]


def bm25_search(query: str, k: int = 30, tipe: str | None = None, surah_no: int | None = None) -> list[tuple[int, float]]:
    retriever, ids = _bm25()
    tokens = tokenize([query])
    if not tokens.vocab:
        return []
    filtered = tipe is not None or surah_no is not None
    # bila difilter, ambil seluruh skor lalu saring (indeks kecil, tetap cepat)
    fetch = len(ids) if filtered else min(k, len(ids))
    docs, scores = retriever.retrieve(tokens, k=fetch, show_progress=False)
    hits = [(ids[int(d)], float(s)) for d, s in zip(docs[0], scores[0]) if s > 0]
    if filtered:
        meta = _chunk_meta()
        hits = [h for h in hits
                if (tipe is None or meta[h[0]][0] == tipe) and (surah_no is None or meta[h[0]][1] == surah_no)]
    return hits[:k]


@lru_cache(maxsize=1)
def _chunk_meta() -> dict[int, tuple[str, int]]:
    con = sqlite3.connect(DB_PATH)
    meta = {r[0]: (r[1], r[2]) for r in con.execute("SELECT id, tipe, surah_no FROM chunks")}
    con.close()
    return meta


def rrf(rankings: list[list[tuple[int, float]]], k: int = RRF_K) -> list[tuple[int, float]]:
    scores: dict[int, float] = {}
    for ranking in rankings:
        for rank, (chunk_id, _) in enumerate(ranking):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (k + rank + 1)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


def load_hits(scored: list[tuple[int, float]]) -> list[Hit]:
    if not scored:
        return []
    con = sqlite3.connect(DB_PATH)
    marks = ",".join("?" * len(scored))
    rows = {r[0]: r for r in con.execute(
        f"SELECT id, tipe, surah_no, ayat_no, teks FROM chunks WHERE id IN ({marks})", [s[0] for s in scored]
    )}
    con.close()
    return [Hit(*rows[cid], score=score) for cid, score in scored if cid in rows]


def search(query: str, k: int = 8, mode: str = "hybrid", tipe: str | None = None,
           surah_no: int | None = None, bm25_query: str | None = None, pool: int = 30) -> list[Hit]:
    """bm25_query: query yang sudah diperluas (sinonim/LLM); default = query asli."""
    bm25_query = bm25_query or query
    if mode == "dense":
        scored = dense_search(query, k, tipe, surah_no)
    elif mode == "bm25":
        scored = bm25_search(bm25_query, k, tipe, surah_no)
    else:
        scored = rrf([dense_search(query, pool, tipe, surah_no), bm25_search(bm25_query, pool, tipe, surah_no)])[:k]
    return load_hits(scored)
