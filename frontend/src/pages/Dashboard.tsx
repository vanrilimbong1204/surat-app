import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, type Dashboard as D, type Letter } from '../api'
import { ThreadState } from '../components/ThreadPanel'
import { DueChip, LetterRow, fmtDate } from '../util'

function Section({ title, items, empty, more }: { title: string; items: Letter[]; empty: string; more?: string }) {
  return (
    <section className="card">
      <div className="card-head"><h2>{title}</h2>{more && <Link to={more} className="link small">Lihat semua →</Link>}</div>
      {items.length === 0 ? <div className="empty">{empty}</div> : items.map(l => <LetterRow key={l.id} l={l} />)}
    </section>
  )
}

export default function Dashboard() {
  const [d, setD] = useState<D | null>(null)
  const [err, setErr] = useState('')
  useEffect(() => { api.dashboard().then(setD).catch(e => setErr(e.message)) }, [])
  if (err) return <div className="error">{err}</div>
  if (!d) return <div className="loading">Memuat…</div>

  const max = Math.max(1, ...d.weeks.map(w => w.masuk + w.keluar))
  const hour = new Date().getHours()
  const greet = hour < 11 ? 'Selamat pagi' : hour < 15 ? 'Selamat siang' : hour < 19 ? 'Selamat sore' : 'Selamat malam'

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <div className="eyebrow">{fmtDate(new Date().toISOString().slice(0, 10))}</div>
          <h1>{greet}.</h1>
          <p className="lead">
            {d.kpi.perlu_tindakan === 0 && d.kpi.lewat_tenggat === 0
              ? 'Tidak ada surat yang menunggu tindakanmu.'
              : <>Ada <b>{d.kpi.perlu_tindakan}</b> surat perlu tindakan{d.kpi.lewat_tenggat > 0 && <>, <b className="red">{d.kpi.lewat_tenggat} lewat tenggat</b></>}.</>}
          </p>
        </div>
        <Link to="/unggah" className="btn btn-primary">+ Unggah surat</Link>
      </header>

      <div className="kpis">
        <div className="kpi"><span>Masuk bulan ini</span><b>{d.kpi.masuk_bulan_ini}</b></div>
        <div className="kpi"><span>Keluar bulan ini</span><b>{d.kpi.keluar_bulan_ini}</b></div>
        <div className="kpi kpi-warn"><span>Perlu tindakan</span><b>{d.kpi.perlu_tindakan}</b></div>
        <div className="kpi"><span>Menunggu balasan</span><b>{d.kpi.menunggu_balasan}</b></div>
        <div className={`kpi ${d.kpi.lewat_tenggat ? 'kpi-red' : ''}`}><span>Lewat tenggat</span><b>{d.kpi.lewat_tenggat}</b></div>
      </div>

      {d.review.length > 0 && (
        <section className="card card-review">
          <div className="card-head"><h2>Baru diisi otomatis — perlu dicek ({d.kpi.perlu_dicek})</h2>
            <Link to="/surat?review=1" className="link small">Lihat semua →</Link></div>
          {d.review.slice(0, 4).map(l => <LetterRow key={l.id} l={l} />)}
        </section>
      )}

      {(d.overdue.length > 0 || d.upcoming.length > 0) && (
        <section className="card card-alert">
          <div className="card-head"><h2>Tenggat</h2></div>
          {[...d.overdue, ...d.upcoming].map(l => (
            <Link key={l.id} to={`/surat/${l.id}`} className="due-line">
              <DueChip due={l.due_date} status={l.status} />
              <span className="due-subj">{l.subject || '(tanpa perihal)'}</span>
              <span className="muted small">{l.party} · {fmtDate(l.due_date)}</span>
            </Link>
          ))}
        </section>
      )}

      <div className="grid2">
        <Section title="Perlu tindakan" items={d.action} empty="Semua beres." more="/surat?status=perlu_tindakan" />
        <div className="stack">
          <section className="card">
            <div className="card-head"><h2>Benang aktif</h2><Link to="/benang" className="link small">Semua benang →</Link></div>
            {d.active_threads.length === 0 && <div className="empty">Belum ada benang aktif. Hubungkan surat yang saling berkaitan dari halaman detail surat.</div>}
            {d.active_threads.map(t => (
              <Link key={t.root_id} to={`/surat/${t.timeline[t.timeline.length - 1].id}`} className="tline">
                <div className="tline-top"><ThreadState s={t.state} /><span className="muted small">{t.stats.count} surat · terakhir {fmtDate(t.stats.last)}</span></div>
                <div className="tline-title">{t.title}</div>
                <div className="muted small">{t.position}</div>
              </Link>
            ))}
          </section>
          <Section title="Menunggu balasan" items={d.waiting} empty="Tidak ada surat keluar yang menunggu balasan." />
        </div>
      </div>

      <div className="grid2">
        <section className="card">
          <div className="card-head"><h2>8 minggu terakhir</h2>
            <span className="legend"><i className="lg-masuk" />Masuk <i className="lg-keluar" />Keluar</span></div>
          <div className="bars">
            {d.weeks.map(w => (
              <div key={w.week} className="bar-col" title={`Minggu ${fmtDate(w.week)}: ${w.masuk} masuk, ${w.keluar} keluar`}>
                <div className="bar-stack">
                  <div className="bar bar-keluar" style={{ height: `${(w.keluar / max) * 100}%` }} />
                  <div className="bar bar-masuk" style={{ height: `${(w.masuk / max) * 100}%` }} />
                </div>
                <span className="bar-lbl">{fmtDate(w.week).split(' ').slice(0, 2).join(' ')}</span>
              </div>
            ))}
          </div>
        </section>
        <Section title="Baru ditambahkan" items={d.recent.slice(0, 5)} empty="Belum ada surat. Mulai dengan mengunggah surat pertama." more="/surat" />
      </div>
    </div>
  )
}
