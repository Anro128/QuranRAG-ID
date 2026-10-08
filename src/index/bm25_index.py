"""Bangun indeks BM25 (bm25s + stemmer Indonesia) atas semua chunk."""
import json
import sqlite3
from functools import lru_cache

import bm25s
import Stemmer

from src.config import BM25_DIR, DB_PATH, RESOURCES

IDS_FILE = BM25_DIR / "chunk_ids.json"


@lru_cache(maxsize=1)
def stopwords() -> list[str]:
    return (RESOURCES / "stopwords_id.txt").read_text(encoding="utf-8").split()


@lru_cache(maxsize=1)
def stemmer() -> Stemmer.Stemmer:
    return Stemmer.Stemmer("indonesian")


def tokenize(texts: list[str]):
    return bm25s.tokenize(texts, stopwords=stopwords(), stemmer=stemmer(), show_progress=False)


def main() -> None:
    con = sqlite3.connect(DB_PATH)
    rows = con.execute("SELECT id, teks FROM chunks ORDER BY id").fetchall()
    con.close()

    retriever = bm25s.BM25()
    retriever.index(tokenize([r[1] for r in rows]))
    BM25_DIR.mkdir(parents=True, exist_ok=True)
    retriever.save(str(BM25_DIR))
    IDS_FILE.write_text(json.dumps([r[0] for r in rows]), encoding="utf-8")
    print(f"BM25: {len(rows)} dokumen diindeks ke {BM25_DIR}")


if __name__ == "__main__":
    main()
