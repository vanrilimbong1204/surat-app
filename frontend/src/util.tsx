import { Link } from 'react-router-dom'
import type { Direction, Letter, Status } from './api'

const BULAN = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des']

export function fmtDate(iso?: string | null) {
  if (!iso) return '—'
  const [y, m, d] = iso.slice(0, 10).split('-').map(Number)
  if (!y || !m || !d) return iso
  return `${d} ${BULAN[m - 1]} ${y}`
}

export function daysUntil(iso?: string | null) {
  if (!iso) return null
  const t = new Date(); t.setHours(0, 0, 0, 0)
  return Math.round((new Date(iso + 'T00:00:00').getTime() - t.getTime()) / 86400000)
}

export const effDate = (l: Letter) => l.io_date || l.letter_date || l.created_at.slice(0, 10)

export const STATUS_LABEL: Record<Status, string> = {
  perlu_tindakan: 'Perlu tindakan',
  menunggu_balasan: 'Menunggu balasan',
  selesai: 'Selesai',
  arsip: 'Arsip / info',
}

export const RELATION_LABEL: Record<string, string> = {
  membalas: 'Membalas',
  menindaklanjuti: 'Menindaklanjuti',
  merujuk: 'Merujuk',
  meralat: 'Meralat / mencabut',
}
// kebalikan relasi, dilihat dari surat yang dirujuk
export const RELATION_INVERSE: Record<string, string> = {
  membalas: 'Dibalas oleh',
  menindaklanjuti: 'Ditindaklanjuti oleh',
  merujuk: 'Dirujuk oleh',
  meralat: 'Diralat oleh',
}

export function DirBadge({ d }: { d: Direction }) {
  return <span className={`dir dir-${d}`}>{d === 'masuk' ? '↓ Masuk' : '↑ Keluar'}</span>
}

export function StatusBadge({ s }: { s: Status }) {
  return <span className={`status st-${s}`}>{STATUS_LABEL[s]}</span>
}

export function DueChip({ due, status }: { due: string | null; status: Status }) {
  if (!due || status === 'selesai' || status === 'arsip') return null
  const n = daysUntil(due)!
  const cls = n < 0 ? 'due due-over' : n <= 7 ? 'due due-soon' : 'due'
  const txt = n < 0 ? `lewat ${-n} hari` : n === 0 ? 'hari ini' : `${n} hari lagi`
  return <span className={cls} title={`Tenggat ${fmtDate(due)}`}>⏱ {txt}</span>
}

export function LetterRow({ l, extra }: { l: Letter; extra?: React.ReactNode }) {
  return (
    <Link to={`/surat/${l.id}`} className="lrow">
      <div className="lrow-main">
        <div className="lrow-top">
          <DirBadge d={l.direction} />
          <span className="lrow-party">{l.party || 'Tanpa pihak'}</span>
          <span className="lrow-date">{fmtDate(effDate(l))}</span>
        </div>
        <div className="lrow-subject">{l.subject || <em>(tanpa perihal)</em>}</div>
        {l.highlights[0] && <div className="lrow-point">{l.highlights[0]}</div>}
        <div className="lrow-meta">
          <StatusBadge s={l.status} />
          <DueChip due={l.due_date} status={l.status} />
          <span className="cat">{l.category}</span>
          {!!l.needs_review && <span className="review-chip">● perlu dicek</span>}
          {!!l.thread_size && l.thread_size > 1 && <span className="thread-chip">🔗 {l.thread_size} surat</span>}
          {extra}
        </div>
      </div>
    </Link>
  )
}
