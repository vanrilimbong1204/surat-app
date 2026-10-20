import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api, type Thread } from '../api'
import { DirBadge, StatusBadge, fmtDate } from '../util'

const STATE_LABEL: Record<Thread['state'], string> = {
  giliranmu: 'Giliranmu',
  menunggu: 'Menunggu pihak lain',
  berjalan: 'Berjalan',
  selesai: 'Selesai',
}

export function ThreadState({ s }: { s: Thread['state'] }) {
  return <span className={`tstate ts-${s}`}>{STATE_LABEL[s]}</span>
}

/** Ringkasan perkembangan sebuah benang + kronologi. `currentId` disorot.
 *  Pasang key={thread.signature} di pemanggil supaya state ikut data baru. */
export default function ThreadPanel({ thread, currentId, aiAvailable, compact }: {
  thread: Thread; currentId?: number; aiAvailable: boolean; compact?: boolean
}) {
  const [t, setT] = useState(thread)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')

  async function runAi() {
    setBusy(true); setErr('')
    try { setT(await api.threadAi(t.timeline[0].id)) } catch (e) { setErr((e as Error).message) }
    setBusy(false)
  }

  return (
    <section className="thread">
      <header className="thread-head">
        <div>
          <div className="eyebrow">Benang · {t.stats.count} surat · {t.stats.masuk} masuk / {t.stats.keluar} keluar
            {t.stats.span_days != null && ` · ${t.stats.span_days} hari`}</div>
          <h3>{t.title}</h3>
          {t.parties.length > 0 && <div className="muted">{t.parties.join(' · ')}</div>}
        </div>
        <ThreadState s={t.state} />
      </header>

      <div className={`position pos-${t.state}`}>
        <strong>Posisi sekarang.</strong> {t.position}
        {t.next_due && <> Tenggat terdekat: <b>{fmtDate(t.next_due)}</b>.</>}
      </div>

      <div className="summary">
        <div className="summary-head">
          <span className="eyebrow">Ringkasan perkembangan</span>
          {aiAvailable && (
            <button className="btn btn-ghost btn-sm" onClick={runAi} disabled={busy}>
              {busy ? 'Meringkas…' : t.ai ? (t.ai.stale ? '↻ Perbarui ringkasan AI' : '↻ Ringkas ulang') : '✦ Ringkas dengan AI'}
            </button>
          )}
        </div>
        {t.ai && (
          <div className="ai-box">
            {t.ai.stale && <div className="stale">Ada surat/relasi baru sejak ringkasan ini dibuat.</div>}
            {t.ai.text.split('\n').filter(Boolean).map((p, i) => <p key={i}>{p}</p>)}
            <div className="muted small">Dibuat AI · {t.ai.created_at.slice(0, 16)}</div>
          </div>
        )}
        <ol className="story">
          {t.story.map((s, i) => <li key={i}>{s}</li>)}
        </ol>
        {t.open_points.length > 0 && (
          <div className="open-points">
            <span className="eyebrow">Yang masih harus diperhatikan</span>
            <ul>{t.open_points.map((p, i) => <li key={i}>{p}</li>)}</ul>
          </div>
        )}
        {err && <div className="error">{err}</div>}
      </div>

      {!compact && (
        <ol className="timeline">
          {t.timeline.map(it => (
            <li key={it.id} className={`tl tl-${it.direction} ${it.id === currentId ? 'tl-current' : ''}`}>
              <div className="tl-dot" />
              <div className="tl-body">
                <div className="tl-top">
                  <span className="tl-date">{fmtDate(it.date)}</span>
                  <DirBadge d={it.direction} />
                  <StatusBadge s={it.status} />
                  {it.relation && <span className="muted small">{it.relation}</span>}
                </div>
                {it.id === currentId
                  ? <div className="tl-subject">{it.subject || '(tanpa perihal)'} <span className="muted small">— surat ini</span></div>
                  : <Link to={`/surat/${it.id}`} className="tl-subject">{it.subject || '(tanpa perihal)'}</Link>}
                <div className="muted small">{it.party}</div>
                {it.points.length > 0 && (
                  <ul className="tl-points">{it.points.slice(0, 3).map((p, i) => <li key={i}>{p}</li>)}</ul>
                )}
              </div>
            </li>
          ))}
        </ol>
      )}
    </section>
  )
}
