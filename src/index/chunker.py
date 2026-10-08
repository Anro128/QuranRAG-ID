"""Bangun tabel `chunks` di quran.db dari tabel ayat & tafsir.

- chunk ayat  : 1 ayat = 1 chunk, teks = "QS <surah> [<n>]:<a> — <terjemahan>"
- chunk tafsir: tafsir per ayat dipecah per paragraf, dikemas hingga ~MAX_WORDS kata

Teks Arab tidak masuk ke chunk; ia hanya ditampilkan dari tabel ayat.
"""
import re
import sqlite3

from src.config import DB_PATH

MAX_WORDS = 250  # ~400 token untuk e5 (bahasa Indonesia ±1,5 token/kata)

SCHEMA = """
DROP TABLE IF EXISTS chunks;
CREATE TABLE chunks (
    id        INTEGER PRIMARY KEY,
    tipe      TEXT NOT NULL,          -- 'ayat' | 'tafsir'
    surah_no  INTEGER NOT NULL,
    ayat_no   INTEGER NOT NULL,
    bagian    INTEGER NOT NULL,       -- urutan potongan tafsir (0 untuk ayat)
    teks      TEXT NOT NULL
);
CREATE INDEX idx_chunks_ref ON chunks(surah_no, ayat_no);
"""


def split_words(text: str, max_words: int) -> list[str]:
    words = text.split()
    return [" ".join(words[i:i + max_words]) for i in range(0, len(words), max_words)]


def pack_paragraphs(text: str, max_words: int = MAX_WORDS) -> list[str]:
    """Gabungkan paragraf berurutan sampai batas kata; paragraf terlalu panjang dipecah per kata."""
    pieces: list[str] = []
    for para in re.split(r"\n\s*\n", text):
        para = " ".join(para.split())
        if para:
            pieces.extend(split_words(para, max_words))

    chunks, current, size = [], [], 0
    for piece in pieces:
        n = len(piece.split())
        if current and size + n > max_words:
            chunks.append("\n".join(current))
            current, size = [], 0
        current.append(piece)
        size += n
    if current:
        chunks.append("\n".join(current))
    return chunks


def ayat_header(nama_latin: str, surah_no: int, ayat_no: int) -> str:
    return f"QS {nama_latin} [{surah_no}]:{ayat_no}"


def main() -> None:
    con = sqlite3.connect(DB_PATH)
    con.executescript(SCHEMA)
    rows = []

    for surah_no, ayat_no, nama, terjemahan in con.execute(
        "SELECT a.surah_no, a.ayat_no, s.nama_latin, a.terjemahan_id "
        "FROM ayat a JOIN surah s ON s.no = a.surah_no ORDER BY a.id"
    ):
        rows.append(("ayat", surah_no, ayat_no, 0, f"{ayat_header(nama, surah_no, ayat_no)} — {terjemahan}"))

    for surah_no, ayat_no, nama, teks in con.execute(
        "SELECT t.surah_no, t.ayat_no, s.nama_latin, t.teks "
        "FROM tafsir t JOIN surah s ON s.no = t.surah_no ORDER BY t.surah_no, t.ayat_no"
    ):
        header = f"Tafsir {ayat_header(nama, surah_no, ayat_no)}"
        for i, part in enumerate(pack_paragraphs(teks)):
            rows.append(("tafsir", surah_no, ayat_no, i, f"{header} — {part}"))

    con.executemany("INSERT INTO chunks (tipe, surah_no, ayat_no, bagian, teks) VALUES (?,?,?,?,?)", rows)
    con.commit()
    stats = dict(con.execute("SELECT tipe, COUNT(*) FROM chunks GROUP BY tipe"))
    con.close()
    print(f"chunks: {stats}")


if __name__ == "__main__":
    main()
