"""Unduh dataset publik ke data/raw/ (sekali saja; file yang sudah ada dilewati).

Sumber:
- rioastamal/quran-json : Arab, latin, terjemahan & Tafsir Kemenag per surah
- Tanzil.net            : terjemahan id.indonesian + metadata surah/juz (validasi silang)
"""
import argparse
from concurrent.futures import ThreadPoolExecutor

import requests
from tqdm import tqdm

from src.config import DATA_RAW, TOTAL_SURAH

QURAN_JSON_URL = "https://raw.githubusercontent.com/rioastamal/quran-json/master/surah/{n}.json"
TANZIL_TRANS_URL = "https://tanzil.net/trans/?transID=id.indonesian&type=txt-2"
TANZIL_META_URL = "https://tanzil.net/res/text/metadata/quran-data.js"

QURAN_JSON_DIR = DATA_RAW / "quran-json"
TANZIL_DIR = DATA_RAW / "tanzil"


def _fetch(url: str, dest, force: bool) -> None:
    if dest.exists() and dest.stat().st_size > 0 and not force:
        return
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    dest.write_bytes(resp.content)


def main(force: bool = False) -> None:
    QURAN_JSON_DIR.mkdir(parents=True, exist_ok=True)
    TANZIL_DIR.mkdir(parents=True, exist_ok=True)

    jobs = [(QURAN_JSON_URL.format(n=n), QURAN_JSON_DIR / f"{n}.json") for n in range(1, TOTAL_SURAH + 1)]
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(tqdm(pool.map(lambda j: _fetch(*j, force), jobs), total=len(jobs), desc="quran-json"))

    _fetch(TANZIL_TRANS_URL, TANZIL_DIR / "id.indonesian.txt", force)
    _fetch(TANZIL_META_URL, TANZIL_DIR / "quran-data.js", force)
    print(f"Selesai. Data di {DATA_RAW}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="unduh ulang semua file")
    main(parser.parse_args().force)
