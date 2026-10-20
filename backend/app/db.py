"""Penyimpanan: SQLite + struktur folder arsip."""
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
ARSIP = DATA / "arsip"
INBOX = DATA / "inbox"      # unggahan yang belum disimpan jadi surat
TRASH = DATA / "sampah"     # surat yang dihapus (file dipindah, tidak dimusnahkan)
DB_PATH = DATA / "surat.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS letters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    direction TEXT NOT NULL CHECK (direction IN ('masuk', 'keluar')),
    number TEXT NOT NULL DEFAULT '',
    letter_date TEXT,            -- tanggal yang tertulis di surat
    io_date TEXT,                -- tanggal diterima (masuk) / dikirim (keluar)
    subject TEXT NOT NULL DEFAULT '',
    party TEXT NOT NULL DEFAULT '',   -- pengirim (masuk) / tujuan (keluar)
    category TEXT NOT NULL DEFAULT 'Lainnya',
    status TEXT NOT NULL DEFAULT 'perlu_tindakan',
    due_date TEXT,
    notes TEXT NOT NULL DEFAULT '',
    ocr_text TEXT NOT NULL DEFAULT '',
    highlights TEXT NOT NULL DEFAULT '[]',
    highlights_source TEXT NOT NULL DEFAULT 'auto',   -- auto | ai | manual
    file_path TEXT,
    file_hash TEXT,
    pages INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
CREATE INDEX IF NOT EXISTS idx_letters_hash ON letters(file_hash);

-- from_id = surat yang lebih baru, to_id = surat yang dirujuk.
-- "from MEMBALAS to", "from MENINDAKLANJUTI to", dst.
CREATE TABLE IF NOT EXISTS relations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_id INTEGER NOT NULL REFERENCES letters(id) ON DELETE CASCADE,
    to_id INTEGER NOT NULL REFERENCES letters(id) ON DELETE CASCADE,
    type TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (from_id, to_id)
);

-- cache ringkasan AI per benang; signature berubah = ringkasan basi
CREATE TABLE IF NOT EXISTS thread_summaries (
    root_id INTEGER PRIMARY KEY,
    signature TEXT NOT NULL,
    summary TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""


def init():
    for d in (ARSIP, INBOX, TRASH):
        d.mkdir(parents=True, exist_ok=True)
    with connect() as c:
        c.executescript(SCHEMA)


@contextmanager
def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def row_to_letter(row, full=True):
    d = dict(row)
    d["highlights"] = json.loads(d.get("highlights") or "[]")
    if not full:
        d.pop("ocr_text", None)
    return d
