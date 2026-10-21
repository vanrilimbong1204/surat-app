#!/usr/bin/env bash
# Pasang semua kebutuhan Arsip Surat (macOS / Linux). Aman dijalankan ulang.
set -euo pipefail
cd "$(dirname "$0")/.."

say() { printf '\n\033[1m==> %s\033[0m\n' "$*"; }

say "Program sistem: Tesseract OCR + Poppler (pdftotext/pdftoppm)"
if ! command -v tesseract >/dev/null || ! command -v pdftoppm >/dev/null; then
  if command -v brew >/dev/null; then
    brew install tesseract poppler
  elif command -v apt-get >/dev/null; then
    sudo apt-get update && sudo apt-get install -y tesseract-ocr poppler-utils
  else
    echo "Pasang 'tesseract' dan 'poppler' secara manual, lalu jalankan skrip ini lagi." >&2
    exit 1
  fi
fi

say "Python (butuh 3.10+)"
PY=""
for c in python3.13 python3.12 python3.11 python3.10 python3; do
  if command -v "$c" >/dev/null && "$c" -c 'import sys; sys.exit(sys.version_info < (3, 10))'; then PY="$c"; break; fi
done
[ -n "$PY" ] || { echo "Python 3.10+ tidak ditemukan (macOS: brew install python@3.12)." >&2; exit 1; }
[ -d .venv ] || "$PY" -m venv .venv
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements.txt

say "Node.js (butuh 20+) dan build tampilan"
command -v npm >/dev/null || { echo "Node.js tidak ditemukan (macOS: brew install node)." >&2; exit 1; }
(cd frontend && npm ci --silent && npm run build --silent)

[ -f .env ] || { cp .env.example .env; say "File .env dibuat dari .env.example — sesuaikan ARSIP_HOME kalau perlu"; }

say "Selesai. Jalankan: ./scripts/start.sh  lalu buka http://localhost:${PORT:-8100}"
