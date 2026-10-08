"""Encoder query e5 berbasis ONNX Runtime (int8), tanpa torch/transformers.

Meniru pipeline sentence-transformers untuk multilingual-e5: tokenisasi -> last_hidden_state
-> mean pooling dengan attention mask -> normalisasi L2.

Tokenisasi memakai `sentencepiece` langsung (±40 MB RAM) alih-alih HF `tokenizers`
(±250 MB RAM untuk kosakata XLM-R 250 ribu token). ID-nya identik dengan tokenizer HF
(diverifikasi pada 3.072 teks: korpus, golden set, dan kasus tepi).
"""
import os
from pathlib import Path

import numpy as np
import onnxruntime as ort
import sentencepiece as spm

MAX_TOKENS = 512
MAX_THREADS = 4  # query pendek: thread tambahan tidak mempercepat, hanya menambah memori


def default_threads() -> int:
    """Jumlah core yang boleh dipakai proses ini (menghormati cpuset Docker), maksimal MAX_THREADS.

    Mode otomatis ONNX Runtime menghitung semua core fisik host, sehingga di container yang
    dibatasi ia membuat thread berlebih dan gagal mengatur affinity.
    """
    try:
        n = len(os.sched_getaffinity(0))
    except AttributeError:  # Windows/macOS
        n = os.cpu_count() or 1
    return max(1, min(n, MAX_THREADS))
# Pemetaan fairseq XLM-R: <s>=0, <pad>=1, </s>=2, <unk>=3; ID sentencepiece digeser +1, unk sentencepiece (0) -> 3.
BOS, EOS, UNK, FAIRSEQ_OFFSET = 0, 2, 3, 1


class OnnxEncoder:
    def __init__(self, model_dir: Path):
        self.sp = spm.SentencePieceProcessor(model_file=str(model_dir / "sentencepiece.bpe.model"))

        opts = ort.SessionOptions()
        opts.intra_op_num_threads = int(os.getenv("ORT_THREADS", "0")) or default_threads()  # 0 = otomatis
        opts.inter_op_num_threads = 1
        opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        # hemat RAM: matikan arena memori agar buffer aktivasi dilepas setelah tiap query
        opts.enable_cpu_mem_arena = False
        self.session = ort.InferenceSession(str(model_dir / "model.onnx"), opts, providers=["CPUExecutionProvider"])

    def token_ids(self, text: str) -> list[int]:
        ids = [i + FAIRSEQ_OFFSET if i != 0 else UNK for i in self.sp.encode(text)]
        return [BOS, *ids[: MAX_TOKENS - 2], EOS]

    def encode(self, text: str) -> np.ndarray:
        ids = np.array([self.token_ids(text)], dtype=np.int64)
        mask = np.ones_like(ids)
        (hidden,) = self.session.run(["last_hidden_state"], {"input_ids": ids, "attention_mask": mask})
        vec = hidden[0].mean(axis=0)  # mean pooling (tanpa padding, semua token dihitung)
        return vec / np.linalg.norm(vec)
