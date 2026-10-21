# Arsip Surat

Dashboard pribadi untuk mencatat **surat masuk & keluar**. Foto atau unggah surat, lalu sistem
membaca isinya (OCR), mengisi datanya sendiri, menyorot **poin yang dibahas**, dan menghubungkan
surat yang saling berkaitan jadi satu **benang** lengkap dengan ringkasan perkembangannya.

Semua berjalan di komputer sendiri — tanpa akun, tanpa server pihak ketiga, tanpa biaya AI.
Bisa dibuka dari HP lewat Wi-Fi rumah atau Tailscale.

## Fitur

- **Baca otomatis**: OCR lokal (Tesseract, bahasa Indonesia + Inggris) untuk foto, scan, dan PDF.
  Nomor, perihal, tanggal, tenggat ("paling lambat …"), pengirim/tujuan, kategori, dan arah
  masuk/keluar diisi sendiri; hasilnya ditandai **perlu dicek**.
- **Poin yang dibahas**: kalimat penting (permintaan, tenggat, nominal Rp, sanksi) disorot; bisa diedit.
- **Relasi & benang**: membalas / menindaklanjuti / merujuk / meralat. Nomor surat yang disebut di isi
  surat otomatis ditautkan ke arsip. Tiap benang punya posisi sekarang (giliranmu / menunggu pihak lain /
  selesai), kronologi, dan hal yang masih harus diperhatikan.
- **Kotak Masuk folder**: taruh file di folder `Kotak Masuk` (mis. di Google Drive/iCloud) — diimpor sendiri.
- **Beranda**: perlu tindakan, tenggat, menunggu balasan, benang aktif, grafik 8 minggu.
- **AI opsional**: tombol "Ringkas dengan AI" bila ada endpoint OpenAI-compatible di `.env`.

## Memasang

Butuh macOS atau Linux (Windows: pakai WSL), plus Python 3.10+ dan Node.js 20+.

```bash
git clone https://github.com/vanrilimbong1204/surat-app.git
cd surat-app
./scripts/setup.sh
./scripts/start.sh
```

Buka `http://localhost:8100`, lalu di menu **Pengaturan** isi **Nama kamu** — dipakai menebak arah surat
(namamu di bagian "Yth./Kepada" = surat masuk; di kop/tanda tangan = surat keluar).

`setup.sh` memasang Tesseract & Poppler (lewat Homebrew atau apt), membuat virtualenv Python, dan
mem-build tampilan. Aman dijalankan ulang setelah `git pull`.

### Jalan otomatis saat login (macOS)

```bash
./scripts/install-autostart.sh              # pasang
./scripts/install-autostart.sh --uninstall  # lepas
```

Log ada di `~/Library/Logs/arsipsurat.log`.

## Penyimpanan

Atur di `.env` (salin dari `.env.example`):

| Variabel | Fungsi |
|---|---|
| `ARSIP_HOME` | Folder file surat. Kosong = iCloud Drive (kalau ada) atau `data/`. |
| `AI_BASE_URL`, `AI_API_KEY`, `AI_MODEL` | Opsional, untuk tombol ringkas AI. |
| `PORT`, `HOST` | Opsional, default `8100` dan `0.0.0.0`. |

Isi folder `ARSIP_HOME`:

```
Arsip Surat/
├── Arsip/2026/10/MASUK/0001_perihal.pdf   ← PDF ber-lapisan-teks (bisa dicari)
├── Kotak Masuk/                           ← taruh file di sini → diimpor otomatis
│   ├── Masuk/  Keluar/                    ← paksa arah surat
│   └── _Sudah diimpor/  _Gagal/
├── Sampah/                                ← surat yang dihapus dari register
└── _backup/                               ← salinan harian database (14 terakhir)
```

Database (`data/surat.db`) sengaja disimpan lokal — SQLite bisa rusak bila disinkron cloud;
salinannya dibackup harian ke `_backup/`.

**Google Drive**: pasang *Google Drive for desktop*, lalu set
`ARSIP_HOME=~/Library/CloudStorage/GoogleDrive-<email>/My Drive/Arsip Surat`. Dari HP, scan langsung lewat
app Google Drive (+ → Pindai) ke folder `Kotak Masuk`. Untuk akun Google lain, bagikan folder
`Arsip Surat` sebagai Editor.

## Akses dari HP

- Wi-Fi yang sama: `http://<IP-komputer>:8100`
- Dari mana saja: pasang [Tailscale](https://tailscale.com) di komputer & HP (akun yang sama), buka
  `http://<nama-komputer>:8100`. Untuk HTTPS + "Add to Home Screen": `tailscale serve --bg 8100`.

## Pengembangan

```
backend/app/
  main.py      API FastAPI + menyajikan build frontend
  service.py   simpan surat, impor otomatis, relasi
  extract.py   ekstraksi berbasis aturan: poin, metadata, arah surat, rujukan
  ocr.py       foto/PDF → PDF ber-lapisan-teks + teks (Tesseract, Poppler)
  threads.py   benang surat & ringkasan perkembangan
  watcher.py   pemantau folder Kotak Masuk + backup harian
  ai.py        AI opsional
frontend/src/  React + TypeScript (Vite), PWA responsif
```

Mode pengembangan (auto-reload):

```bash
.venv/bin/uvicorn app.main:app --app-dir backend --port 8100 --reload --reload-dir backend
cd frontend && npm run dev     # http://localhost:5180, /api diteruskan ke 8100
```

Kontribusi: buat branch, commit dengan pesan jelas, lalu buka Pull Request.
