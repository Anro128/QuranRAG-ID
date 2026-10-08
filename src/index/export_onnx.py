"""Siapkan encoder query ringan: e5-base versi ONNX dengan bobot int8 (tanpa torch saat runtime).

Mengunduh `onnx/model.onnx` (presisi penuh) dan `sentencepiece.bpe.model` dari repo Hugging Face model,
lalu mengkuantisasi bobot ke int8 secara dinamis. Hasilnya portabel untuk CPU x86/ARM
mana pun, berbeda dengan `model_qint8_avx512_vnni.onnx` di repo yang ditujukan khusus
CPU ber-AVX512-VNNI.

Jalankan sekali di mesin build (butuh dependensi `.[index]`), lalu salin
`data/models/e5-base-int8/` ke server:
    python -m src.index.export_onnx
"""
import shutil

from huggingface_hub import hf_hub_download
from onnxruntime.quantization import QuantType, quantize_dynamic

from src.config import EMBED_MODEL, ONNX_MODEL_DIR

FILES = ["onnx/model.onnx", "onnx/sentencepiece.bpe.model"]


def main() -> None:
    ONNX_MODEL_DIR.mkdir(parents=True, exist_ok=True)
    paths = {f: hf_hub_download(EMBED_MODEL, f) for f in FILES}

    shutil.copyfile(paths["onnx/sentencepiece.bpe.model"], ONNX_MODEL_DIR / "sentencepiece.bpe.model")
    out = ONNX_MODEL_DIR / "model.onnx"
    # QUInt8 (asimetris) paling dekat ke model asli: cosine rata-rata 0,985 vs 0,980 (QInt8),
    # 0,928 (QInt8 per-channel), 0,927 (model_qint8_avx512_vnni dari repo) pada golden set.
    quantize_dynamic(paths["onnx/model.onnx"], out, weight_type=QuantType.QUInt8)

    size = out.stat().st_size / 2**20
    print(f"Encoder ONNX int8 ditulis ke {ONNX_MODEL_DIR} ({size:.0f} MB)")


if __name__ == "__main__":
    main()
