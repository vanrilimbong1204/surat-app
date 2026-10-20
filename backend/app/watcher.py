"""Folder pantau: file yang ditaruh di iCloud 'Arsip Surat/Kotak Masuk' diimpor otomatis.

Kotak Masuk/         -> arah surat ditebak dari isinya
Kotak Masuk/Masuk/   -> dipaksa surat masuk
Kotak Masuk/Keluar/  -> dipaksa surat keluar
Setelah diimpor file asli dipindah ke '_Sudah diimpor' (dihapus otomatis setelah 30 hari);
yang gagal dipindah ke '_Gagal' beserta catatan penyebabnya.
"""
import asyncio
import logging
import os
import shutil
import time
from datetime import date, datetime
from pathlib import Path

from fastapi.concurrency import run_in_threadpool

from . import db, service
from .ocr import IMAGE_EXT

log = logging.getLogger("arsip.watcher")
DONE = db.DROP / "_Sudah diimpor"
FAILED = db.DROP / "_Gagal"
INTERVAL = 20         # detik antar pemindaian
SETTLE = 15           # file harus diam sekian detik (sedang disalin/sinkron iCloud)
KEEP_DONE_DAYS = 30

state = {"last_scan": None, "recent": [], "running": False, "error": None}


def _candidates():
    out = []
    for folder, forced in ((db.DROP, None), (db.DROP / "Masuk", "masuk"), (db.DROP / "Keluar", "keluar")):
        if not folder.exists():
            continue
        for p in sorted(folder.iterdir()):
            if (p.is_file() and not p.name.startswith(".")
                    and (p.suffix.lower() in IMAGE_EXT or p.suffix.lower() == ".pdf")
                    and time.time() - p.stat().st_mtime > SETTLE):
                out.append((p, forced))
    return out


def _unique(dest: Path):
    i = 1
    while dest.exists():
        dest = dest.with_name(f"{dest.stem} ({i}){dest.suffix}")
        i += 1
    return dest


def _cleanup_done():
    cutoff = time.time() - KEEP_DONE_DAYS * 86400
    for p in DONE.glob("*"):
        if p.is_file() and p.stat().st_mtime < cutoff:
            p.unlink(missing_ok=True)


async def scan_once():
    DONE.mkdir(exist_ok=True)
    FAILED.mkdir(exist_ok=True)
    for path, forced in _candidates():
        received = date.fromtimestamp(path.stat().st_mtime).isoformat()
        try:
            res = await run_in_threadpool(service.import_files, [path], "folder", forced, received)
            done = _unique(DONE / path.name)
            shutil.move(path, done)
            os.utime(done)   # umur di '_Sudah diimpor' dihitung sejak diimpor
            entry = {**res, "file": path.name, "ok": True}
        except Exception as e:  # noqa: BLE001 — satu file gagal tidak boleh menghentikan yang lain
            log.exception("gagal impor %s", path)
            dest = _unique(FAILED / path.name)
            shutil.move(path, dest)
            dest.with_suffix(dest.suffix + ".txt").write_text(f"Gagal diimpor: {e}\n")
            entry = {"file": path.name, "ok": False, "error": str(e)}
        entry["at"] = datetime.now().isoformat(timespec="seconds")
        state["recent"] = [entry] + state["recent"][:19]
    state["last_scan"] = datetime.now().isoformat(timespec="seconds")


async def loop():
    state["running"] = True
    while True:
        try:
            await scan_once()
            await run_in_threadpool(db.backup_db)
            _cleanup_done()
            state["error"] = None
        except Exception as e:  # noqa: BLE001
            log.exception("pemindaian gagal")
            state["error"] = str(e)
        await asyncio.sleep(INTERVAL)
