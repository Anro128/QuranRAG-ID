"""Validasi sitasi dan pembersihan jawaban LLM.

- Setiap sitasi [QS s:a] / [QS s:a-b] harus menunjuk ayat yang ada di konteks.
  Sitasi yang tidak terverifikasi diganti penanda dan dilaporkan.
- Teks berhuruf Arab dihapus dari jawaban: teks Arab hanya boleh berasal dari database.
"""
import re
from dataclasses import dataclass, field

CITATION = re.compile(r"\[\s*QS\.?\s*(\d{1,3})\s*:\s*(\d{1,3})(?:\s*[-–]\s*(\d{1,3}))?\s*\]", re.IGNORECASE)
ARABIC_RUN = re.compile(r"[؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿]"
                        r"[؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿\s]*")
UNVERIFIED = "[sitasi tidak terverifikasi]"


@dataclass
class Validated:
    text: str
    cited: list[tuple[int, int]] = field(default_factory=list)   # ayat sah yang dikutip, urut kemunculan
    invalid: list[str] = field(default_factory=list)              # sitasi yang dibuang
    arabic_removed: bool = False


def validate(text: str, allowed: set[tuple[int, int]]) -> Validated:
    result = Validated(text="")
    cited: list[tuple[int, int]] = []

    def check(m: re.Match) -> str:
        s, a = int(m[1]), int(m[2])
        b = int(m[3]) if m[3] else a
        keys = [(s, x) for x in range(a, max(a, b) + 1)]
        if keys and all(k in allowed for k in keys):
            cited.extend(keys)
            return f"[QS {s}:{a}" + (f"-{b}" if b != a else "") + "]"
        result.invalid.append(m[0])
        return UNVERIFIED

    text = CITATION.sub(check, text)
    cleaned = ARABIC_RUN.sub("", text)
    result.arabic_removed = cleaned != text
    result.text = re.sub(r"[ \t]{2,}", " ", cleaned).strip()
    result.cited = list(dict.fromkeys(cited))
    return result
