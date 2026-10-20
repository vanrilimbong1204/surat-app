import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api, type Letter, type Meta } from '../api'
import { LetterRow, STATUS_LABEL } from '../util'

export default function Register() {
  const [sp, setSp] = useSearchParams()
  const [meta, setMeta] = useState<Meta | null>(null)
  const [items, setItems] = useState<Letter[] | null>(null)
  const [q, setQ] = useState(sp.get('q') ?? '')
  const direction = sp.get('direction') ?? ''
  const status = sp.get('status') ?? ''
  const category = sp.get('category') ?? ''
  const review = sp.get('review') ?? ''

  useEffect(() => { api.meta().then(setMeta) }, [])
  useEffect(() => {
    const h = setTimeout(() => {
      api.letters({ q, direction, status, category, review }).then(setItems)
    }, 200)
    return () => clearTimeout(h)
  }, [q, direction, status, category, review])

  const setF = (k: string, v: string) => {
    const n = new URLSearchParams(sp)
    if (v) n.set(k, v); else n.delete(k)
    setSp(n, { replace: true })
  }

  return (
    <div className="page">
      <header className="page-head">
        <div><div className="eyebrow">Register</div><h1>Semua surat</h1></div>
        <Link to="/unggah" className="btn btn-primary">+ Unggah</Link>
      </header>
      <div className="filters">
        <input className="search" placeholder="Cari nomor, perihal, pihak, atau kata di dalam isi surat…" value={q} onChange={e => setQ(e.target.value)} />
        <div className="seg">
          {[['', 'Semua'], ['masuk', 'Masuk'], ['keluar', 'Keluar']].map(([v, l]) => (
            <button key={v} className={direction === v ? 'on' : ''} onClick={() => setF('direction', v)}>{l}</button>
          ))}
        </div>
        <select value={status} onChange={e => setF('status', e.target.value)}>
          <option value="">Semua status</option>
          {Object.entries(STATUS_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <select value={category} onChange={e => setF('category', e.target.value)}>
          <option value="">Semua kategori</option>
          {meta?.categories.map(c => <option key={c}>{c}</option>)}
        </select>
        <label className="check small"><input type="checkbox" checked={!!review} onChange={e => setF('review', e.target.checked ? '1' : '')} /> Perlu dicek</label>
      </div>
      <section className="card">
        {items === null ? <div className="loading">Memuat…</div>
          : items.length === 0 ? <div className="empty">Tidak ada surat yang cocok.</div>
            : <>
              <div className="muted small pad">{items.length} surat</div>
              {items.map(l => <LetterRow key={l.id} l={l} />)}
            </>}
      </section>
    </div>
  )
}
