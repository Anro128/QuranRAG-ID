"""Pengenal referensi ayat dalam query bahasa Indonesia.

Mendukung, misalnya:
    "QS 2:255", "2:255-257", "QS. Al-Mulk (67): 2", "Al-Baqarah ayat 286",
    "albaqarah 255", "surat yasin ayat 1", "al ikhlas 1-4", "ayat kursi",
serta penyebutan surah tanpa ayat ("isi surat al-mulk") sebagai filter surah.
"""
import json
import re
import sqlite3
from dataclasses import dataclass
from functools import lru_cache

from rapidfuzz import fuzz, process

from src.config import DB_PATH, RESOURCES

MAX_RANGE = 20
FUZZY_CUTOFF = 88
RANGE_SEP = r"(?:-|–|sampai|s/d|hingga|sd)"
FILLER = {"ayat", "ayah", "ay", "ke", "surat", "surah", "qs", "q", "s", "no", "nomor", "dalam", "di", "isi"}
ARTICLE = re.compile(r"^(?:al|an|ar|as|asy|ash|at|az|ad|adh|adz|ath)[\s-]+")


@dataclass(frozen=True)
class Ref:
    surah_no: int
    start: int
    end: int

    def label(self) -> str:
        return f"QS {self.surah_no}:{self.start}" + (f"-{self.end}" if self.end != self.start else "")


@dataclass
class ParsedQuery:
    refs: list[Ref]
    surah_filter: int | None = None


def norm_name(text: str) -> str:
    """Kunci fonetik kasar agar ejaan Kemenag, Tanzil, dan ketikan bebas bertemu."""
    s = re.sub(r"[’'`‘ʼ]", "", text.lower())
    s = re.sub(r"[^a-z]+", "", s)
    for a, b in (("sy", "s"), ("sh", "s"), ("ts", "s"), ("th", "t"), ("dz", "z"), ("dh", "d"),
                 ("kh", "k"), ("gh", "g"), ("q", "k"), ("oo", "u"), ("ee", "i"),
                 ("w", "u"), ("y", "i"), ("e", "i"), ("o", "u")):
        s = s.replace(a, b)
    s = re.sub(r"(.)\1+", r"\1", s)
    return re.sub(r"h$", "", s)


@lru_cache(maxsize=1)
def surah_info() -> dict[int, tuple[str, int]]:
    con = sqlite3.connect(DB_PATH)
    info = {n: (nama, jml) for n, nama, jml in con.execute("SELECT no, nama_latin, jumlah_ayat FROM surah")}
    con.close()
    return info


@lru_cache(maxsize=1)
def _aliases() -> tuple[dict[str, int], dict[str, tuple[int, int, int]]]:
    con = sqlite3.connect(DB_PATH)
    names = list(con.execute("SELECT no, nama_latin, nama_tanzil FROM surah"))
    con.close()

    keys: dict[str, int] = {}
    for no, *variants in names:
        for v in variants:
            keys[norm_name(v)] = no
            keys[norm_name(ARTICLE.sub("", v.lower()))] = no
    extra = json.loads((RESOURCES / "alias_surah.json").read_text(encoding="utf-8"))
    for alias, no in extra["surah"].items():
        keys[norm_name(alias)] = no
    special = {k: tuple(v) for k, v in extra["khusus"].items()}
    return keys, special


def match_surah(phrase: str) -> int | None:
    key = norm_name(phrase)
    if len(key) < 2:
        return None
    keys, _ = _aliases()
    if key in keys:
        return keys[key]
    if len(key) <= 4:  # nama pendek (nas, jin, tin) hanya boleh cocok persis
        return None
    best = process.extractOne(key, keys.keys(), scorer=fuzz.ratio, score_cutoff=FUZZY_CUTOFF)
    return keys[best[0]] if best else None


def _make_ref(surah_no: int, start: int, end: int | None) -> Ref | None:
    info = surah_info().get(surah_no)
    if not info or start < 1 or start > info[1]:
        return None
    end = min(max(end or start, start), info[1], start + MAX_RANGE - 1)
    return Ref(surah_no, start, end)


def _surah_before(words: list[str]) -> int | None:
    while words and words[-1] in FILLER:
        words = words[:-1]
    for n in range(min(4, len(words)), 0, -1):
        window = words[-n:]
        if window[0] in FILLER:
            continue
        if (no := match_surah(" ".join(window))) is not None:
            return no
    return None


def parse(query: str) -> ParsedQuery:
    q = query.lower()
    refs: list[Ref] = []
    consumed: list[tuple[int, int]] = []

    _, special = _aliases()
    simple = re.sub(r"[^a-z0-9 ]+", " ", q)
    simple = " ".join(simple.split())
    for phrase, (s, a, b) in special.items():
        if phrase in simple and (ref := _make_ref(s, a, b)):
            refs.append(ref)

    # 1) numerik: 2:255, [2]:255, (67): 2, 2:255-257
    for m in re.finditer(rf"(?<!\d)(\d{{1,3}})\s*[\])]?\s*:\s*(\d{{1,3}})(?:\s*{RANGE_SEP}\s*(\d{{1,3}}))?", q):
        if ref := _make_ref(int(m[1]), int(m[2]), int(m[3]) if m[3] else None):
            refs.append(ref)
            consumed.append(m.span())

    # 2) nama surah diikuti nomor ayat: "al-baqarah ayat 255", "an nisa 3", "al ikhlas 1-4"
    for m in re.finditer(rf"(?<![\d:])(\d{{1,3}})(?:\s*{RANGE_SEP}\s*(\d{{1,3}}))?(?![\d:])", q):
        if any(a <= m.start() < b for a, b in consumed):
            continue
        before = re.sub(r"[^a-z'’\- ]+", " ", q[max(0, m.start() - 60):m.start()])
        words = re.sub(r"[-'’]", " ", before).split()
        if (no := _surah_before(words)) and (ref := _make_ref(no, int(m[1]), int(m[2]) if m[2] else None)):
            refs.append(ref)

    # 3) surah tanpa ayat: "surat al-mulk" -> filter
    surah_filter = None
    if not refs:
        if m := re.search(r"\b(?:surah|surat|qs)\.?\s+([a-z'’\- ]{2,40})", q):
            words = re.sub(r"[-'’]", " ", m[1]).split()
            for n in range(min(4, len(words)), 0, -1):
                if (no := match_surah(" ".join(words[:n]))) is not None:
                    surah_filter = no
                    break

    return ParsedQuery(refs=list(dict.fromkeys(refs)), surah_filter=surah_filter)
