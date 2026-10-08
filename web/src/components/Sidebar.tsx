import { CloseIcon, Logo, LogoutIcon, PlusIcon } from "./Icons";

const EXAMPLES = [
  "Ayat tentang sabar menghadapi musibah",
  "Apa isi ayat kursi?",
  "Gimana biar hati tenang?",
  "QS Al-Mulk ayat 2",
  "Larangan riba dalam jual beli",
];

interface Props {
  open: boolean;
  username: string;
  llmConfigured: boolean;
  showTafsir: boolean;
  useLlmExpand: boolean;
  busy: boolean;
  onClose: () => void;
  onNewChat: () => void;
  onAsk: (q: string) => void;
  onShowTafsir: (v: boolean) => void;
  onUseLlmExpand: (v: boolean) => void;
  onLogout: () => void;
}

export function Sidebar(p: Props) {
  return (
    <>
      <div className={`scrim ${p.open ? "show" : ""}`} onClick={p.onClose} />
      <aside className={`sidebar ${p.open ? "open" : ""}`}>
        <div className="sidebar-head">
          <Logo size={28} />
          <span className="sidebar-title">QuranRAG-ID</span>
          <button type="button" className="icon-btn only-mobile" onClick={p.onClose} aria-label="Tutup menu">
            <CloseIcon />
          </button>
        </div>

        <button type="button" className="new-chat" onClick={p.onNewChat}>
          <PlusIcon size={18} /> Chat baru
        </button>

        <nav className="sidebar-scroll">
          <section>
            <h4>Pengaturan</h4>
            <label className="toggle">
              <span>Tampilkan tafsir</span>
              <input type="checkbox" checked={p.showTafsir} onChange={(e) => p.onShowTafsir(e.target.checked)} />
            </label>
            <label className="toggle" title="Perluas kata kunci pencarian dengan AI">
              <span>Ekspansi kata kunci AI</span>
              <input
                type="checkbox"
                checked={p.useLlmExpand && p.llmConfigured}
                disabled={!p.llmConfigured}
                onChange={(e) => p.onUseLlmExpand(e.target.checked)}
              />
            </label>
          </section>

          <section>
            <h4>Coba tanyakan</h4>
            {EXAMPLES.map((ex) => (
              <button key={ex} type="button" className="side-link" disabled={p.busy} onClick={() => p.onAsk(ex)}>
                {ex}
              </button>
            ))}
          </section>

          <section className="side-info">
            <h4>Tentang</h4>
            <p>
              Jawaban bersumber dari terjemahan &amp; Tafsir Kemenag RI. Riwayat chat tidak disimpan; percakapan hilang
              saat memulai chat baru atau keluar.
            </p>
            <p>
              Data:{" "}
              <a href="https://github.com/rioastamal/quran-json" target="_blank" rel="noreferrer">
                quran-json
              </a>{" "}
              ·{" "}
              <a href="https://tanzil.net" target="_blank" rel="noreferrer">
                Tanzil.net
              </a>
            </p>
          </section>
        </nav>

        <div className="user-row">
          <span className="avatar">{p.username.slice(0, 1).toUpperCase()}</span>
          <span className="user-name" title={p.username}>
            {p.username}
          </span>
          <button type="button" className="ghost with-icon" onClick={p.onLogout}>
            <LogoutIcon size={15} /> Keluar
          </button>
        </div>
      </aside>
    </>
  );
}
