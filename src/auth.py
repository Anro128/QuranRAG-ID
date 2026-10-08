"""Autentikasi username + password dan sesi berbasis cookie (SQLite: data/app.db).

- Password di-hash dengan scrypt (stdlib) + salt acak per pengguna.
- Token sesi acak dikirim sebagai cookie httpOnly; yang disimpan di DB hanya hash SHA-256-nya.
- Tidak ada pendaftaran publik: akun dibuat lewat CLI.

CLI:
    python -m src.auth create-user <username>     # password ditanya (atau --password)
    python -m src.auth passwd <username>
    python -m src.auth delete-user <username>
    python -m src.auth list-users
"""
import argparse
import base64
import getpass
import hashlib
import hmac
import re
import secrets
import sqlite3
import sys
import time
from dataclasses import dataclass

from src.config import APP_DB

SESSION_TTL = 7 * 24 * 3600
USERNAME_RE = re.compile(r"^[a-zA-Z0-9_.-]{3,32}$")
MIN_PASSWORD = 8
SCRYPT_N, SCRYPT_R, SCRYPT_P = 2**14, 8, 1

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    created_at    INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at INTEGER NOT NULL
);
"""


@dataclass
class User:
    id: int
    username: str


def _connect() -> sqlite3.Connection:
    APP_DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(APP_DB)
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(SCHEMA)
    return con


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P)
    b64 = lambda b: base64.b64encode(b).decode()  # noqa: E731
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${b64(salt)}${b64(digest)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, n, r, p, salt, digest = stored.split("$")
        expected = base64.b64decode(digest)
        actual = hashlib.scrypt(password.encode(), salt=base64.b64decode(salt), n=int(n), r=int(r), p=int(p))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual, expected)


# hash tiruan agar waktu respons sama untuk username yang tidak ada (cegah enumerasi user)
_DUMMY_HASH = hash_password(secrets.token_hex(8))


def authenticate(username: str, password: str) -> User | None:
    con = _connect()
    row = con.execute("SELECT id, username, password_hash FROM users WHERE username = ?", (username,)).fetchone()
    con.close()
    if row is None:
        verify_password(password, _DUMMY_HASH)
        return None
    return User(row[0], row[1]) if verify_password(password, row[2]) else None


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_session(user: User) -> str:
    token = secrets.token_urlsafe(32)
    con = _connect()
    now = int(time.time())
    con.execute("DELETE FROM sessions WHERE expires_at < ?", (now,))
    con.execute("INSERT INTO sessions VALUES (?, ?, ?)", (_token_hash(token), user.id, now + SESSION_TTL))
    con.commit()
    con.close()
    return token


def user_for_token(token: str | None) -> User | None:
    if not token:
        return None
    con = _connect()
    row = con.execute(
        "SELECT u.id, u.username FROM sessions s JOIN users u ON u.id = s.user_id "
        "WHERE s.token_hash = ? AND s.expires_at > ?", (_token_hash(token), int(time.time()))
    ).fetchone()
    con.close()
    return User(*row) if row else None


def delete_session(token: str | None) -> None:
    if not token:
        return
    con = _connect()
    con.execute("DELETE FROM sessions WHERE token_hash = ?", (_token_hash(token),))
    con.commit()
    con.close()


class LoginRateLimiter:
    """Kunci sementara setelah terlalu banyak percobaan gagal per (IP, username). Disimpan di memori."""

    def __init__(self, max_failures: int = 5, window: int = 300, lockout: int = 60):
        self.max_failures, self.window, self.lockout = max_failures, window, lockout
        self._failures: dict[str, list[float]] = {}

    def retry_after(self, key: str) -> int:
        now = time.time()
        recent = [t for t in self._failures.get(key, []) if now - t < self.window]
        self._failures[key] = recent
        remaining = self.lockout - (now - recent[-1]) if len(recent) >= self.max_failures else 0
        # setelah masa kunci habis, percobaan dibuka lagi; kegagalan berikutnya langsung mengunci ulang
        return int(remaining) + 1 if remaining > 0 else 0

    def fail(self, key: str) -> None:
        self._failures.setdefault(key, []).append(time.time())

    def reset(self, key: str) -> None:
        self._failures.pop(key, None)


# ---------------------------------------------------------------- CLI


def _ask_password(given: str | None) -> str:
    if given:
        password = given
    else:
        password = getpass.getpass("Password: ")
        if getpass.getpass("Ulangi password: ") != password:
            sys.exit("Password tidak sama.")
    if len(password) < MIN_PASSWORD:
        sys.exit(f"Password minimal {MIN_PASSWORD} karakter.")
    return password


def main() -> None:
    parser = argparse.ArgumentParser(description="Kelola akun QuranRAG-ID")
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in ("create-user", "passwd"):
        p = sub.add_parser(name)
        p.add_argument("username")
        p.add_argument("--password", help="tidak disarankan: tersimpan di riwayat shell")
    sub.add_parser("delete-user").add_argument("username")
    sub.add_parser("list-users")
    args = parser.parse_args()

    con = _connect()
    if args.cmd == "create-user":
        if not USERNAME_RE.match(args.username):
            sys.exit("Username 3-32 karakter: huruf, angka, titik, minus, garis bawah.")
        if con.execute("SELECT 1 FROM users WHERE username = ?", (args.username,)).fetchone():
            sys.exit(f"Username '{args.username}' sudah ada.")
        con.execute("INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
                    (args.username, hash_password(_ask_password(args.password)), int(time.time())))
        print(f"Pengguna '{args.username}' dibuat.")
    elif args.cmd == "passwd":
        row = con.execute("SELECT id FROM users WHERE username = ?", (args.username,)).fetchone()
        if not row:
            sys.exit("Pengguna tidak ditemukan.")
        con.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hash_password(_ask_password(args.password)), row[0]))
        con.execute("DELETE FROM sessions WHERE user_id = ?", (row[0],))
        print("Password diganti; semua sesi pengguna ini dikeluarkan.")
    elif args.cmd == "delete-user":
        n = con.execute("DELETE FROM users WHERE username = ?", (args.username,)).rowcount
        print("Pengguna dihapus." if n else "Pengguna tidak ditemukan.")
    else:
        for uid, name, created in con.execute("SELECT id, username, created_at FROM users ORDER BY id"):
            print(f"{uid:>3}  {name:<32} dibuat {time.strftime('%Y-%m-%d %H:%M', time.localtime(created))}")
    con.commit()
    con.close()


if __name__ == "__main__":
    main()
