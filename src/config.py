import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"
RESOURCES = ROOT / "src" / "resources"

DB_PATH = DATA_PROCESSED / "quran.db"
LANCEDB_DIR = DATA_PROCESSED / "lancedb"
LANCE_TABLE = "chunks"
BM25_DIR = DATA_PROCESSED / "bm25"

APP_DB = ROOT / "data" / "app.db"  # akun & sesi login (terpisah dari data Qur'an yang bisa dibangun ulang)
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"  # true bila disajikan lewat HTTPS

EMBED_MODEL = os.getenv("EMBED_MODEL", "intfloat/multilingual-e5-base")
# Encoder query ringan (ONNX int8, tanpa torch) hasil `python -m src.index.export_onnx`.
ONNX_MODEL_DIR = ROOT / "data" / "models" / "e5-base-int8"
# auto: pakai ONNX bila tersedia, selain itu sentence-transformers | onnx | torch
EMBED_BACKEND = os.getenv("EMBED_BACKEND", "auto").lower()

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

TOTAL_SURAH = 114
TOTAL_AYAT = 6236
