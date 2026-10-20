"""Penyimpanan: SQLite + struktur folder arsip."""
import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
INBOX = DATA / "inbox"      # unggahan yang belum disimpan jadi surat
DB_PATH = DATA / "surat.db"  # database tetap lokal (SQLite tidak aman disinkron iCloud)

# File surat disimpan di folder yang tersinkron cloud (Google Drive for desktop / iCloud)
# supaya bisa dibuka dari HP walau Mac mati dan otomatis ter-backup. Atur lewat env ARSIP_HOME.
_ICLOUD = Path.home() / "Library/Mobile Documents/com~apple~CloudDocs"
HOME = Path(os.getenv("ARSIP_HOME") or (_ICLOUD / "Arsip Surat" if _ICLOUD.exists() else DATA))
CLOUD = ("Google Drive" if "CloudStorage/GoogleDrive" in str(HOME)
         else "iCloud Drive" if "Mobile Documents" in str(HOME) else None)
ARSIP = HOME / "Arsip"              # Arsip/2026/10/MASUK/0001_perihal.pdf
DROP = HOME / "Kotak Masuk"         # taruh file di sini -> diimpor otomatis
TRASH = HOME / "Sampah"             # surat yang dihapus (file dipindah, tidak dimusnahkan)
BACKUP = HOME / "_backup"           # salinan harian database

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
    needs_review INTEGER NOT NULL DEFAULT 0,          -- 1 = diisi otomatis, belum dicek user
    source TEXT NOT NULL DEFAULT 'manual',            -- manual | otomatis | folder
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

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
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
    for d in (ARSIP, INBOX, TRASH, BACKUP, DROP, DROP / "Masuk", DROP / "Keluar"):
        d.mkdir(parents=True, exist_ok=True)
    with connect() as c:
        c.executescript(SCHEMA)


def get_setting(conn, key, default=None):
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return json.loads(row["value"]) if row else default


def set_setting(conn, key, value):
    conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, json.dumps(value)))


def backup_db():
    """Salinan harian database ke iCloud; simpan 14 terakhir."""
    dest = BACKUP / f"surat-{date.today().isoformat()}.db"
    if dest.exists():
        return
    src = sqlite3.connect(DB_PATH)
    dst = sqlite3.connect(dest)
    with dst:
        src.backup(dst)
    src.close(), dst.close()
    for old in sorted(BACKUP.glob("surat-*.db"))[:-14]:
        old.unlink()


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
