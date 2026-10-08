import type { Ayat } from "../types";

export function ayatDomId(messageId: string, surah: number, ayat: number) {
  return `ayat-${messageId}-${surah}-${ayat}`;
}

interface Props {
  ayat: Ayat;
  messageId: string;
  defaultOpen: boolean;
  showTafsir: boolean;
}

export function AyatCard({ ayat, messageId, defaultOpen, showTafsir }: Props) {
  return (
    <details className="ayat-card" id={ayatDomId(messageId, ayat.surah_no, ayat.ayat_no)} open={defaultOpen}>
      <summary>
        <span className="ayat-ref">QS {ayat.surah_no}:{ayat.ayat_no}</span>
        <span className="ayat-name">{ayat.nama_surah} · ayat {ayat.ayat_no}</span>
        <span className="ayat-juz">Juz {ayat.juz}</span>
      </summary>
      <div className="ayat-body">
        <p className="arab" lang="ar" dir="rtl">{ayat.teks_arab}</p>
        <p className="terjemahan">{ayat.terjemahan}</p>
        <p className="sumber">Terjemahan Kemenag RI</p>
        {showTafsir && ayat.tafsir && (
          <details className="tafsir">
            <summary>Tafsir Kemenag</summary>
            <div className="tafsir-text">{ayat.tafsir}</div>
          </details>
        )}
      </div>
    </details>
  );
}
