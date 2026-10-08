# QuranRAG-ID

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
| Python | 3.11+ | 3.11+ |
| Node.js | 20+ (build frontend) | tidak perlu (cukup `web/dist`) |
| RAM | ±8 GB | 1 GB cukup (server ±500 MB, puncak ±650 MB) |
| Disk | ±5 GB (torch, model, data) | ±1 GB |
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

> Di server yang hanya menjalankan aplikasi, cukup `pip install -e .` (tanpa torch). Lihat [Deploy ke VPS](#deploy-ke-vps).

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

## Deploy ke VPS

Server tidak memerlukan torch: VPS 1 GB RAM sudah cukup.

1. **Salin ke server**: kode repo, `data/processed/`, `data/models/`, dan `web/dist/`.
   `data/raw/` tidak diperlukan.
2. **Pasang dan konfigurasi**:

   ```bash
   python3 -m venv .venv && source .venv/bin/activate
   pip install -e .                 # hanya dependensi runtime (±520 MB)
   cp .env.example .env             # isi DEEPSEEK_API_KEY, EMBED_BACKEND=onnx, COOKIE_SECURE=true
   python -m src.auth create-user <username>
   ```

3. **Jalankan** di belakang reverse proxy HTTPS (Nginx/Caddy):

   ```bash
   uvicorn src.api:app --host 127.0.0.1 --port 8000
   ```

Catatan untuk VPS kecil:

- Jalankan **satu worker** (satu proses), yaitu perintah `uvicorn` di atas apa adanya. Jangan menambah
  `--workers N` atau memakai `gunicorn -w N`: tiap worker memuat model dan indeks sendiri (±500 MB per proses).
  Satu worker tetap bisa melayani banyak pengguna bersamaan karena tiap request berjalan di thread terpisah
  dan sebagian besar waktunya menunggu respons DeepSeek.
- Aktifkan swap ±1 GB sebagai pengaman puncak memori saat start.
- Bila VPS hanya 1 vCPU, set `ORT_THREADS=1`.
- Di Nginx, tambahkan `proxy_buffering off;` untuk `/api/chat` agar jawaban tetap mengalir (streaming).

## Konfigurasi

Semua diatur lewat file `.env`:

| Variabel | Default | Keterangan |
|---|---|---|
| `DEEPSEEK_API_KEY` | *(kosong)* | API key DeepSeek. Kosong = mode mesin pencari ayat saja |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` | endpoint API (kompatibel OpenAI) |
| `DEEPSEEK_MODEL` | `deepseek-chat` | nama model DeepSeek |
| `EMBED_MODEL` | `intfloat/multilingual-e5-base` | model embedding (harus sama dengan saat indeks dibangun) |
| `EMBED_BACKEND` | `auto` | `auto` (ONNX bila tersedia), `onnx`, atau `torch` |
| `ORT_THREADS` | `0` | jumlah thread ONNX Runtime; `0` = otomatis |
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
