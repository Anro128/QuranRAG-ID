# QuranRAG-ID

[English](README.md) | **Bahasa Indonesia**

Tanya-jawab Al-Qur'an berbahasa Indonesia berbasis RAG (Retrieval-Augmented Generation).
Setiap jawaban mengutip ayat sumbernya (`[QS surah:ayat]`), dan teks Arab selalu diambil dari
database, tidak pernah dibuat oleh AI.

## Fitur

- **Pencarian hybrid**: embedding `multilingual-e5-base` + BM25 berstemmer Indonesia, digabung dengan RRF.
  Saat runtime, encoder query memakai ONNX int8, jadi server tidak butuh torch.
- **Referensi langsung**: `QS 2:255`, `Al-Baqarah ayat 255`, `albaqarah 255`, `ayat kursi`, `surat yasin ayat 1`.
- **Normalisasi istilah** ke ejaan Kemenag (`sholat` → `salat`, `bunga` → `riba`, dst.).
- **Jawaban AI via DeepSeek** dengan validasi sitasi: sitasi ke ayat di luar sumber otomatis ditandai.
- **Login** username + password; riwayat chat tidak disimpan.
- Tetap bisa dipakai sebagai mesin pencari ayat tanpa API key.

## Prasyarat

| | Untuk membangun data & indeks | Untuk menjalankan server |
|---|---|---|
| Perangkat lunak | Python 3.11+, Node.js 20+ | Docker + Compose (atau Python 3.11+ tanpa Docker) |
| RAM | ±8 GB | 1 GB + swap 1–2 GB (aplikasi ±650 MiB, puncak ±830 MB) |
| Disk | ±5 GB (torch, model, data) | ±1,5 GB (image ±1 GB + data ±350 MB) |
| Lainnya | koneksi internet untuk unduh dataset & model | API key [DeepSeek](https://platform.deepseek.com) (opsional) |

Data dan indeks cukup dibangun **sekali** di laptop/PC, lalu hasilnya dipakai oleh server.

## Instalasi

Perintah di bawah memakai bash (Linux/macOS/Git Bash). Untuk Windows PowerShell, lihat catatan di tiap langkah.

### 1. Ambil kode dan siapkan virtualenv

```bash
git clone https://github.com/Anro128/QuranRAG-ID.git
cd QuranRAG-ID
python -m venv .venv
source .venv/bin/activate          # PowerShell: .venv\Scripts\Activate.ps1
```

### 2. Pasang dependensi

```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -e ".[index]"          # runtime + alat build (sentence-transformers, onnx)
```

> Di server yang hanya menjalankan aplikasi, cukup `pip install -e .` (tanpa torch). Lihat [Deploy ke VPS](#deploy-ke-vps-docker).

### 3. Konfigurasi

```bash
cp .env.example .env               # PowerShell: Copy-Item .env.example .env
```

Isi minimal `DEEPSEEK_API_KEY`. Daftar lengkap variabel ada di [Konfigurasi](#konfigurasi).

### 4. Bangun data dan indeks

Jalankan berurutan (total ±1 jam, sebagian besar untuk embedding):

```bash
python -m src.ingest.download      # unduh dataset publik ke data/raw/
python -m src.ingest.normalize     # bangun data/processed/quran.db
python -m src.ingest.validate      # cek 114 surah & 6.236 ayat, cocok dengan Tanzil
python -m src.index.chunker        # pecah ayat + tafsir menjadi chunk
python -m src.index.bm25_index     # indeks BM25
python -m src.index.embed          # embedding ke LanceDB (±30–60 menit di CPU)
python -m src.index.export_onnx    # encoder query ONNX int8 -> data/models/e5-base-int8/
```

### 5. Build frontend

```bash
cd web
npm install
npm run build                      # hasil di web/dist/, dilayani langsung oleh backend
cd ..
```

### 6. Buat akun

Tidak ada pendaftaran publik; akun dibuat lewat CLI (password minimal 8 karakter, ditanyakan secara interaktif):

```bash
python -m src.auth create-user <username>
```

## Menjalankan

```bash
uvicorn src.api:app --port 8000
```

Buka http://localhost:8000 lalu login.

### Mode pengembangan

Untuk mengubah frontend dengan hot reload, jalankan dua terminal. Request `/api` dari Vite diteruskan ke port 8000.

```bash
uvicorn src.api:app --reload --port 8000     # terminal 1: backend
cd web && npm run dev                        # terminal 2: frontend -> http://localhost:5173
```

Setelah selesai mengubah frontend, jalankan `npm run build` agar perubahan ikut tersaji di port 8000.

### Kelola akun

| Perintah | Fungsi |
|---|---|
| `python -m src.auth create-user <username>` | buat akun |
| `python -m src.auth passwd <username>` | ganti password (semua sesi akun itu ikut dikeluarkan) |
| `python -m src.auth delete-user <username>` | hapus akun |
| `python -m src.auth list-users` | daftar akun |

### Alat bantu

```bash
python search.py "sabar menghadapi musibah"   # uji pencarian dari terminal
python -m eval.run_eval --detail              # evaluasi pencarian atas golden set (66 pertanyaan)
python -m eval.run_eval --configs hybrid+sin --llm   # idem, dengan ekspansi kata kunci via DeepSeek
```

## Deploy ke VPS (Docker)

Image Docker sudah berisi backend **dan** frontend (di-build di dalam image), tanpa torch.
Yang tidak masuk image adalah folder `data/` (database, indeks, model ONNX, akun); folder ini
di-mount sebagai volume.

### 1. Siapkan VPS

Pasang Docker Engine + Compose plugin, lalu ambil kode:

```bash
git clone https://github.com/Anro128/QuranRAG-ID.git
cd QuranRAG-ID
cp .env.example .env               # isi DEEPSEEK_API_KEY
```

### 2. Kirim data dari mesin build

`data/` tidak ada di git. Dari mesin build (mis. WSL), kirim hasil langkah [Bangun data dan indeks](#4-bangun-data-dan-indeks):

```bash
rsync -avzR --progress --exclude 'api.log' data/processed data/models <host-vps>:~/QuranRAG-ID/
```

Ganti `<host-vps>` dengan alias SSH atau `user@ip`, dan sesuaikan path tujuannya dengan lokasi clone di VPS.

### 3. Build dan jalankan

```bash
docker compose up -d --build
docker compose exec app python -m src.auth create-user <username>
```

Container hanya mendengarkan di `127.0.0.1:8001`; akses publik lewat reverse proxy di depannya
(contoh konfigurasi Nginx ada di [deploy/nginx/](deploy/nginx/)). Bila disajikan lewat HTTPS, set `COOKIE_SECURE=true`.
Cek dari VPS: `curl http://127.0.0.1:8001/api/health`.

### Perintah sehari-hari

| Perintah | Fungsi |
|---|---|
| `docker compose logs -f app` | lihat log |
| `docker compose ps` | status & health container |
| `docker compose restart app` | restart (mis. setelah mengubah `.env`) |
| `git pull && docker compose up -d --build` | update ke kode terbaru |
| `docker compose exec app python -m src.auth <perintah>` | kelola akun (lihat [Kelola akun](#kelola-akun)) |
| `docker compose down` | hentikan |

### Catatan

- **Contoh konfigurasi Nginx** ([deploy/nginx/](deploy/nginx/)) sudah mematikan buffering untuk `/api/chat` agar
  jawaban mengalir bertahap, dan menimpa `X-Forwarded-For` dengan IP asli agar pembatasan login per IP
  tidak bisa diakali. Container mempercayai header ini (`FORWARDED_ALLOW_IPS` di `docker-compose.yml`)
  karena port-nya hanya terbuka di localhost.
- **Akses langsung lewat IP** (`http://IP:8001`, tanpa reverse proxy): ubah port di `docker-compose.yml` menjadi `"8001:8000"`, set
  `COOKIE_SECURE=false` (kalau `true`, login tidak tersimpan lewat HTTP), dan buka port 8001 di firewall Azure.
  Port yang dipublikasikan Docker **tidak** tunduk pada aturan `ufw`. Kembalikan setelah selesai menguji.
- **Memori**: container memakai ±650 MiB (puncak ±830 MB, terukur dengan 1 vCPU). Di VPS 1 GB aktifkan
  swap 1–2 GB, karena sistem operasi dan Docker sendiri juga butuh ±250 MB.
- **Satu worker**: image menjalankan satu proses uvicorn. Jangan menambah `--workers`, karena tiap worker
  memuat model dan indeks sendiri. Satu worker tetap melayani banyak pengguna bersamaan karena tiap request
  berjalan di thread terpisah dan sebagian besar waktunya menunggu respons DeepSeek.
- **Izin tulis**: container berjalan sebagai UID 1000 dan menulis `data/app.db`. Bila user VPS Anda bukan
  UID 1000, jalankan `sudo chown -R 1000:1000 data`.

### Tanpa Docker

Bisa juga langsung dengan Python di VPS: salin juga `web/dist/`, lalu `pip install -e .` (hanya dependensi
runtime) dan `uvicorn src.api:app --host 127.0.0.1 --port 8000`, dengan catatan yang sama soal satu worker,
swap, dan reverse proxy.

## Konfigurasi

Semua diatur lewat file `.env`:

| Variabel | Default | Keterangan |
|---|---|---|
| `DEEPSEEK_API_KEY` | *(kosong)* | API key DeepSeek. Kosong = mode mesin pencari ayat saja |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` | endpoint API (kompatibel OpenAI) |
| `DEEPSEEK_MODEL` | `deepseek-chat` | nama model DeepSeek |
| `EMBED_MODEL` | `intfloat/multilingual-e5-base` | model embedding (harus sama dengan saat indeks dibangun) |
| `EMBED_BACKEND` | `auto` | `auto` (ONNX bila tersedia), `onnx`, atau `torch` |
| `ORT_THREADS` | `0` | jumlah thread ONNX Runtime; `0` = otomatis (core yang tersedia untuk proses, maks. 4) |
| `COOKIE_SECURE` | `false` | `true` bila aplikasi disajikan lewat HTTPS |

## API

| Method | Path | Keterangan |
|---|---|---|
| GET | `/api/health` | status backend dan LLM (publik) |
| POST | `/api/auth/login` | body `{username, password}`; set cookie sesi httpOnly (berlaku 7 hari) |
| POST | `/api/auth/logout` | hapus sesi |
| GET | `/api/auth/me` | pengguna yang sedang login |
| POST | `/api/chat` | perlu login. Body `{query, history, use_llm_expand}`; respons SSE: `retrieval` → `delta`* → `final` (atau `error`) |
| GET | `/api/ayat/{surah}/{ayat}` | perlu login. Satu ayat lengkap (Arab, terjemahan, tafsir) |

Keamanan: password di-hash scrypt, token sesi hanya disimpan sebagai hash, dan login dikunci 60 detik
setelah 5 kali gagal per IP + username. Riwayat chat **tidak disimpan** di server maupun browser.

## Struktur

```
src/ingest/       unduh dataset, normalisasi ke SQLite, validasi
src/index/        chunking, BM25, embedding (LanceDB), ekspor & encoder ONNX
src/retrieval/    pengenal referensi, router, hybrid search, ekspansi query, akses DB
src/generation/   klien DeepSeek, prompt, validator sitasi, pipeline RAG
src/resources/    sinonim.json, alias_surah.json, stopwords_id.txt
src/api.py        backend FastAPI (SSE)
src/auth.py       login, sesi, CLI kelola akun
Dockerfile        image runtime (frontend + backend, tanpa torch)
docker-compose.yml  layanan di 127.0.0.1:8001, volume data/
deploy/nginx/     contoh konfigurasi Nginx (reverse proxy)
eval/             golden_set.jsonl, run_eval.py
web/              frontend React + Vite + TypeScript
search.py         CLI uji pencarian
```

## Batasan

Aplikasi ini bukan pengganti ulama dan tidak mengeluarkan fatwa. Jawaban AI dapat keliru;
selalu periksa ayat dan tafsir yang dikutip.

## Lisensi

**Kode sumber** QuranRAG-ID dirilis di bawah [lisensi MIT](LICENSE) © 2026 Anro128.

Lisensi MIT hanya berlaku untuk kode. Data dan model yang dipakai aplikasi tetap tunduk pada
ketentuan sumbernya masing-masing:

| Komponen | Sumber | Ketentuan |
|---|---|---|
| Teks Arab, terjemahan, dan Tafsir Kemenag | Kementerian Agama RI, via [rioastamal/quran-json](https://github.com/rioastamal/quran-json) | Repositori berlisensi MIT; hak atas isi teks tetap milik Kemenag RI. Cantumkan atribusi Kemenag RI. |
| Metadata surah/juz, terjemahan untuk validasi | [Tanzil.net](https://tanzil.net) | CC BY 3.0 (metadata). Cantumkan atribusi Tanzil. |
| Model embedding `multilingual-e5-base` (termasuk versi ONNX int8 turunannya) | [intfloat/multilingual-e5-base](https://huggingface.co/intfloat/multilingual-e5-base) | MIT |
| Jawaban AI | DeepSeek API | Mengikuti ketentuan layanan DeepSeek |

Bila Anda mendistribusikan ulang aplikasi beserta datanya, sertakan atribusi di atas
(aplikasi sudah menampilkannya di sidebar).
