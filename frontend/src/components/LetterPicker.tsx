import { useEffect, useState } from 'react'
import { api, type Letter } from '../api'
import { DirBadge, effDate, fmtDate } from '../util'

/** Cari & pilih surat lain (untuk membuat relasi). */
export default function LetterPicker({ exclude, onPick }: { exclude: number[]; onPick: (l: Letter) => void }) {
  const [q, setQ] = useState('')
  const [items, setItems] = useState<Letter[]>([])
  useEffect(() => {
    const h = setTimeout(() => { api.letters({ q, limit: '20' }).then(setItems).catch(() => setItems([])) }, 200)
    return () => clearTimeout(h)
  }, [q])
  const shown = items.filter(l => !exclude.includes(l.id))
  return (
    <div className="picker">
      <input autoFocus placeholder="Cari nomor, perihal, pihak, atau isi surat…" value={q} onChange={e => setQ(e.target.value)} />
      <div className="picker-list">
        {shown.length === 0 && <div className="muted small pad">Tidak ada surat yang cocok.</div>}
        {shown.map(l => (
          <button key={l.id} type="button" className="picker-item" onClick={() => onPick(l)}>
            <DirBadge d={l.direction} />
            <span className="picker-subj">{l.subject || '(tanpa perihal)'}</span>
            <span className="muted small">{l.party} · {fmtDate(effDate(l))}</span>
          </button>
        ))}
      </div>
    </div>
  )
}
