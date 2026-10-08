# QuranRAG-ID

Tanya-jawab Al-Qur'an berbahasa Indonesia berbasis RAG (Retrieval-Augmented Generation).
Setiap jawaban mengutip ayat sumbernya (`[QS surah:ayat]`), dan teks Arab selalu diambil dari
database, tidak pernah dibuat oleh AI.

## Fitur

- Pencarian makna (hybrid: embedding `multilingual-e5-base` + BM25 dengan stemmer Indonesia, digabung dengan RRF)
- Pengenalan referensi langsung: `QS 2:255`, `Al-Baqarah ayat 255`, `albaqarah 255`, `ayat kursi`, `surat yasin ayat 1`
- Normalisasi istilah ke ejaan Kemenag (`sholat` → `salat`, `bunga` → `riba`, dst.)
- Jawaban AI via DeepSeek, dengan validasi sitasi: sitasi ke ayat yang tidak ada di sumber otomatis ditandai
- Tetap bisa dipakai sebagai mesin pencari ayat tanpa API key

## Instalasi

Prasyarat: Python 3.11+, RAM ±8 GB.

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows  (Linux/macOS: source .venv/bin/activate)
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -e .
copy .env.example .env            # lalu isi DEEPSEEK_API_KEY
```

## Menjalankan

Build frontend sekali (butuh Node.js 20+):

```bash
cd web
npm install
npm run build        # hasil di web/dist, otomatis dilayani backend
cd ..
```

Buat akun (tidak ada pendaftaran publik; password minimal 8 karakter):

```bash
python -m src.auth create-user <username>     # password ditanyakan
python -m src.auth list-users | passwd <username> | delete-user <username>
```

Jalankan aplikasi (satu proses), lalu buka http://localhost:8000 dan login:

```bash
uvicorn src.api:app --port 8000
```

Mode pengembangan frontend (hot reload, request `/api` diteruskan ke port 8000):

```bash
uvicorn src.api:app --reload --port 8000     # terminal 1
cd web && npm run dev                        # terminal 2 -> http://localhost:5173
```

Alat bantu:

```bash
python search.py "sabar menghadapi musibah"   # uji retrieval dari terminal
python -m eval.run_eval --detail              # evaluasi retrieval atas golden set
```

## API

| Method | Path | Keterangan |
|---|---|---|
| GET | `/api/health` | status backend dan LLM (publik) |
| POST | `/api/auth/login` | body `{username, password}`; set cookie sesi httpOnly (berlaku 7 hari) |
| POST | `/api/auth/logout` | hapus sesi |
| GET | `/api/auth/me` | pengguna yang sedang login |
| POST | `/api/chat` | perlu login. Body `{query, history, use_llm_expand}`; respons SSE: `retrieval` → `delta`* → `final` (atau `error`) |
| GET | `/api/ayat/{surah}/{ayat}` | perlu login. Satu ayat lengkap (Arab, terjemahan, tafsir) |

Keamanan login: password di-hash scrypt, token sesi hanya disimpan sebagai hash, login dikunci 60 detik
setelah 5 kali gagal per IP + username. Bila disajikan lewat HTTPS, set `COOKIE_SECURE=true` di `.env`.
Riwayat chat **tidak disimpan** di server maupun browser.

## Struktur

```
src/ingest/       unduh, normalisasi ke SQLite, validasi
src/index/        chunking, embedding (LanceDB), BM25
src/retrieval/    ref_parser, router, hybrid search, ekspansi query, akses DB
src/generation/   klien DeepSeek, prompt, validator sitasi, pipeline RAG
src/resources/    sinonim.json, alias_surah.json, stopwords_id.txt
src/api.py        backend FastAPI (SSE)
src/auth.py       login username/password, sesi, CLI kelola akun
eval/             golden_set.jsonl, run_eval.py
web/              frontend React + Vite + TypeScript
search.py         CLI uji retrieval
```

## Sumber data dan atribusi

- Teks Arab, terjemahan, dan Tafsir Kemenag: **Kementerian Agama Republik Indonesia**, melalui dataset
  [rioastamal/quran-json](https://github.com/rioastamal/quran-json) (lisensi repositori MIT).
- Metadata surah/juz dan validasi struktur: [Tanzil.net](https://tanzil.net) (CC BY 3.0).

## Batasan

Aplikasi ini bukan pengganti ulama dan tidak mengeluarkan fatwa. Jawaban AI dapat keliru;
selalu periksa ayat dan tafsir yang dikutip.
