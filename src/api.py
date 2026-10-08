"""Backend HTTP QuranRAG-ID (FastAPI).

Endpoint:
    GET  /api/health              status backend & LLM (publik)
    POST /api/auth/login          {username, password} -> cookie sesi
    POST /api/auth/logout         hapus sesi
    GET  /api/auth/me             pengguna yang sedang login
    POST /api/chat                jawaban streaming (Server-Sent Events)       [perlu login]
    GET  /api/ayat/{surah}/{ayat} satu ayat lengkap (Arab, terjemahan, tafsir) [perlu login]
    /                             frontend hasil build (web/dist), bila ada

Jalankan:
    uvicorn src.api:app --reload --port 8000
"""
import json
from collections.abc import Iterator
from dataclasses import asdict
from typing import Annotated

from fastapi import Cookie, Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from src import auth
from src.config import COOKIE_SECURE, DEEPSEEK_API_KEY, DEEPSEEK_MODEL, ROOT
from src.generation.llm import LLMNotConfigured
from src.generation.rag import prepare
from src.retrieval.store import Ayat, get_ayat

WEB_DIST = ROOT / "web" / "dist"

LLM_ERRORS = {
    401: "API key DeepSeek tidak valid",
    402: "Saldo akun DeepSeek habis, silakan top up",
    404: "Nama model tidak ditemukan, periksa DEEPSEEK_MODEL di .env",
    429: "Batas permintaan DeepSeek terlampaui, coba lagi sebentar",
}

SESSION_COOKIE = "qr_session"

app = FastAPI(title="QuranRAG-ID")
login_limiter = auth.LoginRateLimiter()


def current_user(qr_session: Annotated[str | None, Cookie()] = None) -> auth.User:
    user = auth.user_for_token(qr_session)
    if user is None:
        raise HTTPException(401, "Silakan login terlebih dahulu")
    return user


CurrentUser = Annotated[auth.User, Depends(current_user)]


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


class Message(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(max_length=8000)


class ChatRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    history: list[Message] = Field(default_factory=list, max_length=20)
    use_llm_expand: bool = True


def ayat_json(a: Ayat) -> dict:
    return {**asdict(a), "label": a.label}


def sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "llm_configured": bool(DEEPSEEK_API_KEY), "model": DEEPSEEK_MODEL}


@app.post("/api/auth/login")
def login(req: LoginRequest, request: Request, response: Response) -> dict:
    key = f"{request.client.host if request.client else '?'}:{req.username.lower()}"
    if wait := login_limiter.retry_after(key):
        raise HTTPException(429, f"Terlalu banyak percobaan gagal. Coba lagi dalam {wait} detik.")
    user = auth.authenticate(req.username, req.password)
    if user is None:
        login_limiter.fail(key)
        raise HTTPException(401, "Username atau password salah")
    login_limiter.reset(key)
    response.set_cookie(SESSION_COOKIE, auth.create_session(user), max_age=auth.SESSION_TTL,
                        httponly=True, samesite="lax", secure=COOKIE_SECURE, path="/")
    return {"username": user.username}


@app.post("/api/auth/logout")
def logout(response: Response, qr_session: Annotated[str | None, Cookie()] = None) -> dict:
    auth.delete_session(qr_session)
    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"ok": True}


@app.get("/api/auth/me")
def me(user: CurrentUser) -> dict:
    return {"username": user.username}


@app.get("/api/ayat/{surah_no}/{ayat_no}")
def ayat(surah_no: int, ayat_no: int, _: CurrentUser) -> dict:
    found = get_ayat([(surah_no, ayat_no)])
    if not found:
        raise HTTPException(404, "Ayat tidak ditemukan")
    return ayat_json(found[0])


@app.post("/api/chat")
def chat(req: ChatRequest, _: CurrentUser) -> StreamingResponse:
    """Urutan event: retrieval -> delta* -> final, atau error (ayat tetap terkirim lebih dulu)."""

    def events() -> Iterator[str]:
        turn = prepare(req.query, history=[m.model_dump() for m in req.history],
                       use_llm_expand=req.use_llm_expand and bool(DEEPSEEK_API_KEY))
        r = turn.retrieval
        yield sse("retrieval", {
            "route": r.route,
            "refs": [ref.label() for ref in r.refs],
            "surah_filter": r.surah_filter,
            "ayat": [ayat_json(a) for a in turn.ayat],
        })

        if not turn.ayat:
            yield sse("final", {"text": "Tidak ditemukan ayat yang relevan. Coba ubah kata kunci "
                                        "atau sebutkan surah/ayat tertentu.", "cited": [], "invalid": [], "ai": False})
            return
        if not DEEPSEEK_API_KEY:
            yield sse("final", {"text": f"Ditemukan {len(turn.ayat)} ayat yang relevan. "
                                        "(Jawaban AI nonaktif: DEEPSEEK_API_KEY belum diisi.)",
                                "cited": [], "invalid": [], "ai": False})
            return

        try:
            for delta in turn.stream():
                yield sse("delta", {"text": delta})
        except LLMNotConfigured as e:
            yield sse("error", {"message": str(e)})
            return
        except Exception as e:  # jaringan / kuota / API
            status = getattr(e, "status_code", None)
            yield sse("error", {"status": status,
                                "message": LLM_ERRORS.get(status, f"Gagal menghubungi layanan AI ({type(e).__name__})")})
            return

        v = turn.finalize()
        yield sse("final", {"text": v.text, "cited": v.cited, "invalid": v.invalid, "ai": True})

    return StreamingResponse(events(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


if WEB_DIST.exists():
    app.mount("/", StaticFiles(directory=WEB_DIST, html=True), name="web")
