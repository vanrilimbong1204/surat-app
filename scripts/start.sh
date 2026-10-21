#!/usr/bin/env bash
# Jalankan Arsip Surat (API + tampilan). Bisa diakses dari HP lewat Tailscale/Wi-Fi.
cd "$(dirname "$0")/.."
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"   # tesseract, pdftotext, pdftoppm
exec .venv/bin/uvicorn app.main:app --app-dir backend --host "${HOST:-0.0.0.0}" --port "${PORT:-8100}"
