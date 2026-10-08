"""Validasi quran.db: jumlah surah/ayat, kecocokan jumlah ayat per surah dengan Tanzil,
dan tidak ada teks kosong. Keluar dengan kode 1 jika ada kegagalan.

Catatan: teks Arab Kemenag dan Tanzil memakai rasm/penulisan berbeda, sehingga
validasi silang dilakukan pada struktur (surah, ayat), bukan kecocokan karakter.
"""
import sqlite3
import sys

from src.config import DB_PATH, TOTAL_AYAT, TOTAL_SURAH
from src.ingest.download import TANZIL_DIR
from src.ingest.normalize import parse_tanzil_meta


def main() -> int:
    con = sqlite3.connect(DB_PATH)
    errors: list[str] = []

    n_surah = con.execute("SELECT COUNT(*) FROM surah").fetchone()[0]
    n_ayat = con.execute("SELECT COUNT(*) FROM ayat").fetchone()[0]
    if n_surah != TOTAL_SURAH:
        errors.append(f"jumlah surah {n_surah} != {TOTAL_SURAH}")
    if n_ayat != TOTAL_AYAT:
        errors.append(f"jumlah ayat {n_ayat} != {TOTAL_AYAT}")

    tanzil, _ = parse_tanzil_meta()
    per_surah = dict(con.execute("SELECT surah_no, COUNT(*) FROM ayat GROUP BY surah_no"))
    declared = dict(con.execute("SELECT no, jumlah_ayat FROM surah"))
    for n in range(1, TOTAL_SURAH + 1):
        if per_surah.get(n) != tanzil[n]["ayas"] or declared.get(n) != tanzil[n]["ayas"]:
            errors.append(f"surah {n}: db={per_surah.get(n)} deklarasi={declared.get(n)} tanzil={tanzil[n]['ayas']}")

    tanzil_keys = set()
    for line in (TANZIL_DIR / "id.indonesian.txt").read_text(encoding="utf-8").splitlines():
        parts = line.split("|", 2)
        if len(parts) == 3 and parts[0].isdigit():
            tanzil_keys.add((int(parts[0]), int(parts[1])))
    db_keys = set(con.execute("SELECT surah_no, ayat_no FROM ayat"))
    if db_keys != tanzil_keys:
        errors.append(f"pasangan (surah, ayat) beda dengan Tanzil: {len(db_keys ^ tanzil_keys)} selisih")

    empty = con.execute(
        "SELECT COUNT(*) FROM ayat WHERE TRIM(teks_arab)='' OR TRIM(terjemahan_id)=''"
    ).fetchone()[0]
    if empty:
        errors.append(f"{empty} ayat dengan teks Arab/terjemahan kosong")

    n_tafsir = con.execute("SELECT COUNT(*) FROM tafsir").fetchone()[0]
    juz_range = con.execute("SELECT MIN(juz), MAX(juz) FROM ayat").fetchone()
    con.close()

    print(f"surah={n_surah} ayat={n_ayat} tafsir={n_tafsir} juz={juz_range}")
    if n_tafsir < TOTAL_AYAT:
        print(f"PERINGATAN: {TOTAL_AYAT - n_tafsir} ayat tanpa tafsir")
    if errors:
        print("GAGAL:\n- " + "\n- ".join(errors))
        return 1
    print("VALID: semua cek lolos")
    return 0


if __name__ == "__main__":
    sys.exit(main())
