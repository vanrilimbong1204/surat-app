"""Logika simpan surat, dipakai bersama oleh form manual, unggah otomatis, dan folder pantau."""
import json
import re
import shutil
import uuid
from datetime import date
from pathlib import Path

from pypdf import PdfReader

from . import extract, ocr
from .db import ARSIP, INBOX, connect, get_setting


def slug(s):
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s.lower()).strip("-")
    return s[:50] or "surat"


def archive_path(lid, direction, d, subject):
    try:
        y, m = d[:4], d[5:7]
        int(y), int(m)
    except (TypeError, ValueError):
        y, m = date.today().strftime("%Y"), date.today().strftime("%m")
    folder = ARSIP / y / m / direction.upper()
    folder.mkdir(parents=True, exist_ok=True)
    return folder / f"{lid:04d}_{slug(subject)}.pdf"


def file_abspath(rel):
    return ARSIP / rel if rel else None


def match_references(conn, refs, exclude_id):
    """Nomor surat yang dirujuk -> surat yang sudah ada di arsip."""
    if not refs:
        return []
    out = []
    for r in conn.execute("SELECT id, number, subject, party, direction FROM letters WHERE number != ''"):
        if r["id"] != exclude_id and any(extract.same_number(r["number"], ref) for ref in refs):
            out.append(dict(r))
    return out


def auto_close(conn, to_id, rtype):
    """Balasan menutup surat yang dibalas."""
    if rtype != "membalas":
        return
    conn.execute("UPDATE letters SET status='selesai', updated_at=datetime('now','localtime')"
                 " WHERE id=? AND status IN ('perlu_tindakan','menunggu_balasan')", (to_id,))


def add_relation(conn, from_id, to_id, rtype):
    conn.execute("INSERT OR IGNORE INTO relations (from_id, to_id, type) VALUES (?,?,?)", (from_id, to_id, rtype))
    auto_close(conn, to_id, rtype)


def ocr_to_inbox(inputs: list[Path]):
    """OCR file mentah -> data/inbox/{token}.pdf + .txt. Return (token, hasil ocr)."""
    token = uuid.uuid4().hex
    out_pdf = INBOX / f"{token}.pdf"
    res = ocr.process(inputs, out_pdf)
    (INBOX / f"{token}.txt").write_text(res["text"])
    return token, res


def store(conn, f: dict, text: str, pdf: Path | None, highlights: list[str],
          needs_review=0, source="manual"):
    """Simpan satu surat; pindahkan PDF dari inbox ke arsip. Return id."""
    cur = conn.execute(
        "INSERT INTO letters (direction, number, letter_date, io_date, subject, party, category, status,"
        " due_date, notes, ocr_text, highlights, highlights_source, needs_review, source)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (f["direction"], f.get("number") or "", f.get("letter_date") or None, f.get("io_date") or None,
         f.get("subject") or "", f.get("party") or "", f.get("category") or "Lainnya", f["status"],
         f.get("due_date") or None, f.get("notes") or "", text,
         json.dumps(highlights, ensure_ascii=False), "auto", needs_review, source))
    lid = cur.lastrowid
    if pdf:
        dest = archive_path(lid, f["direction"], f.get("io_date") or f.get("letter_date"), f.get("subject") or "")
        shutil.move(pdf, dest)
        (INBOX / f"{pdf.stem}.txt").unlink(missing_ok=True)
        conn.execute("UPDATE letters SET file_path=?, file_hash=?, pages=? WHERE id=?",
                     (str(dest.relative_to(ARSIP)), ocr.file_hash(dest), len(PdfReader(str(dest)).pages), lid))
    return lid


def auto_fields(conn, text, forced_direction=None, io_date=None):
    """Isi semua data surat dari teksnya. Return (fields, highlights, catatan_keraguan)."""
    sug = extract.suggest(text)
    hl = extract.highlights(text)
    doubts = []

    owners = get_setting(conn, "owner_names", [])
    direction = forced_direction or extract.detect_direction(text, owners)
    if not direction:
        direction = "masuk"
        doubts.append("arah surat" if owners else "arah surat (nama kamu belum diatur di Pengaturan)")

    if direction == "keluar":
        party = extract.addressee(text) or ""
    else:
        party = sug["party"]
    related = match_references(conn, sug["references"], None)
    if related and related[0]["party"]:
        party = related[0]["party"]   # pakai nama pihak yang sudah konsisten di arsip
    if not party:
        doubts.append("pihak")

    subject = sug["subject"]
    if not subject:
        doubts.append("perihal")
        base = hl[0] if hl else ""
        subject = (base[:77].rstrip() + "…") if len(base) > 80 else base
    if not sug["letter_date"]:
        doubts.append("tanggal surat")

    if direction == "keluar":
        status = "menunggu_balasan"
    elif sug["due_date"] or any(extract.is_action(p) for p in hl):
        status = "perlu_tindakan"
    else:
        status = "arsip"     # sekadar pemberitahuan

    f = {"direction": direction, "number": sug["number"], "letter_date": sug["letter_date"],
         "io_date": io_date or date.today().isoformat(), "subject": subject, "party": party,
         "category": sug["category"], "status": status, "due_date": sug["due_date"],
         "notes": ("Perlu dicek: " + ", ".join(doubts)) if doubts else ""}
    return f, hl, related


def import_files(inputs: list[Path], source="otomatis", forced_direction=None, io_date=None):
    """Baca file -> simpan surat tanpa campur tangan user (ditandai 'perlu dicek')."""
    token, res = ocr_to_inbox(inputs)
    pdf = INBOX / f"{token}.pdf"
    text = res["text"]
    with connect() as conn:
        h = ocr.file_hash(pdf)
        dup = conn.execute("SELECT id, subject FROM letters WHERE file_hash = ?", (h,)).fetchone()
        if dup:
            pdf.unlink(missing_ok=True)
            (INBOX / f"{token}.txt").unlink(missing_ok=True)
            return {"id": dup["id"], "subject": dup["subject"], "duplicate": True}
        f, hl, related = auto_fields(conn, text, forced_direction, io_date)
        if len(text.strip()) < 40:
            f["notes"] = "Teks tidak terbaca — isi data secara manual. " + f["notes"]
        lid = store(conn, f, text, pdf, hl, needs_review=1, source=source)
        for r in related:
            add_relation(conn, lid, r["id"], "membalas" if r["direction"] != f["direction"] else "merujuk")
        return {"id": lid, "subject": f["subject"], "direction": f["direction"], "party": f["party"],
                "status": f["status"], "duplicate": False, "linked": len(related)}
