"""Ubah data mentah (quran-json + metadata Tanzil) menjadi SQLite: data/processed/quran.db."""
import json
import re
import sqlite3

from src.config import DATA_PROCESSED, DB_PATH, TOTAL_SURAH
from src.ingest.download import QURAN_JSON_DIR, TANZIL_DIR

SCHEMA = """
DROP TABLE IF EXISTS surah;
DROP TABLE IF EXISTS ayat;
DROP TABLE IF EXISTS tafsir;
CREATE TABLE surah (
    no            INTEGER PRIMARY KEY,
    nama_latin    TEXT NOT NULL,
    nama_arab     TEXT NOT NULL,
    nama_tanzil   TEXT NOT NULL,
    arti          TEXT NOT NULL,
    jumlah_ayat   INTEGER NOT NULL,
    tempat_turun  TEXT NOT NULL
);
CREATE TABLE ayat (
    id            INTEGER PRIMARY KEY,   -- nomor urut global 1..6236
    surah_no      INTEGER NOT NULL REFERENCES surah(no),
    ayat_no       INTEGER NOT NULL,
    juz           INTEGER NOT NULL,
    teks_arab     TEXT NOT NULL,
    terjemahan_id TEXT NOT NULL,
    UNIQUE (surah_no, ayat_no)
);
CREATE TABLE tafsir (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    surah_no      INTEGER NOT NULL,
    ayat_no       INTEGER NOT NULL,
    sumber        TEXT NOT NULL,
    teks          TEXT NOT NULL,
    UNIQUE (surah_no, ayat_no, sumber)
);
"""


def clean(text: str) -> str:
    text = text.replace("\r\n", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def parse_tanzil_meta() -> tuple[dict[int, dict], list[tuple[int, int]]]:
    """Kembalikan ({surah_no: {tname, type, ayas}}, [(surah, ayat) awal tiap juz])."""
    js = (TANZIL_DIR / "quran-data.js").read_text(encoding="utf-8")

    sura_block = js.split("QuranData.Sura = [", 1)[1].split("];", 1)[0]
    rows = re.findall(r"\[(\d+), (\d+), \d+, \d+, '[^']*', \"([^\"]*)\", '(?:[^'\\]|\\.)*', '(\w+)'\]", sura_block)
    suras = {i: {"ayas": int(r[1]), "tname": r[2], "type": r[3]} for i, r in enumerate(rows, start=1)}

    juz_block = js.split("QuranData.Juz = [", 1)[1].split("];", 1)[0]
    juz_starts = [(int(s), int(a)) for s, a in re.findall(r"\[(\d+), (\d+)\]", juz_block)]
    return suras, juz_starts[:30]


def juz_of(surah_no: int, ayat_no: int, juz_starts: list[tuple[int, int]]) -> int:
    juz = 1
    for i, start in enumerate(juz_starts, start=1):
        if (surah_no, ayat_no) >= start:
            juz = i
    return juz


def main() -> None:
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    tanzil, juz_starts = parse_tanzil_meta()
    if len(tanzil) != TOTAL_SURAH or len(juz_starts) != 30:
        raise SystemExit(f"Metadata Tanzil tidak lengkap: {len(tanzil)} surah, {len(juz_starts)} juz")

    con = sqlite3.connect(DB_PATH)
    con.executescript(SCHEMA)

    global_id = 0
    for n in range(1, TOTAL_SURAH + 1):
        data = json.loads((QURAN_JSON_DIR / f"{n}.json").read_text(encoding="utf-8"))[str(n)]
        trans = data["translations"]["id"]
        tafsir = data["tafsir"]["id"]["kemenag"]["text"]
        tempat = "Makkiyah" if tanzil[n]["type"] == "Meccan" else "Madaniyah"

        con.execute(
            "INSERT INTO surah VALUES (?,?,?,?,?,?,?)",
            (n, data["name_latin"], data["name"], tanzil[n]["tname"], trans["name"],
             int(data["number_of_ayah"]), tempat),
        )
        for ayat_key in sorted(data["text"], key=int):
            a = int(ayat_key)
            global_id += 1
            con.execute(
                "INSERT INTO ayat VALUES (?,?,?,?,?,?)",
                (global_id, n, a, juz_of(n, a, juz_starts),
                 clean(data["text"][ayat_key]), clean(trans["text"][ayat_key])),
            )
            if tafsir.get(ayat_key, "").strip():
                con.execute(
                    "INSERT INTO tafsir (surah_no, ayat_no, sumber, teks) VALUES (?,?,?,?)",
                    (n, a, "Tafsir Kemenag", clean(tafsir[ayat_key])),
                )

    con.commit()
    counts = {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in ("surah", "ayat", "tafsir")}
    con.close()
    print(f"SQLite ditulis ke {DB_PATH}: {counts}")


if __name__ == "__main__":
    main()
