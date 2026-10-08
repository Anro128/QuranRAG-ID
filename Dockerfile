# syntax=docker/dockerfile:1
#
# Image runtime QuranRAG-ID: tanpa torch (encoder query ONNX int8), muat di VPS 1 GB.
# Data (data/processed, data/models) dan akun (data/app.db) TIDAK dimasukkan ke image;
# folder data/ di-mount sebagai volume (lihat docker-compose.yml).

# ---- 1. build frontend --------------------------------------------------------
FROM node:22-alpine AS web
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY web/ ./
RUN npm run build

# ---- 2. dependensi Python (hanya runtime dari pyproject.toml) -----------------
FROM python:3.11-slim AS deps
WORKDIR /build
COPY pyproject.toml ./
RUN python -m venv /opt/venv \
 && /opt/venv/bin/pip install --no-cache-dir --upgrade pip \
 && python -c "import tomllib; print('\n'.join(tomllib.load(open('pyproject.toml', 'rb'))['project']['dependencies']))" > requirements.txt \
 && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

# ---- 3. image akhir -------------------------------------------------------------
FROM python:3.11-slim
ENV PATH=/opt/venv/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    EMBED_BACKEND=onnx
WORKDIR /app

# UID 1000 = user pertama di kebanyakan VPS Linux, agar bisa menulis data/app.db di volume
RUN useradd --create-home --uid 1000 app
COPY --from=deps /opt/venv /opt/venv
COPY src/ src/
COPY --from=web /web/dist web/dist

USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=3)"

# satu worker: tiap worker memuat model + indeks sendiri (±500 MB)
CMD ["uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "8000"]
