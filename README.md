# Arsip Surat

Dashboard pribadi untuk surat masuk & keluar: unggah scan/PDF, isi surat dibaca otomatis (OCR),
poin yang dibahas disorot, surat yang saling berkaitan dihubungkan jadi **benang** lengkap dengan
ringkasan perkembangannya.

## Menjalankan

```bash
./scripts/start.sh
```

Buka `http://localhost:8100`, lalu isi **Nama kamu** di menu Pengaturan (dipakai menebak arah surat).

## Penyimpanan

| Lokasi | Isi |
|---|---|
| `Google Drive/Arsip Surat/Arsip/TAHUN/BULAN/MASUK|KELUAR/` | PDF surat (ber-lapisan-teks, bisa dicari) |
| `Google Drive/Arsip Surat/Kotak Masuk/` | taruh file di sini → diimpor otomatis |
| `Google Drive/Arsip Surat/_backup/` | salinan harian database (14 terakhir) |
| `Google Drive/Arsip Surat/Sampah/` | file surat yang dihapus dari register |
| `data/surat.db` | database (lokal; SQLite tidak aman disinkron cloud) |
| `data/inbox/` | unggahan yang belum disimpan (dibersihkan setelah 2 hari) |

Lokasi diatur lewat `ARSIP_HOME` di `.env` (mis. folder Google Drive for desktop).
Tanpa `ARSIP_HOME`, app memakai iCloud Drive kalau ada.

### Dipakai dari akun Gmail lain

Dashboard tidak memakai login Google, jadi akun Gmail di perangkat lain tidak berpengaruh — cukup buka alamat dashboard
(lewat Tailscale). Untuk melihat/menambah file langsung di Drive dari akun lain: bagikan folder `Arsip Surat`
ke akun itu sebagai **Editor**, lalu di akun tersebut *Tambahkan pintasan ke Drive*.

## Input otomatis

- **Kotak Masuk Drive**: di HP buka app Google Drive → + → *Pindai*, simpan ke `Arsip Surat/Kotak Masuk`
  (atau pindahkan file yang sudah ada di Drive ke folder itu).
  Dalam ±30 detik surat dibaca, diisi, dan disimpan. Subfolder `Masuk/` dan `Keluar/` memaksa arahnya.
- **Unggah di web**: pilih/foto file → *Baca & simpan otomatis*. Banyak PDF = banyak surat;
  banyak foto = halaman satu surat (bisa diubah).
- Surat yang diisi otomatis ditandai **perlu dicek** (muncul di beranda). Tekan *Sudah benar* atau *Perbaiki*.

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
