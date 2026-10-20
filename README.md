# Arsip Surat

Dashboard pribadi untuk surat masuk & keluar: unggah scan/PDF, isi surat dibaca otomatis (OCR),
poin yang dibahas disorot, surat yang saling berkaitan dihubungkan jadi **benang** lengkap dengan
ringkasan perkembangannya.

## Menjalankan

```bash
./scripts/start.sh
```

Buka `http://localhost:8100`. Semua data ada di `data/`:

| Lokasi | Isi |
|---|---|
| `data/surat.db` | database (SQLite) |
| `data/arsip/TAHUN/BULAN/MASUK|KELUAR/` | PDF surat (sudah ber-lapisan-teks, bisa dicari) |
| `data/sampah/` | file surat yang dihapus dari register |
| `data/inbox/` | unggahan yang belum disimpan (dibersihkan otomatis setelah 2 hari) |

Backup cukup salin folder `data/`.

### Jalan otomatis saat Mac menyala

```bash
cp scripts/com.arsipsurat.api.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.arsipsurat.api.plist
```

Log: `~/Library/Logs/arsipsurat.log`. Restart: `launchctl kickstart -k gui/$(id -u)/com.arsipsurat.api`.

## Akses dari HP (Tailscale)

1. Pasang **Tailscale** di Mac (App Store / tailscale.com) dan di HP, login dengan akun yang sama.
2. Di HP buka `http://<nama-mac>:8100` (nama/IP Mac terlihat di app Tailscale, mis. `100.x.y.z`).
3. Supaya bisa "Add to Home Screen" sebagai app + HTTPS, jalankan di Mac:
   `tailscale serve --bg 8100` → akses lewat `https://<nama-mac>.<tailnet>.ts.net`.

Di Wi-Fi rumah yang sama, `http://<IP-lokal-Mac>:8100` juga bisa tanpa Tailscale.

## Cara kerja fitur

- **OCR**: Tesseract lokal (bahasa Indonesia + Inggris), tanpa AI. PDF digital dibaca langsung.
- **Poin yang dibahas**: kalimat diberi skor berdasarkan kata kunci (mohon, paling lambat, wajib,
  denda…), tanggal, dan nominal Rp. Selalu bisa diedit manual.
- **Usulan metadata**: nomor, perihal, tanggal, tenggat ("paling lambat …"), pengirim, kategori.
- **Relasi**: membalas / menindaklanjuti / merujuk / meralat. Nomor surat yang disebut di isi surat
  dicocokkan otomatis ke arsip (toleran salah baca OCR). Mencatat balasan menutup surat yang dibalas.
- **Benang**: posisi sekarang (giliranmu / menunggu pihak lain / selesai), kronologi dalam kalimat,
  hal yang masih harus diperhatikan, tenggat terdekat.
- **AI (opsional)**: tombol "Ringkas dengan AI" muncul hanya jika endpoint di `.env` hidup
  (lihat `.env.example`). Dipanggil hanya saat diklik, hasil disimpan.
