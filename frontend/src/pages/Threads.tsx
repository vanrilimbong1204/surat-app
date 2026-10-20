import { useEffect, useState } from 'react'
import { api, type Meta, type Thread } from '../api'
import ThreadPanel from '../components/ThreadPanel'

export default function Threads() {
  const [items, setItems] = useState<Thread[] | null>(null)
  const [meta, setMeta] = useState<Meta | null>(null)
  const [showDone, setShowDone] = useState(false)
  useEffect(() => { api.threads().then(setItems); api.meta().then(setMeta) }, [])
  const shown = (items ?? []).filter(t => showDone || t.state !== 'selesai')
  const done = (items ?? []).filter(t => t.state === 'selesai').length

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <div className="eyebrow">Benang surat</div>
          <h1>Perkembangan per perkara</h1>
          <p className="lead">Surat yang saling berelasi dikelompokkan jadi satu benang, lengkap dengan posisi terakhir dan kronologinya.</p>
        </div>
        {done > 0 && <label className="check"><input type="checkbox" checked={showDone} onChange={e => setShowDone(e.target.checked)} /> Tampilkan yang selesai ({done})</label>}
      </header>
      {items === null && <div className="loading">Memuat…</div>}
      {items !== null && shown.length === 0 && (
        <div className="card empty">Belum ada benang aktif. Buka detail surat lalu tambahkan relasi ("membalas", "menindaklanjuti", …) untuk membentuk benang.</div>
      )}
      <div className="stack">
        {shown.map(t => <ThreadPanel key={t.signature} thread={t} aiAvailable={!!meta?.ai_available} />)}
      </div>
    </div>
  )
}
