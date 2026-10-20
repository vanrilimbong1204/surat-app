export type Direction = 'masuk' | 'keluar'
export type Status = 'perlu_tindakan' | 'menunggu_balasan' | 'selesai' | 'arsip'

export interface Letter {
  id: number
  direction: Direction
  number: string
  letter_date: string | null
  io_date: string | null
  subject: string
  party: string
  category: string
  status: Status
  due_date: string | null
  notes: string
  highlights: string[]
  highlights_source: 'auto' | 'ai' | 'manual'
  needs_review: number
  source: 'manual' | 'otomatis' | 'folder'
  file_path: string | null
  pages: number
  created_at: string
  updated_at: string
  thread_size?: number
}

export interface Relation {
  id: number
  from_id: number
  to_id: number
  type: string
  outgoing: boolean
  other_id: number
  subject: string
  party: string
  direction: Direction
  number: string
  d: string | null
}

export interface TimelineItem {
  id: number
  date: string
  direction: Direction
  party: string
  subject: string
  status: Status
  due_date: string | null
  points: string[]
  relation: string
}

export interface Thread {
  root_id: number
  title: string
  parties: string[]
  stats: { count: number; masuk: number; keluar: number; start: string; last: string; span_days: number | null }
  state: 'giliranmu' | 'menunggu' | 'berjalan' | 'selesai'
  position: string
  next_due: string | null
  open_points: string[]
  story: string[]
  timeline: TimelineItem[]
  signature: string
  ai: { text: string; created_at: string; stale: boolean } | null
}

export interface RefMatch { id: number; number: string; subject: string; party: string; direction: Direction }

export interface LetterDetail extends Letter {
  ocr_text: string
  relations: Relation[]
  thread: Thread | null
  suggested_relations: RefMatch[]
}

export interface Meta {
  statuses: Record<Status, string>
  categories: string[]
  relation_types: string[]
  ai_available: boolean
  ai_model: string
}

export interface UploadResult {
  token: string
  pages: number
  method: string
  text_chars: number
  suggestions: {
    number: string; subject: string; letter_date: string | null; due_date: string | null
    party: string; category: string; references: string[]; related: RefMatch[]
  }
  highlights: string[]
  duplicate: { id: number; subject: string } | null
}

export interface ImportResult {
  ok: boolean; file: string; error?: string
  id?: number; subject?: string; direction?: Direction; party?: string; status?: Status
  duplicate?: boolean; linked?: number; at?: string
}

export interface Settings {
  owner_names: string[]
  storage: { arsip: string; kotak_masuk: string; sampah: string; backup: string; database: string; cloud: string | null }
  watcher: { last_scan: string | null; recent: ImportResult[]; running: boolean; error: string | null }
}

export interface Dashboard {
  kpi: Record<'masuk_bulan_ini' | 'keluar_bulan_ini' | 'perlu_tindakan' | 'menunggu_balasan' | 'lewat_tenggat' | 'perlu_dicek' | 'total', number>
  review: Letter[]
  overdue: Letter[]
  upcoming: Letter[]
  action: Letter[]
  unreplied: Letter[]
  waiting: Letter[]
  active_threads: Thread[]
  recent: Letter[]
  weeks: { week: string; masuk: number; keluar: number }[]
}

async function req<T>(url: string, init?: RequestInit): Promise<T> {
  const r = await fetch(url, init)
  if (!r.ok) {
    let msg = `${r.status} ${r.statusText}`
    try { msg = (await r.json()).detail ?? msg } catch { /* bukan json */ }
    throw new Error(msg)
  }
  return r.json()
}

const json = (method: string, body: unknown): RequestInit => ({
  method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
})

export const api = {
  meta: () => req<Meta>('/api/meta'),
  dashboard: () => req<Dashboard>('/api/dashboard'),
  letters: (params: Record<string, string>) => req<Letter[]>('/api/letters?' + new URLSearchParams(params)),
  letter: (id: number) => req<LetterDetail>(`/api/letters/${id}`),
  create: (body: Record<string, unknown>) => req<LetterDetail>('/api/letters', json('POST', body)),
  patch: (id: number, body: Partial<Letter>) => req<LetterDetail>(`/api/letters/${id}`, json('PATCH', body)),
  remove: (id: number) => req<{ ok: boolean }>(`/api/letters/${id}`, { method: 'DELETE' }),
  autoHighlights: (id: number) => req<LetterDetail>(`/api/letters/${id}/highlights/auto`, { method: 'POST' }),
  aiHighlights: (id: number) => req<LetterDetail>(`/api/letters/${id}/highlights/ai`, { method: 'POST' }),
  addRelation: (from_id: number, to_id: number, type: string) => req('/api/relations', json('POST', { from_id, to_id, type })),
  delRelation: (id: number) => req(`/api/relations/${id}`, { method: 'DELETE' }),
  threads: () => req<Thread[]>('/api/threads'),
  threadAi: (id: number) => req<Thread>(`/api/threads/${id}/ai`, { method: 'POST' }),
  settings: () => req<Settings>('/api/settings'),
  saveSettings: (owner_names: string[]) => req<Settings>('/api/settings', json('PUT', { owner_names })),
  uploadAuto: (files: File[], oneLetter: boolean) => {
    const fd = new FormData()
    files.forEach(f => fd.append('files', f))
    fd.append('one_letter', String(oneLetter))
    return req<ImportResult[]>('/api/upload/auto', { method: 'POST', body: fd })
  },
  upload: (files: File[]) => {
    const fd = new FormData()
    files.forEach(f => fd.append('files', f))
    return req<UploadResult>('/api/upload', { method: 'POST', body: fd })
  },
}
