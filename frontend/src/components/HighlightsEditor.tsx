import { useState } from 'react'

/** Daftar poin penting yang bisa diedit (tambah, ubah, hapus). */
export default function HighlightsEditor({ value, onChange }: { value: string[]; onChange: (v: string[]) => void }) {
  const [draft, setDraft] = useState('')
  const set = (i: number, s: string) => onChange(value.map((v, j) => (j === i ? s : v)))
  const add = () => { if (draft.trim()) { onChange([...value, draft.trim()]); setDraft('') } }
  return (
    <div className="hl-edit">
      {value.map((p, i) => (
        <div key={i} className="hl-row">
          <span className="hl-mark" />
          <textarea rows={2} value={p} onChange={e => set(i, e.target.value)} />
          <button type="button" className="icon-btn" title="Hapus poin" onClick={() => onChange(value.filter((_, j) => j !== i))}>×</button>
        </div>
      ))}
      <div className="hl-row">
        <span className="hl-mark hl-mark-new" />
        <textarea rows={1} placeholder="Tambah poin…" value={draft} onChange={e => setDraft(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); add() } }} />
        <button type="button" className="icon-btn" title="Tambah" onClick={add}>+</button>
      </div>
    </div>
  )
}
