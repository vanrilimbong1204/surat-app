import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { api, type LetterDetail, type Meta, type RefMatch, type UploadResult } from '../api'
import HighlightsEditor from '../components/HighlightsEditor'
import LetterForm, { emptyForm, type FormValue } from '../components/LetterForm'
import LetterPicker from '../components/LetterPicker'
import { DirBadge, RELATION_LABEL } from '../util'

const METHOD_LABEL: Record<string, string> = {
  'pdf-digital': 'PDF digital — teks dibaca langsung',
  'ocr-foto': 'Foto — teks dibaca dengan OCR',
  'ocr-scan': 'PDF hasil scan — teks dibaca dengan OCR',
}

interface Link_ { id: number; subject: string; party: string; direction: 'masuk' | 'keluar'; type: string }

export default function Upload() {
  const nav = useNavigate()
  const [sp] = useSearchParams()
  const replyTo = Number(sp.get('reply') || 0)
  const [meta, setMeta] = useState<Meta | null>(null)
  const [files, setFiles] = useState<File[]>([])
  const [res, setRes] = useState<UploadResult | null>(null)
  const [noFile, setNoFile] = useState(false)
  const [busy, setBusy] = useState('')
  const [err, setErr] = useState('')
  const [form, setForm] = useState<FormValue>(emptyForm(replyTo ? 'keluar' : 'masuk'))
  const [points, setPoints] = useState<string[]>([])
  const [links, setLinks] = useState<Link_[]>([])
  const [picking, setPicking] = useState(false)
  const pickRef = useRef<HTMLInputElement>(null)
  const camRef = useRef<HTMLInputElement>(null)

  useEffect(() => { api.meta().then(setMeta) }, [])
  useEffect(() => {
    if (!replyTo) return
    api.letter(replyTo).then((l: LetterDetail) => {
      setLinks([{ id: l.id, subject: l.subject, party: l.party, direction: l.direction, type: 'membalas' }])
      setForm(f => ({
        ...f, direction: l.direction === 'masuk' ? 'keluar' : 'masuk', party: l.party, category: l.category,
        subject: l.subject ? `Tanggapan: ${l.subject}` : '',
        status: l.direction === 'masuk' ? 'menunggu_balasan' : 'perlu_tindakan',
      }))
    })
  }, [replyTo])

  const addFiles = (fl: FileList | null) => { if (fl) setFiles(f => [...f, ...Array.from(fl)]) }

  async function process() {
    setBusy('Membaca surat… (OCR bisa butuh beberapa detik per halaman)'); setErr('')
    try {
      const r = await api.upload(files)
      setRes(r)
      const s = r.suggestions
      setForm(f => ({
        ...f,
        number: s.number || f.number, subject: f.subject && replyTo ? f.subject : (s.subject || f.subject),
        letter_date: s.letter_date || f.letter_date, due_date: s.due_date || f.due_date,
        party: f.party || s.related[0]?.party || s.party, category: f.category !== 'Lainnya' ? f.category : s.category,
      }))
      setPoints(r.highlights)
      setLinks(ls => [...ls, ...s.related.filter((m: RefMatch) => !ls.some(x => x.id === m.id))
        .map(m => ({ ...m, type: m.direction !== form.direction ? 'membalas' : 'merujuk' }))])
    } catch (e) { setErr((e as Error).message) }
    setBusy('')
  }

  async function save() {
    setBusy('Menyimpan…'); setErr('')
    try {
      const [first, ...rest] = links
      const body: Record<string, unknown> = { ...form, highlights: points, token: res?.token }
      if (first) { body.relate_to = first.id; body.relate_type = first.type }
      const l = await api.create(body)
      for (const x of rest) await api.addRelation(l.id, x.id, x.type)
      nav(`/surat/${l.id}`)
    } catch (e) { setErr((e as Error).message); setBusy('') }
  }

  const ready = res || noFile

  return (
    <div className="page">
      <header className="page-head">
        <div><div className="eyebrow">Unggah</div><h1>{replyTo ? 'Catat tanggapan' : 'Surat baru'}</h1>
          <p className="lead">Foto surat kertas atau pilih PDF. Isi surat dibaca otomatis, poin penting disorot, lalu kamu tinggal cek.</p></div>
      </header>

      {!ready && (
        <section className="card upload-card">
          <input ref={pickRef} type="file" multiple accept="application/pdf,image/*" hidden onChange={e => { addFiles(e.target.files); e.target.value = '' }} />
          <input ref={camRef} type="file" accept="image/*" capture="environment" hidden onChange={e => { addFiles(e.target.files); e.target.value = '' }} />
          <div className="drop" onDragOver={e => e.preventDefault()} onDrop={e => { e.preventDefault(); addFiles(e.dataTransfer.files) }}>
            <div className="drop-ic">✉</div>
            <div className="drop-title">Tarik file ke sini, atau</div>
            <div className="row-btns">
              <button className="btn btn-primary" onClick={() => camRef.current?.click()}>📷 Foto halaman</button>
              <button className="btn" onClick={() => pickRef.current?.click()}>Pilih PDF / gambar</button>
            </div>
            <div className="muted small">Surat beberapa halaman: foto satu per satu, urutannya mengikuti urutan foto. Di iPhone, “Pindai Dokumen” di app Files/Notes memberi hasil paling rapi.</div>
          </div>
          {files.length > 0 && (
            <div className="file-list">
              {files.map((f, i) => (
                <div key={i} className="file-item">
                  <span className="file-no">{i + 1}</span>
                  <span className="file-name">{f.name}</span>
                  <span className="muted small">{(f.size / 1024 / 1024).toFixed(1)} MB</span>
                  <button className="icon-btn" onClick={() => setFiles(files.filter((_, j) => j !== i))}>×</button>
                </div>
              ))}
              <button className="btn btn-primary btn-block" disabled={!!busy} onClick={process}>
                {busy || `Proses ${files.length} file →`}
              </button>
            </div>
          )}
          <button className="link small center" onClick={() => setNoFile(true)}>Catat tanpa file (mis. surat keluar yang tidak di-scan)</button>
          {err && <div className="error">{err}</div>}
        </section>
      )}

      {ready && (
        <div className="split">
          {res && (
            <section className="card preview-card">
              <div className="card-head"><h2>Pratinjau</h2><span className="muted small">{res.pages} hlm · {METHOD_LABEL[res.method] ?? res.method}</span></div>
              {res.text_chars < 40 && <div className="warn">Teks hampir tidak terbaca. Coba foto ulang dengan cahaya lebih terang & tegak lurus.</div>}
              {res.duplicate && <div className="warn">File ini sudah pernah disimpan: <Link to={`/surat/${res.duplicate.id}`}>{res.duplicate.subject || `Surat #${res.duplicate.id}`}</Link></div>}
              <iframe className="pdf" src={`/api/inbox/${res.token}.pdf`} title="pratinjau" />
            </section>
          )}
          <div className="stack">
            <section className="card">
              <div className="card-head"><h2>Data surat</h2>{res && <span className="muted small">diisi otomatis — mohon dicek</span>}</div>
              <LetterForm v={form} onChange={setForm} meta={meta} />
            </section>
            <section className="card">
              <div className="card-head"><h2>Poin yang dibahas</h2><span className="muted small">bisa diubah</span></div>
              <HighlightsEditor value={points} onChange={setPoints} />
            </section>
            <section className="card">
              <div className="card-head"><h2>Relasi</h2><button className="link small" onClick={() => setPicking(!picking)}>{picking ? 'Tutup' : '+ Hubungkan ke surat lain'}</button></div>
              {links.length === 0 && !picking && <div className="empty">Belum terhubung ke surat lain.</div>}
              {links.map((x, i) => (
                <div key={x.id} className="rel-new">
                  <span>Surat ini</span>
                  <select value={x.type} onChange={e => setLinks(links.map((y, j) => j === i ? { ...y, type: e.target.value } : y))}>
                    {Object.entries(RELATION_LABEL).map(([k, l]) => <option key={k} value={k}>{l.toLowerCase()}</option>)}
                  </select>
                  <DirBadge d={x.direction} />
                  <span className="rel-subj">{x.subject || `Surat #${x.id}`}</span>
                  <button className="icon-btn" onClick={() => setLinks(links.filter((_, j) => j !== i))}>×</button>
                </div>
              ))}
              {picking && <LetterPicker exclude={links.map(x => x.id)} onPick={l => {
                setLinks([...links, { id: l.id, subject: l.subject, party: l.party, direction: l.direction, type: l.direction !== form.direction ? 'membalas' : 'menindaklanjuti' }])
                setPicking(false)
              }} />}
            </section>
            {err && <div className="error">{err}</div>}
            <div className="row-btns end">
              <button className="btn" onClick={() => { setRes(null); setNoFile(false); setFiles([]) }}>Batal</button>
              <button className="btn btn-primary" disabled={!!busy} onClick={save}>{busy || 'Simpan surat'}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
