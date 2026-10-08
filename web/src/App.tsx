import { useEffect, useState } from "react";
import { getMe, logout } from "./api";
import { Login } from "./components/Login";
import { Workspace } from "./components/Workspace";

type AuthState = { status: "loading" } | { status: "anon"; notice?: string } | { status: "authed"; username: string };

export default function App() {
  const [auth, setAuth] = useState<AuthState>({ status: "loading" });

  useEffect(() => {
    getMe()
      .then((username) => setAuth(username ? { status: "authed", username } : { status: "anon" }))
      .catch(() => setAuth({ status: "anon", notice: "Backend tidak dapat dihubungi." }));
  }, []);

  if (auth.status === "loading") return <div className="splash">📖</div>;

  if (auth.status === "anon") {
    return (
      <>
        {auth.notice && <div className="toast">{auth.notice}</div>}
        <Login onLogin={(username) => setAuth({ status: "authed", username })} />
      </>
    );
  }

  return (
    <Workspace
      // key: remount saat ganti pengguna agar percakapan sebelumnya tidak terbawa
      key={auth.username}
      username={auth.username}
      onLogout={async () => {
        await logout();
        setAuth({ status: "anon" });
      }}
      onSessionExpired={() => setAuth({ status: "anon", notice: "Sesi berakhir, silakan login kembali." })}
    />
  );
}
