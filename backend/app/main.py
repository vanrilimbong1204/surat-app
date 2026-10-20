"""API Arsip Surat — satu port menyajikan API + frontend (build)."""
import json
import re
import shutil
import time
import uuid
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import ai, db, extract, ocr, threads
from .db import ARSIP, INBOX, ROOT, TRASH, connect, row_to_letter

try:  # foto HEIC dari iPhone
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass

app = FastAPI(title="Arsip Surat")
db.init()

STATUSES = {
    "perlu_tindakan": "Perlu tindakan",
    "menunggu_balasan": "Menunggu balasan",
    "selesai": "Selesai",
    "arsip": "Arsip / info saja",
}
RELATION_TYPES = list(threads.RELATION_LABEL)
LETTER_FIELDS = ["direction", "number", "letter_date", "io_date", "subject", "party",
                 "category", "status", "due_date", "notes"]


class LetterIn(BaseModel):
    token: Optional[str] = None
    direction: str
    number: str = ""
    letter_date: Optional[str] = None
    io_date: Optional[str] = None
    subject: str = ""
    party: str = ""
    category: str = "Lainnya"
    status: Optional[str] = None
    due_date: Optional[str] = None
    notes: str = ""
    highlights: Optional[list[str]] = None
    relate_to: Optional[int] = None        # buat relasi langsung (mis. "buat balasan")
    relate_type: Optional[str] = None


class LetterPatch(BaseModel):
    direction: Optional[str] = None
    number: Optional[str] = None
    letter_date: Optional[str] = None
    io_date: Optional[str] = None
    subject: Optional[str] = None
    party: Optional[str] = None
    category: Optional[str] = None
    status: Optional[str] = None
    due_date: Optional[str] = None
    notes: Optional[str] = None
    highlights: Optional[list[str]] = None


class RelationIn(BaseModel):
    from_id: int
    to_id: int
    type: str


def _get(conn, lid):
    row = conn.execute("SELECT * FROM letters WHERE id = ?", (lid,)).fetchone()
    if not row:
        raise HTTPException(404, "Surat tidak ditemukan")
    return row_to_letter(row)


def _slug(s):
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s.lower()).strip("-")
    return s[:50] or "surat"


def _archive_path(lid, direction, d, subject):
    try:
        y, m = d[:4], d[5:7]
        int(y), int(m)
    except (TypeError, ValueError):
        y, m = date.today().strftime("%Y"), date.today().strftime("%m")
    folder = ARSIP / y / m / direction.upper()
    folder.mkdir(parents=True, exist_ok=True)
    return folder / f"{lid:04d}_{_slug(subject)}.pdf"


# ---------------------------------------------------------------- meta / unggah

@app.get("/api/meta")
def meta():
    return {"statuses": STATUSES, "categories": extract.CATEGORY_LIST,
            "relation_types": RELATION_TYPES, "ai_available": ai.available(), "ai_model": ai.MODEL}


def _clean_inbox(max_age_hours=48):
    """Unggahan yang tidak jadi disimpan dibuang setelah 2 hari."""
    cutoff = time.time() - max_age_hours * 3600
    for p in INBOX.iterdir():
        if p.is_file() and p.stat().st_mtime < cutoff:
            p.unlink(missing_ok=True)


@app.post("/api/upload")
async def upload(files: list[UploadFile] = File(...)):
    _clean_inbox()
    token = uuid.uuid4().hex
    work = INBOX / token
    work.mkdir(parents=True)
    inputs = []
    for i, f in enumerate(files):
        suffix = Path(f.filename or "").suffix.lower() or ".jpg"
        p = work / f"in{i:03d}{suffix}"
        with open(p, "wb") as out:
            shutil.copyfileobj(f.file, out)
        inputs.append(p)
    out_pdf = INBOX / f"{token}.pdf"
    try:
        res = await run_in_threadpool(ocr.process, inputs, out_pdf)
    except ValueError as e:
        shutil.rmtree(work, ignore_errors=True)
        raise HTTPException(400, str(e))
    finally:
        shutil.rmtree(work, ignore_errors=True)

    text = res["text"]
    (INBOX / f"{token}.txt").write_text(text)
    h = ocr.file_hash(out_pdf)
    with connect() as conn:
        dup = conn.execute("SELECT id, subject FROM letters WHERE file_hash = ?", (h,)).fetchone()
        sug = extract.suggest(text)
        sug["related"] = _match_references(conn, sug["references"], None)
    return {"token": token, "pages": res["pages"], "method": res["method"],
            "text_chars": len(text.strip()), "suggestions": sug,
            "highlights": extract.highlights(text), "duplicate": dict(dup) if dup else None}


@app.get("/api/inbox/{token}.pdf")
def inbox_file(token: str):
    p = INBOX / f"{re.sub(r'[^a-f0-9]', '', token)}.pdf"
    if not p.exists():
        raise HTTPException(404)
    return FileResponse(p, media_type="application/pdf")


def _match_references(conn, refs, exclude_id):
    """Nomor surat yang dirujuk -> surat yang sudah ada di arsip."""
    if not refs:
        return []
    out = []
    for r in conn.execute("SELECT id, number, subject, party, direction FROM letters WHERE number != ''"):
        if r["id"] != exclude_id and any(extract.same_number(r["number"], ref) for ref in refs):
            out.append(dict(r))
    return out


# ---------------------------------------------------------------- surat

def _auto_close(conn, from_id, to_id, rtype):
    """Balasan menutup surat yang dibalas."""
    if rtype != "membalas":
        return
    target = _get(conn, to_id)
    if target["status"] in ("perlu_tindakan", "menunggu_balasan"):
        conn.execute("UPDATE letters SET status='selesai', updated_at=datetime('now','localtime') WHERE id=?",
                     (to_id,))


@app.post("/api/letters")
def create_letter(body: LetterIn):
    if body.direction not in ("masuk", "keluar"):
        raise HTTPException(400, "direction harus masuk/keluar")
    text, pdf = "", None
    if body.token:
        tok = re.sub(r"[^a-f0-9]", "", body.token)
        pdf = INBOX / f"{tok}.pdf"
        if not pdf.exists():
            raise HTTPException(400, "Unggahan sudah kedaluwarsa, unggah ulang")
        txt = INBOX / f"{tok}.txt"
        text = txt.read_text() if txt.exists() else ""
    status = body.status or ("perlu_tindakan" if body.direction == "masuk" else "menunggu_balasan")
    hl = body.highlights if body.highlights is not None else extract.highlights(text)
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO letters (direction, number, letter_date, io_date, subject, party, category, status,"
            " due_date, notes, ocr_text, highlights, highlights_source) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (body.direction, body.number, body.letter_date or None, body.io_date or None, body.subject,
             body.party, body.category, status, body.due_date or None, body.notes, text,
             json.dumps(hl, ensure_ascii=False), "auto"))
        lid = cur.lastrowid
        if pdf:
            dest = _archive_path(lid, body.direction, body.io_date or body.letter_date, body.subject)
            shutil.move(pdf, dest)
            (INBOX / f"{pdf.stem}.txt").unlink(missing_ok=True)
            from pypdf import PdfReader
            conn.execute("UPDATE letters SET file_path=?, file_hash=?, pages=? WHERE id=?",
                         (str(dest.relative_to(ROOT)), ocr.file_hash(dest), len(PdfReader(str(dest)).pages), lid))
        if body.relate_to and body.relate_type in RELATION_TYPES:
            _get(conn, body.relate_to)
            conn.execute("INSERT INTO relations (from_id, to_id, type) VALUES (?,?,?)",
                         (lid, body.relate_to, body.relate_type))
            _auto_close(conn, lid, body.relate_to, body.relate_type)
        return _detail(conn, lid)


@app.get("/api/letters")
def list_letters(q: str = "", direction: str = "", status: str = "", category: str = "", limit: int = 500):
    sql, args = "SELECT * FROM letters WHERE 1=1", []
    for term in q.split():
        like = f"%{term}%"
        sql += " AND (subject LIKE ? OR party LIKE ? OR number LIKE ? OR notes LIKE ? OR ocr_text LIKE ? OR highlights LIKE ?)"
        args += [like] * 6
    for col, val in (("direction", direction), ("status", status), ("category", category)):
        if val:
            sql += f" AND {col} = ?"
            args.append(val)
    sql += " ORDER BY COALESCE(io_date, letter_date, substr(created_at,1,10)) DESC, id DESC LIMIT ?"
    args.append(limit)
    with connect() as conn:
        comp = threads.components(conn)
        sizes = {}
        for r in comp.values():
            sizes[r] = sizes.get(r, 0) + 1
        out = []
        for row in conn.execute(sql, args):
            l = row_to_letter(row, full=False)
            l["thread_size"] = sizes.get(comp.get(l["id"]), 1)
            out.append(l)
        return out


def _detail(conn, lid):
    l = _get(conn, lid)
    rel = []
    for r in conn.execute(
            "SELECT r.*, l.subject, l.party, l.direction, l.number,"
            " COALESCE(l.io_date, l.letter_date) AS d FROM relations r"
            " JOIN letters l ON l.id = CASE WHEN r.from_id = ? THEN r.to_id ELSE r.from_id END"
            " WHERE r.from_id = ? OR r.to_id = ?", (lid, lid, lid)):
        r = dict(r)
        r["outgoing"] = r["from_id"] == lid
        r["other_id"] = r["to_id"] if r["outgoing"] else r["from_id"]
        rel.append(r)
    l["relations"] = rel
    ids = threads.members(conn, lid)
    l["thread"] = threads.with_ai(conn, threads.build(conn, ids)) if len(ids) > 1 else None
    sug = extract.suggest(l["ocr_text"]) if l["ocr_text"] else {"references": []}
    linked = {r["other_id"] for r in rel}
    l["suggested_relations"] = [s for s in _match_references(conn, sug["references"], lid) if s["id"] not in linked]
    return l


@app.get("/api/letters/{lid}")
def get_letter(lid: int):
    with connect() as conn:
        return _detail(conn, lid)


@app.patch("/api/letters/{lid}")
def patch_letter(lid: int, body: LetterPatch):
    data = body.model_dump(exclude_unset=True)
    with connect() as conn:
        _get(conn, lid)
        sets, args = [], []
        for k, v in data.items():
            if k == "highlights":
                sets += ["highlights = ?", "highlights_source = 'manual'"]
                args.append(json.dumps([p for p in v if p.strip()], ensure_ascii=False))
            elif k in LETTER_FIELDS:
                sets.append(f"{k} = ?")
                args.append(v if v != "" or k not in ("letter_date", "io_date", "due_date") else None)
        if sets:
            conn.execute(f"UPDATE letters SET {', '.join(sets)}, updated_at = datetime('now','localtime') WHERE id = ?",
                         args + [lid])
        return _detail(conn, lid)


@app.delete("/api/letters/{lid}")
def delete_letter(lid: int):
    """File dipindah ke data/sampah (tidak dimusnahkan), data dihapus dari register."""
    with connect() as conn:
        l = _get(conn, lid)
        if l["file_path"] and (ROOT / l["file_path"]).exists():
            shutil.move(ROOT / l["file_path"], TRASH / Path(l["file_path"]).name)
        conn.execute("DELETE FROM letters WHERE id = ?", (lid,))
    return {"ok": True}


@app.get("/api/letters/{lid}/file")
def letter_file(lid: int):
    with connect() as conn:
        l = _get(conn, lid)
    if not l["file_path"] or not (ROOT / l["file_path"]).exists():
        raise HTTPException(404, "Surat ini tidak punya file")
    return FileResponse(ROOT / l["file_path"], media_type="application/pdf",
                        headers={"Content-Disposition": f'inline; filename="{Path(l["file_path"]).name}"'})


@app.post("/api/letters/{lid}/highlights/auto")
def auto_highlights(lid: int):
    with connect() as conn:
        l = _get(conn, lid)
        conn.execute("UPDATE letters SET highlights=?, highlights_source='auto', updated_at=datetime('now','localtime') WHERE id=?",
                     (json.dumps(extract.highlights(l["ocr_text"]), ensure_ascii=False), lid))
        return _detail(conn, lid)


@app.post("/api/letters/{lid}/highlights/ai")
async def ai_highlights(lid: int):
    with connect() as conn:
        l = _get(conn, lid)
    if not l["ocr_text"].strip():
        raise HTTPException(400, "Surat ini belum punya teks (tidak ada file / OCR kosong)")
    try:
        pts = await run_in_threadpool(ai.letter_points, l["ocr_text"])
    except Exception as e:
        raise HTTPException(502, f"AI tidak bisa dihubungi: {e}")
    with connect() as conn:
        conn.execute("UPDATE letters SET highlights=?, highlights_source='ai', updated_at=datetime('now','localtime') WHERE id=?",
                     (json.dumps(pts, ensure_ascii=False), lid))
        return _detail(conn, lid)


# ---------------------------------------------------------------- relasi & benang

@app.post("/api/relations")
def add_relation(body: RelationIn):
    if body.type not in RELATION_TYPES:
        raise HTTPException(400, "Jenis relasi tidak dikenal")
    if body.from_id == body.to_id:
        raise HTTPException(400, "Surat tidak bisa berelasi dengan dirinya sendiri")
    with connect() as conn:
        _get(conn, body.from_id), _get(conn, body.to_id)
        exists = conn.execute("SELECT 1 FROM relations WHERE (from_id=? AND to_id=?) OR (from_id=? AND to_id=?)",
                              (body.from_id, body.to_id, body.to_id, body.from_id)).fetchone()
        if exists:
            raise HTTPException(400, "Kedua surat ini sudah berelasi")
        conn.execute("INSERT INTO relations (from_id, to_id, type) VALUES (?,?,?)",
                     (body.from_id, body.to_id, body.type))
        _auto_close(conn, body.from_id, body.to_id, body.type)
    return {"ok": True}


@app.delete("/api/relations/{rid}")
def delete_relation(rid: int):
    with connect() as conn:
        conn.execute("DELETE FROM relations WHERE id = ?", (rid,))
    return {"ok": True}


@app.get("/api/threads")
def list_threads():
    with connect() as conn:
        ts = threads.all_threads(conn)
    order = {"giliranmu": 0, "menunggu": 1, "berjalan": 2, "selesai": 3}
    ts.sort(key=lambda t: (order[t["state"]], -int((t["stats"]["last"] or "0").replace("-", "") or 0)))
    return ts


@app.post("/api/threads/{lid}/ai")
async def thread_ai(lid: int):
    with connect() as conn:
        ids = threads.members(conn, lid)
        if len(ids) < 2:
            raise HTTPException(400, "Surat ini belum punya relasi")
        summary = threads.build(conn, ids)
    try:
        text = await run_in_threadpool(ai.thread_narrative, summary["timeline"])
    except Exception as e:
        raise HTTPException(502, f"AI tidak bisa dihubungi: {e}")
    with connect() as conn:
        conn.execute("INSERT OR REPLACE INTO thread_summaries (root_id, signature, summary, created_at)"
                     " VALUES (?,?,?,datetime('now','localtime'))", (summary["root_id"], summary["signature"], text))
        return threads.with_ai(conn, summary)


# ---------------------------------------------------------------- beranda

@app.get("/api/dashboard")
def dashboard():
    today = date.today()
    month = today.strftime("%Y-%m")
    with connect() as conn:
        rows = [row_to_letter(r, full=False) for r in conn.execute("SELECT * FROM letters")]
        replied = {r["to_id"] for r in conn.execute("SELECT to_id FROM relations WHERE type='membalas'")}
        ts = threads.all_threads(conn)
    d = threads.eff_date
    open_ = [l for l in rows if l["status"] in ("perlu_tindakan", "menunggu_balasan")]
    overdue = [l for l in open_ if l["due_date"] and l["due_date"] < today.isoformat()]
    soon_limit = (today + timedelta(days=7)).isoformat()
    upcoming = sorted([l for l in open_ if l["due_date"] and today.isoformat() <= l["due_date"] <= soon_limit],
                      key=lambda l: l["due_date"])
    action = sorted([l for l in rows if l["status"] == "perlu_tindakan"],
                    key=lambda l: (l["due_date"] or "9999", d(l)))
    unreplied = [l for l in rows if l["direction"] == "masuk" and l["status"] == "perlu_tindakan" and l["id"] not in replied]
    waiting = sorted([l for l in rows if l["direction"] == "keluar" and l["status"] == "menunggu_balasan"], key=d)

    weeks = []
    for i in range(7, -1, -1):
        start = today - timedelta(days=today.weekday() + 7 * i)
        end = start + timedelta(days=7)
        inw = [l for l in rows if start.isoformat() <= d(l) < end.isoformat()]
        weeks.append({"week": start.isoformat(), "masuk": sum(l["direction"] == "masuk" for l in inw),
                      "keluar": sum(l["direction"] == "keluar" for l in inw)})

    return {
        "kpi": {
            "masuk_bulan_ini": sum(l["direction"] == "masuk" and d(l).startswith(month) for l in rows),
            "keluar_bulan_ini": sum(l["direction"] == "keluar" and d(l).startswith(month) for l in rows),
            "perlu_tindakan": len(action),
            "menunggu_balasan": len(waiting),
            "lewat_tenggat": len(overdue),
            "total": len(rows),
        },
        "overdue": sorted(overdue, key=lambda l: l["due_date"]),
        "upcoming": upcoming,
        "action": action[:10],
        "unreplied": unreplied[:10],
        "waiting": waiting[:10],
        "active_threads": [t for t in ts if t["state"] != "selesai"][:6],
        "recent": sorted(rows, key=lambda l: l["created_at"], reverse=True)[:8],
        "weeks": weeks,
    }


# ---------------------------------------------------------------- frontend

DIST = ROOT / "frontend" / "dist"
if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{path:path}")
    def spa(path: str):
        f = DIST / path
        if path and f.is_file():
            return FileResponse(f)
        return FileResponse(DIST / "index.html")
