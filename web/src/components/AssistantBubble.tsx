import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { AssistantMessage } from "../types";
import { AyatCard, ayatDomId } from "./AyatCard";

const CITATION = /\[QS\s*(\d{1,3}):(\d{1,3})(?:-(\d{1,3}))?\]/g;

/** Ubah [QS 2:255] menjadi tautan internal agar bisa diklik menuju kartu ayat. */
function linkCitations(text: string) {
  return text.replace(CITATION, (_, s, a, b) => `[QS ${s}:${a}${b ? `-${b}` : ""}](#cite-${s}-${a})`);
}

function openAyat(messageId: string, surah: number, ayat: number) {
  const el = document.getElementById(ayatDomId(messageId, surah, ayat)) as HTMLDetailsElement | null;
  if (!el) return;
  el.open = true;
  el.scrollIntoView({ behavior: "smooth", block: "center" });
  el.classList.add("flash");
  setTimeout(() => el.classList.remove("flash"), 1200);
}

interface Props {
  message: AssistantMessage;
  showTafsir: boolean;
}

export function AssistantBubble({ message: m, showTafsir }: Props) {
  const citedKeys = new Set(m.cited.map(([s, a]) => `${s}:${a}`));
  const dikutip = m.cited
    .map(([s, a]) => m.ayat.find((x) => x.surah_no === s && x.ayat_no === a))
    .filter((x) => x !== undefined);
  const terkait = m.ayat.filter((x) => !citedKeys.has(`${x.surah_no}:${x.ayat_no}`));

  return (
    <div className="bubble assistant">
      {m.status === "searching" && <p className="muted pulse">Mencari ayat…</p>}

      {m.content && (
        <div className="answer">
          <Markdown
            remarkPlugins={[remarkGfm]}
            components={{
              a: ({ href, children }) => {
                const match = href?.match(/^#cite-(\d+)-(\d+)$/);
                if (match) {
                  return (
                    <button type="button" className="cite" onClick={() => openAyat(m.id, +match[1], +match[2])}>
                      {children}
                    </button>
                  );
                }
                return <a href={href} target="_blank" rel="noreferrer">{children}</a>;
              },
            }}
          >
            {linkCitations(m.content)}
          </Markdown>
          {m.status === "streaming" && <span className="caret" />}
        </div>
      )}

      {m.error && <p className="error">⚠️ {m.error}. Ayat yang ditemukan tetap ditampilkan di bawah.</p>}
      {m.invalid.length > 0 && (
        <p className="warn">
          {m.invalid.length} sitasi dihapus karena tidak ada di sumber yang ditemukan (ditandai “sitasi tidak terverifikasi”).
        </p>
      )}

      {dikutip.length > 0 && (
        <section className="cards">
          <h3>Ayat yang dikutip</h3>
          {dikutip.map((a, i) => (
            <AyatCard key={`${a.surah_no}:${a.ayat_no}`} ayat={a} messageId={m.id} defaultOpen={i < 3} showTafsir={showTafsir} />
          ))}
        </section>
      )}

      {terkait.length > 0 && m.status !== "searching" && (
        <section className="cards">
          <h3>{dikutip.length > 0 ? "Ayat terkait lainnya" : `Ayat yang ditemukan (${terkait.length})`}</h3>
          {terkait.map((a) => (
            <AyatCard
              key={`${a.surah_no}:${a.ayat_no}`}
              ayat={a}
              messageId={m.id}
              defaultOpen={!m.ai && m.status === "done" && terkait.length <= 3}
              showTafsir={showTafsir}
            />
          ))}
        </section>
      )}

      {m.ai && m.status === "done" && (
        <p className="disclaimer">
          Jawaban disusun AI dari terjemahan dan Tafsir Kemenag RI, bukan fatwa. Untuk persoalan hukum atau pribadi,
          tanyakan kepada ulama yang kompeten.
        </p>
      )}
    </div>
  );
}
