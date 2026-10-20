import type { Direction, Meta, Status } from '../api'
import { STATUS_LABEL } from '../util'

export interface FormValue {
  direction: Direction
  number: string
  letter_date: string
  io_date: string
  subject: string
  party: string
  category: string
  status: Status
  due_date: string
  notes: string
}

export const emptyForm = (direction: Direction = 'masuk'): FormValue => ({
  direction, number: '', letter_date: '', io_date: new Date().toISOString().slice(0, 10),
  subject: '', party: '', category: 'Lainnya',
  status: direction === 'masuk' ? 'perlu_tindakan' : 'menunggu_balasan', due_date: '', notes: '',
})

export default function LetterForm({ v, onChange, meta }: { v: FormValue; onChange: (v: FormValue) => void; meta: Meta | null }) {
  const set = <K extends keyof FormValue>(k: K, val: FormValue[K]) => onChange({ ...v, [k]: val })
  return (
    <div className="form">
      <div className="seg seg-wide">
        {(['masuk', 'keluar'] as Direction[]).map(d => (
          <button type="button" key={d} className={v.direction === d ? `on on-${d}` : ''}
            onClick={() => onChange({ ...v, direction: d, status: d === 'masuk' ? 'perlu_tindakan' : 'menunggu_balasan' })}>
            {d === 'masuk' ? '↓ Surat masuk' : '↑ Surat keluar'}
          </button>
        ))}
      </div>
      <label className="f f-full">Perihal<input value={v.subject} onChange={e => set('subject', e.target.value)} placeholder="Pokok surat" /></label>
      <label className="f f-full">{v.direction === 'masuk' ? 'Pengirim' : 'Tujuan'}
        <input value={v.party} onChange={e => set('party', e.target.value)} placeholder="Instansi / orang" /></label>
      <label className="f">Nomor surat<input value={v.number} onChange={e => set('number', e.target.value)} /></label>
      <label className="f">Kategori
        <select value={v.category} onChange={e => set('category', e.target.value)}>
          {(meta?.categories ?? [v.category]).map(c => <option key={c}>{c}</option>)}
        </select></label>
      <label className="f">Tanggal surat<input type="date" value={v.letter_date} onChange={e => set('letter_date', e.target.value)} /></label>
      <label className="f">{v.direction === 'masuk' ? 'Tanggal diterima' : 'Tanggal dikirim'}
        <input type="date" value={v.io_date} onChange={e => set('io_date', e.target.value)} /></label>
      <label className="f">Status
        <select value={v.status} onChange={e => set('status', e.target.value as Status)}>
          {Object.entries(STATUS_LABEL).map(([k, l]) => <option key={k} value={k}>{l}</option>)}
        </select></label>
      <label className="f">Tenggat<input type="date" value={v.due_date} onChange={e => set('due_date', e.target.value)} /></label>
      <label className="f f-full">Catatan<textarea rows={2} value={v.notes} onChange={e => set('notes', e.target.value)} placeholder="Catatan pribadi (opsional)" /></label>
    </div>
  )
}
