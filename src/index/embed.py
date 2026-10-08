"""Embedding semua chunk ke LanceDB (model e5: prefix "passage: " / "query: ")."""
import argparse
import sqlite3
from functools import lru_cache

import lancedb
import pyarrow as pa
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

from src.config import DB_PATH, EMBED_MODEL, LANCE_TABLE, LANCEDB_DIR


@lru_cache(maxsize=1)
def get_model() -> SentenceTransformer:
    return SentenceTransformer(EMBED_MODEL, device="cpu")


def embed_query(text: str) -> list[float]:
    return get_model().encode(f"query: {text}", normalize_embeddings=True).tolist()


def main(batch_size: int, limit: int | None) -> None:
    con = sqlite3.connect(DB_PATH)
    sql = "SELECT id, tipe, surah_no, ayat_no, teks FROM chunks ORDER BY id"
    rows = con.execute(sql + (f" LIMIT {int(limit)}" if limit else "")).fetchall()
    con.close()

    model = get_model()
    dim = model.get_sentence_embedding_dimension()
    schema = pa.schema([
        ("id", pa.int64()),
        ("tipe", pa.string()),
        ("surah_no", pa.int32()),
        ("ayat_no", pa.int32()),
        ("vector", pa.list_(pa.float32(), dim)),
    ])
    db = lancedb.connect(str(LANCEDB_DIR))
    table = db.create_table(LANCE_TABLE, schema=schema, mode="overwrite")

    # urutkan berdasarkan panjang agar padding per batch minimal (jauh lebih cepat di CPU)
    rows.sort(key=lambda r: len(r[4]))
    for start in tqdm(range(0, len(rows), batch_size), desc="embedding"):
        batch = rows[start:start + batch_size]
        vecs = model.encode([f"passage: {r[4]}" for r in batch], normalize_embeddings=True, batch_size=batch_size)
        table.add([
            {"id": r[0], "tipe": r[1], "surah_no": r[2], "ayat_no": r[3], "vector": v.tolist()}
            for r, v in zip(batch, vecs)
        ])
    print(f"{table.count_rows()} vektor (dim={dim}) ditulis ke {LANCEDB_DIR}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--limit", type=int, default=None, help="hanya N chunk pertama (untuk uji cepat)")
    args = parser.parse_args()
    main(args.batch_size, args.limit)
