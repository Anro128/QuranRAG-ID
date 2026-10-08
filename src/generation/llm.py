"""Klien LLM (DeepSeek, API kompatibel OpenAI). Satu-satunya tempat yang tahu provider LLM."""
from collections.abc import Iterator
from functools import lru_cache

from openai import OpenAI

from src.config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL


class LLMNotConfigured(RuntimeError):
    pass


@lru_cache(maxsize=1)
def client() -> OpenAI:
    if not DEEPSEEK_API_KEY:
        raise LLMNotConfigured("DEEPSEEK_API_KEY belum diisi di file .env")
    return OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL, timeout=60)


def complete(prompt: str, max_tokens: int = 512, temperature: float = 0.0) -> str:
    resp = client().chat.completions.create(
        model=DEEPSEEK_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return resp.choices[0].message.content or ""


# Model DeepSeek yang "berpikir" dulu (reasoning) menghitung token berpikir ke max_tokens. Jawaban normal
# terukur ±1.100–1.300 token termasuk ±100–350 token berpikir, jadi beri ruang lega agar tidak terpotong.
def stream_chat(messages: list[dict], max_tokens: int = 4096, temperature: float = 0.2) -> Iterator[str]:
    stream = client().chat.completions.create(
        model=DEEPSEEK_MODEL,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
        stream=True,
    )
    for chunk in stream:
        if chunk.choices and (delta := chunk.choices[0].delta.content):
            yield delta
