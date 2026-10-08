import { useState } from "react";
import { login } from "../api";

interface Props {
  onLogin: (username: string) => void;
}

export function Login({ onLogin }: Props) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      onLogin(await login(username.trim(), password));
    } catch (err) {
      setError((err as Error).message);
      setPassword("");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-page">
      <form className="login-card" onSubmit={submit}>
        <div className="login-brand">
          <span className="logo">📖</span>
          <h1>QuranRAG-ID</h1>
          <p>Tanya-jawab Al-Qur'an berbahasa Indonesia</p>
        </div>

        <label>
          Username
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            autoFocus
            required
          />
        </label>
        <label>
          Password
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            required
          />
        </label>

        {error && <p className="error" role="alert">{error}</p>}

        <button type="submit" className="primary block" disabled={busy || !username.trim() || !password}>
          {busy ? "Memeriksa…" : "Masuk"}
        </button>
        <p className="login-note">Belum punya akun? Hubungi admin aplikasi.</p>
      </form>
    </div>
  );
}
