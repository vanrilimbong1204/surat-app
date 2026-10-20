#!/bin/zsh
# Jalankan Arsip Surat (API + tampilan) di port 8100, bisa diakses dari HP lewat Tailscale/Wi-Fi.
cd "$(dirname "$0")/.."
export PATH="/opt/homebrew/bin:$PATH"   # tesseract, pdftotext, pdftoppm
exec .venv/bin/uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8100
