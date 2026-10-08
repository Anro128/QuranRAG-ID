"""Akses baca ke quran.db: data ayat untuk ditampilkan dan chunk untuk referensi langsung."""
import sqlite3
from dataclasses import dataclass

from src.config import DB_PATH
from src.retrieval.hybrid import Hit


@dataclass
class Ayat:
    surah_no: int
    ayat_no: int
    nama_surah: str
    juz: int
    teks_arab: str
    terjemahan: str
    tafsir: str | None

    @property
    def label(self) -> str:
        return f"QS {self.nama_surah} [{self.surah_no}]:{self.ayat_no}"


def _connect() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH)


def get_ayat(keys: list[tuple[int, int]]) -> list[Ayat]:
    """Ambil ayat (urutan sesuai `keys`, duplikat diabaikan) beserta tafsirnya."""
    keys = list(dict.fromkeys(keys))
    if not keys:
        return []
    con = _connect()
    rows = {}
    for s, a in keys:
        r = con.execute(
            "SELECT a.surah_no, a.ayat_no, s.nama_latin, a.juz, a.teks_arab, a.terjemahan_id, t.teks "
            "FROM ayat a JOIN surah s ON s.no = a.surah_no "
            "LEFT JOIN tafsir t ON t.surah_no = a.surah_no AND t.ayat_no = a.ayat_no "
            "WHERE a.surah_no = ? AND a.ayat_no = ?", (s, a)
        ).fetchone()
        if r:
            rows[(s, a)] = Ayat(*r)
    con.close()
    return [rows[k] for k in keys if k in rows]


def chunks_for_refs(refs, with_tafsir: bool = True, max_tafsir_parts: int = 2) -> list[Hit]:
    """Chunk ayat (dan potongan awal tafsirnya) untuk referensi yang disebut langsung di query."""
    con = _connect()
    hits: list[Hit] = []
    for ref in refs:
        rows = con.execute(
            "SELECT id, tipe, surah_no, ayat_no, teks FROM chunks "
            "WHERE surah_no = ? AND ayat_no BETWEEN ? AND ? AND (tipe = 'ayat' OR (? AND bagian < ?)) "
            "ORDER BY ayat_no, tipe, bagian",
            (ref.surah_no, ref.start, ref.end, int(with_tafsir), max_tafsir_parts),
        ).fetchall()
        hits.extend(Hit(*r, score=1.0) for r in rows)
    con.close()
    return hits
