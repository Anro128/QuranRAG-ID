"""Evaluasi retrieval atas eval/golden_set.jsonl.

Unit penilaian = ayat: chunk tafsir dihitung sebagai hit untuk ayat yang ditafsirkannya.
Metrik per konfigurasi:
    Hit@5     : minimal satu ayat yang diharapkan muncul di 5 ayat teratas
    Recall@5  : proporsi ayat yang diharapkan yang muncul di 5 ayat teratas
    Recall@10 : idem untuk 10 ayat teratas
    MRR       : 1 / peringkat ayat benar pertama (dalam 10 teratas)

Contoh:
    python -m eval.run_eval
    python -m eval.run_eval --configs hybrid+sin --llm --detail
"""
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

from src.retrieval.router import retrieve

GOLDEN = Path(__file__).parent / "golden_set.jsonl"
CONFIGS = {
    "dense": dict(mode="dense", use_synonyms=False),
    "bm25": dict(mode="bm25", use_synonyms=False),
    "bm25+sin": dict(mode="bm25", use_synonyms=True),
    "hybrid": dict(mode="hybrid", use_synonyms=False),
    "hybrid+sin": dict(mode="hybrid", use_synonyms=True),
}
CHUNK_POOL = 25  # chunk yang diambil agar tersedia >= 10 ayat unik


def score(ranked: list[str], expected: set[str]) -> dict[str, float]:
    top5, top10 = ranked[:5], ranked[:10]
    first = next((i for i, r in enumerate(top10, start=1) if r in expected), None)
    return {
        "hit@5": float(any(r in expected for r in top5)),
        "recall@5": len(expected & set(top5)) / len(expected),
        "recall@10": len(expected & set(top10)) / len(expected),
        "mrr": 1.0 / first if first else 0.0,
    }


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--configs", default=",".join(CONFIGS), help="dipisah koma: " + ", ".join(CONFIGS))
    parser.add_argument("--llm", action="store_true", help="aktifkan ekspansi query via DeepSeek")
    parser.add_argument("--detail", action="store_true", help="tampilkan kasus yang gagal Hit@5")
    args = parser.parse_args()

    golden = [json.loads(line) for line in GOLDEN.read_text(encoding="utf-8").splitlines() if line.strip()]
    names = [c.strip() for c in args.configs.split(",")]
    metrics = ("hit@5", "recall@5", "recall@10", "mrr")

    print(f"{len(golden)} pertanyaan\n")
    header = f"{'konfigurasi':<12} {'kategori':<10} " + " ".join(f"{m:>9}" for m in metrics)
    print(header + "\n" + "-" * len(header))

    for name in names:
        per_cat: dict[str, list[dict]] = defaultdict(list)
        failures = []
        for g in golden:
            result = retrieve(g["query"], k=CHUNK_POOL, use_llm_expand=args.llm, **CONFIGS[name])
            ranked = [f"{s}:{a}" for s, a in result.ayat_keys()]
            s = score(ranked, set(g["expected"]))
            per_cat[g["kategori"]].append(s)
            per_cat["SEMUA"].append(s)
            if not s["hit@5"]:
                failures.append((g, ranked[:5]))

        for cat in sorted(per_cat, key=lambda c: (c == "SEMUA", c)):
            rows = per_cat[cat]
            avg = " ".join(f"{sum(r[m] for r in rows) / len(rows):>9.3f}" for m in metrics)
            print(f"{name:<12} {cat + f' ({len(rows)})':<10} {avg}")
        print()

        if args.detail and failures:
            print(f"  gagal Hit@5 [{name}]:")
            for g, top in failures:
                print(f"   #{g['id']:<3} {g['query'][:55]:<55} harap={g['expected'][:3]} dapat={top}")
            print()


if __name__ == "__main__":
    main()
