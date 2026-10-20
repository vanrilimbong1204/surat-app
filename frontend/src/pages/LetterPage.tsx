import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api, type Letter, type LetterDetail, type Meta, type Status } from '../api'
import HighlightsEditor from '../components/HighlightsEditor'
import LetterForm, { type FormValue } from '../components/LetterForm'
import LetterPicker from '../components/LetterPicker'
import ThreadPanel from '../components/ThreadPanel'
import { DirBadge, DueChip, RELATION_INVERSE, RELATION_LABEL, STATUS_LABEL, effDate, fmtDate } from '../util'

const SOURCE_LABEL = { auto: 'otomatis', ai: 'dibuat AI', manual: 'diedit manual' }

export default function LetterPage() {
  const id = Number(useParams().id)
  const nav = useNavigate()
  const [l, setL] = useState<LetterDetail | null>(null)
  const [meta, setMeta] = useState<Meta | null>(null)
  const [edit, setEdit] = useState<FormValue | null>(null)
  const [pts, setPts] = useState<string[] | null>(null)
  const [picking, setPicking] = useState(false)
  const [relType, setRelType] = useState('membalas')
  const [busy, setBusy] = useState('')
  const [err, setErr] = useState('')
  const [showText, setShowText] = useState(false)

  const load = useCallback(() => api.letter(id).then(setL).catch(e => setErr(e.message)), [id])
  useEffect(() => { setL(null); setEdit(null); setPts(null); load() }, [load])
  useEffect(() => { api.meta().then(setMeta) }, [])

  async function run(label: string, fn: () => Promise<unknown>) {
    setBusy(label); setErr('')
    try { await fn() } catch (e) { setErr((e as Error).message) }
    setBusy('')
  }

  if (err && !l) return <div className="page"><div className="error">{err}</div></div>
  if (!l) return <div className="loading">Memuat…</div>

  const startEdit = () => setEdit({
    direction: l.direction, number: l.number, letter_date: l.letter_date ?? '', io_date: l.io_date ?? '',
    subject: l.subject, party: l.party, category: l.category, status: l.status, due_date: l.due_date ?? '', notes: l.notes,
  })

  const addRel = (o: Letter) => run('Menghubungkan…', async () => {
    // surat yang lebih baru "membalas / menindaklanjuti" surat yang lebih lama
    const thisNewer = effDate(l) >= effDate(o)
    await api.addRelation(thisNewer ? l.id : o.id, thisNewer ? o.id : l.id, relType)
    setPicking(false); await load()
  })

  return (
    <div className="page">
      <div className="crumb"><Link to="/surat" className="link small">← Register</Link></div>
      <header className="page-head letter-head">
        <div>
          <div className="row-chips"><DirBadge d={l.direction} /><span className="cat">{l.category}</span><DueChip due={l.due_date} status={l.status} /></div>
          <h1>{l.subject || '(tanpa perihal)'}</h1>
          <div className="muted">{l.direction === 'masuk' ? 'Dari' : 'Kepada'} <b>{l.party || '—'}</b>
            {l.number && <> · No. {l.number}</>} · {fmtDate(l.letter_date)}</div>
        </div>
        <div className="head-actions">
          <select className={`status-select st-${l.status}`} value={l.status}
            onChange={e => run('', async () => setL(await api.patch(l.id, { status: e.target.value as Status })))}>
            {Object.entries(STATUS_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
          {l.file_path && <a className="btn only-mobile" href={`/api/letters/${l.id}/file`} target="_blank" rel="noreferrer">📄 Dokumen</a>}
          <button className="btn btn-primary" onClick={() => nav(`/unggah?reply=${l.id}`)}>
            {l.direction === 'masuk' ? '↩ Catat balasan' : '↩ Catat tanggapan masuk'}
          </button>
        </div>
      </header>
      {err && <div className="error">{err}</div>}
      {!!l.needs_review && (
        <div className="review-bar">
          <div><b>Diisi otomatis.</b> Cek sekilas arah surat, pihak, perihal, dan tanggalnya.
            {l.notes.startsWith('Perlu dicek') || l.notes.startsWith('Teks tidak') ? <span className="muted"> {l.notes}</span> : null}</div>
          <div className="row-btns">
            <button className="btn btn-sm" onClick={() => { startEdit(); setTimeout(() => document.getElementById('data-surat')?.scrollIntoView({ behavior: 'smooth' }), 50) }}>Perbaiki</button>
            <button className="btn btn-sm btn-primary" onClick={() => run('', async () => setL(await api.patch(l.id, { needs_review: 0 })))}>✓ Sudah benar</button>
          </div>
        </div>
      )}

      <div className="split letter-split">
        <div className="stack">
          <section className="card highlight-card">
            <div className="card-head">
              <h2>Poin yang dibahas</h2>
              <span className="muted small">{SOURCE_LABEL[l.highlights_source]}</span>
            </div>
            {pts === null ? (
              <>
                {l.highlights.length === 0 ? <div className="empty">Belum ada poin. Tambahkan manual{l.ocr_text ? ' atau ekstrak dari isi surat' : ''}.</div>
                  : <ul className="hl-list">{l.highlights.map((p, i) => <li key={i}>{p}</li>)}</ul>}
                <div className="row-btns">
                  <button className="btn btn-sm" onClick={() => setPts(l.highlights)}>Edit poin</button>
                  {l.ocr_text && <button className="btn btn-sm btn-ghost" disabled={!!busy}
                    onClick={() => run('Mengekstrak…', async () => setL(await api.autoHighlights(l.id)))}>↻ Ekstrak ulang</button>}
                  {l.ocr_text && meta?.ai_available && <button className="btn btn-sm btn-ghost" disabled={!!busy}
                    onClick={() => run('AI sedang membaca…', async () => setL(await api.aiHighlights(l.id)))}>
                    {busy === 'AI sedang membaca…' ? busy : '✦ Ringkas dengan AI'}</button>}
                </div>
              </>
            ) : (
              <>
                <HighlightsEditor value={pts} onChange={setPts} />
                <div className="row-btns end">
                  <button className="btn btn-sm" onClick={() => setPts(null)}>Batal</button>
                  <button className="btn btn-sm btn-primary" onClick={() => run('', async () => { setL(await api.patch(l.id, { highlights: pts })); setPts(null) })}>Simpan poin</button>
                </div>
              </>
            )}
          </section>

          {l.thread ? <ThreadPanel key={l.thread.signature} thread={l.thread} currentId={l.id} aiAvailable={!!meta?.ai_available} /> : null}

          <section className="card">
            <div className="card-head"><h2>Relasi</h2>
              <button className="link small" onClick={() => setPicking(!picking)}>{picking ? 'Tutup' : '+ Hubungkan'}</button></div>
            {l.relations.length === 0 && !picking && <div className="empty">Surat ini belum terhubung ke surat lain.</div>}
            {l.relations.map(r => (
              <div key={r.id} className="rel">
                <span className="rel-type">{r.outgoing ? RELATION_LABEL[r.type] : RELATION_INVERSE[r.type]}</span>
                <DirBadge d={r.direction} />
                <Link to={`/surat/${r.other_id}`} className="rel-subj">{r.subject || `Surat #${r.other_id}`}</Link>
                <span className="muted small">{r.party} · {fmtDate(r.d)}</span>
                <button className="icon-btn" title="Hapus relasi" onClick={() => run('', async () => { await api.delRelation(r.id); await load() })}>×</button>
              </div>
            ))}
            {l.suggested_relations.length > 0 && (
              <div className="suggest">
                <span className="eyebrow">Disebut di isi surat ini</span>
                {l.suggested_relations.map(s => (
                  <div key={s.id} className="rel">
                    <DirBadge d={s.direction} /><span className="rel-subj">{s.subject} <span className="muted small">No. {s.number}</span></span>
                    <button className="btn btn-sm" onClick={() => run('', async () => { await api.addRelation(l.id, s.id, s.direction !== l.direction ? 'membalas' : 'merujuk'); await load() })}>Hubungkan</button>
                  </div>
                ))}
              </div>
            )}
            {picking && (
              <div className="rel-picker">
                <label className="f">Jenis relasi
                  <select value={relType} onChange={e => setRelType(e.target.value)}>
                    {Object.entries(RELATION_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                  </select></label>
                <div className="muted small">Surat yang lebih baru otomatis jadi yang “{relType}” surat yang lebih lama.</div>
                <LetterPicker exclude={[l.id, ...l.relations.map(r => r.other_id)]} onPick={addRel} />
              </div>
            )}
          </section>

          <section className="card" id="data-surat">
            <div className="card-head"><h2>Data surat</h2>{!edit && <button className="link small" onClick={startEdit}>Edit</button>}</div>
            {edit ? (
              <>
                <LetterForm v={edit} onChange={setEdit} meta={meta} />
                <div className="row-btns end">
                  <button className="btn btn-sm" onClick={() => setEdit(null)}>Batal</button>
                  <button className="btn btn-sm btn-primary" onClick={() => run('', async () => { setL(await api.patch(l.id, { ...edit, needs_review: 0 })); setEdit(null) })}>Simpan</button>
                </div>
              </>
            ) : (
              <dl className="kv">
                <dt>Nomor</dt><dd>{l.number || '—'}</dd>
                <dt>Tanggal surat</dt><dd>{fmtDate(l.letter_date)}</dd>
                <dt>{l.direction === 'masuk' ? 'Diterima' : 'Dikirim'}</dt><dd>{fmtDate(l.io_date)}</dd>
                <dt>Tenggat</dt><dd>{fmtDate(l.due_date)}</dd>
                <dt>Kategori</dt><dd>{l.category}</dd>
                <dt>File</dt><dd>{l.file_path ? <span className="mono small">{l.file_path.replace('data/arsip/', '')}</span> : '—'}</dd>
                {l.notes && <><dt>Catatan</dt><dd>{l.notes}</dd></>}
              </dl>
            )}
          </section>

          {l.ocr_text && (
            <section className="card">
              <div className="card-head"><h2>Teks surat</h2><button className="link small" onClick={() => setShowText(!showText)}>{showText ? 'Sembunyikan' : 'Tampilkan'}</button></div>
              {showText && <pre className="ocr">{l.ocr_text}</pre>}
            </section>
          )}

          <div className="row-btns">
            <button className="btn btn-danger btn-sm" onClick={() => {
              if (confirm('Hapus surat ini dari register? File dipindah ke folder data/sampah, tidak dimusnahkan.'))
                run('', async () => { await api.remove(l.id); nav('/surat') })
            }}>Hapus surat</button>
          </div>
        </div>

        {l.file_path && (
          <section className="card preview-card sticky">
            <div className="card-head"><h2>Dokumen</h2>
              <a className="link small" href={`/api/letters/${l.id}/file`} target="_blank" rel="noreferrer">Buka penuh ↗</a></div>
            <iframe className="pdf" src={`/api/letters/${l.id}/file`} title="dokumen" />
          </section>
        )}
      </div>
    </div>
  )
}
