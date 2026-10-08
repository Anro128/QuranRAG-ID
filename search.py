"""CLI uji retrieval (lewat router: referensi langsung atau pencarian hybrid).

Contoh:
    python search.py "sabar menghadapi musibah"
    python search.py "Al-Baqarah ayat 255"
    python search.py "riba" --mode bm25 -k 5 --no-llm
"""
import argparse
import sys

from src.retrieval.router import retrieve


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("query")
    parser.add_argument("-k", type=int, default=8)
    parser.add_argument("--mode", choices=["hybrid", "dense", "bm25"], default="hybrid")
    parser.add_argument("--no-llm", action="store_true", help="tanpa ekspansi query via DeepSeek")
    args = parser.parse_args()

    result = retrieve(args.query, args.k, args.mode, use_llm_expand=not args.no_llm)
    print(f"route={result.route}  refs={[r.label() for r in result.refs]}  filter_surah={result.surah_filter}")
    if result.bm25_query and result.bm25_query != args.query:
        print(f"bm25_query={result.bm25_query!r}")
    print()
    for i, hit in enumerate(result.hits, start=1):
        teks = hit.teks if len(hit.teks) <= 220 else hit.teks[:220] + "…"
        print(f"{i:>2}. [{hit.tipe:6}] QS {hit.surah_no}:{hit.ayat_no}  ({hit.score:.4f})\n    {teks}\n")


if __name__ == "__main__":
    main()
