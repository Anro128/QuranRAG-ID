"""Embedding query untuk pencarian dense.

Backend (EMBED_BACKEND di .env):
- auto  : ONNX int8 bila data/models/e5-base-int8 ada, selain itu sentence-transformers
- onnx  : wajib ONNX (server ringan tanpa torch, mis. VPS 1 GB)
- torch : sentence-transformers presisi penuh (butuh dependensi `.[index]`)

Vektor passage di LanceDB dibuat dengan model yang sama (presisi penuh); encoder ONNX
hanya versi int8 dari model tersebut, sehingga ruang vektornya kompatibel.
"""
from collections.abc import Callable
from functools import lru_cache

from src.config import EMBED_BACKEND, ONNX_MODEL_DIR


def onnx_available() -> bool:
    return all((ONNX_MODEL_DIR / f).exists() for f in ("model.onnx", "sentencepiece.bpe.model"))


def active_backend() -> str:
    if EMBED_BACKEND == "onnx" or (EMBED_BACKEND == "auto" and onnx_available()):
        return "onnx"
    return "torch"


@lru_cache(maxsize=1)
def _encoder() -> Callable[[str], list[float]]:
    if active_backend() == "onnx":
        if not onnx_available():
            raise RuntimeError(f"Model ONNX tidak ditemukan di {ONNX_MODEL_DIR}. Jalankan: python -m src.index.export_onnx")
        from src.index.onnx_encoder import OnnxEncoder

        enc = OnnxEncoder(ONNX_MODEL_DIR)
        return lambda text: enc.encode(text).tolist()

    from src.index.embed import get_model  # impor lambat: torch hanya dimuat bila diperlukan

    model = get_model()
    return lambda text: model.encode(text, normalize_embeddings=True).tolist()


@lru_cache(maxsize=256)
def _embed_cached(query: str) -> tuple[float, ...]:
    return tuple(_encoder()(f"query: {query}"))


def embed_query(query: str) -> list[float]:
    return list(_embed_cached(query))
