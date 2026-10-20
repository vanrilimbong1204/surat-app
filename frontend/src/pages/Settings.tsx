import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, type Settings as S } from '../api'

const short = (p: string) => p.replace(/^.*com~apple~CloudDocs/, 'iCloud Drive').replace(/^\/Users\/[^/]+/, '~')

export default function Settings() {
  const [s, setS] = useState<S | null>(null)
  const [names, setNames] = useState('')
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    const load = () => api.settings().then(r => { setS(r); setNames(n => n || r.owner_names.join('\n')) })
    load()
    const t = setInterval(load, 10000)   // status folder pantau
    return () => clearInterval(t)
  }, [])
  if (!s) return <div className="loading">Memuat…</div>

  async function save() {
    setS(await api.saveSettings(names.split('\n')))
    setSaved(true); setTimeout(() => setSaved(false), 2000)
  }

  return (
    <div className="page narrow">
      <header className="page-head"><div><div className="eyebrow">Pengaturan</div><h1>Pengaturan</h1></div></header>

      <section className="card">
        <div className="card-head"><h2>Nama kamu</h2></div>
        <p className="muted small top0">Dipakai untuk menebak arah surat: kalau namamu ada di bagian “Yth./Kepada” berarti <b>surat masuk</b>,
          kalau ada di kop atau tanda tangan berarti <b>surat keluar</b>. Satu nama per baris; tambahkan variasi yang sering dipakai (mis. tanpa gelar).</p>
        <textarea rows={3} value={names} onChange={e => setNames(e.target.value)} placeholder="Nama lengkap sesuai surat" />
        <div className="row-btns end">
          {saved && <span className="muted small">Tersimpan ✓</span>}
          <button className="btn btn-primary btn-sm" onClick={save}>Simpan</button>
        </div>
        {s.owner_names.length === 0 && <div className="warn">Nama belum diatur — arah surat yang diimpor otomatis akan dianggap “masuk” dan ditandai perlu dicek.</div>}
      </section>

      <section className="card">
        <div className="card-head"><h2>Kotak Masuk otomatis</h2>
          <span className={`tstate ${s.watcher.running && !s.watcher.error ? 'ts-selesai' : 'ts-giliranmu'}`}>{s.watcher.running && !s.watcher.error ? 'Aktif' : 'Bermasalah'}</span></div>
        <p className="muted small top0">Taruh foto/PDF surat di folder ini — dari iPhone (app Files → “Pindai Dokumen” → simpan ke folder ini) atau dari Finder di Mac.
          Dalam ±30 detik surat dibaca, diisi, dan disimpan sendiri.</p>
        <div className="path">{short(s.storage.kotak_masuk)}</div>
        <ul className="small muted list">
          <li><b>Kotak Masuk/</b> — arah masuk/keluar ditebak dari isi surat</li>
          <li><b>Kotak Masuk/Masuk/</b> dan <b>Kotak Masuk/Keluar/</b> — kalau ingin menentukan arahnya sendiri</li>
          <li>File asli dipindah ke <b>_Sudah diimpor</b> (dihapus otomatis setelah 30 hari); yang gagal ke <b>_Gagal</b></li>
        </ul>
        {s.watcher.error && <div className="error">{s.watcher.error}</div>}
        <div className="muted small">Pemindaian terakhir: {s.watcher.last_scan?.replace('T', ' ') ?? '—'}</div>
        {s.watcher.recent.length > 0 && (
          <div className="recent">
            {s.watcher.recent.slice(0, 8).map((r, i) => (
              <div key={i} className="recent-item">
                <span className={r.ok ? 'ok' : 'fail'}>{r.ok ? (r.duplicate ? '=' : '✓') : '!'}</span>
                {r.ok && r.id ? <Link to={`/surat/${r.id}`} className="link">{r.subject || r.file}</Link> : <span>{r.file}</span>}
                <span className="muted small">{r.ok ? (r.duplicate ? 'duplikat' : r.direction) : r.error}</span>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="card">
        <div className="card-head"><h2>Lokasi penyimpanan</h2></div>
        <dl className="kv">
          <dt>File surat (PDF)</dt><dd className="mono small">{short(s.storage.arsip)}/TAHUN/BULAN/MASUK|KELUAR</dd>
          <dt>Database</dt><dd className="mono small">{short(s.storage.database)}</dd>
          <dt>Backup database</dt><dd className="mono small">{short(s.storage.backup)} <span className="muted">(harian, 14 terakhir)</span></dd>
          <dt>Surat dihapus</dt><dd className="mono small">{short(s.storage.sampah)}</dd>
        </dl>
        {s.storage.icloud && <p className="muted small">File surat ada di iCloud Drive: ikut ter-backup dan bisa dibuka dari app Files di iPhone walau Mac sedang mati.</p>}
      </section>
    </div>
  )
}
