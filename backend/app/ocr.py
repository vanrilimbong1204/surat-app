"""Ubah unggahan (foto/scan/PDF) jadi satu PDF yang bisa dicari + teksnya.

- PDF digital  -> teks diambil langsung (pdftotext), file tidak diubah.
- PDF scan     -> tiap halaman dirender lalu di-OCR; hasilnya PDF ber-lapisan-teks.
- Foto/gambar  -> dirapikan (orientasi, ukuran) lalu di-OCR jadi PDF ber-lapisan-teks.
OCR pakai Tesseract lokal (bahasa Indonesia + Inggris), tanpa AI/token.
"""
import hashlib
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageOps
from pypdf import PdfReader, PdfWriter

from .db import DATA

TESSDATA = DATA / "tessdata"
LANGS = "ind+eng"
MAX_SIDE = 2480          # ~A4 300 dpi, cukup tajam untuk OCR, ukuran file wajar
MIN_CHARS_PER_PAGE = 40  # di bawah ini dianggap PDF hasil scan (tanpa teks)
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".heic", ".webp", ".tif", ".tiff", ".bmp"}


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _tesseract_page(image: Path, outbase: Path) -> str:
    """OCR satu gambar -> outbase.pdf (ber-lapisan-teks) + teksnya."""
    subprocess.run(
        ["tesseract", str(image), str(outbase), "--tessdata-dir", str(TESSDATA),
         "-l", LANGS, "--psm", "3", "pdf", "txt"],
        check=True, capture_output=True,
    )
    return outbase.with_suffix(".txt").read_text(errors="ignore")


def _prepare_image(src: Path, dst: Path):
    img = Image.open(src)
    img = ImageOps.exif_transpose(img).convert("RGB")
    img.thumbnail((MAX_SIDE, MAX_SIDE))
    img.save(dst, "JPEG", quality=78)


def _ocr_images(images: list[Path], out_pdf: Path, work: Path) -> list[str]:
    writer, texts = PdfWriter(), []
    for i, img in enumerate(images):
        prepared = work / f"p{i:03d}.jpg"
        _prepare_image(img, prepared)
        base = work / f"p{i:03d}"
        texts.append(_tesseract_page(prepared, base))
        writer.append(str(base.with_suffix(".pdf")))
    with open(out_pdf, "wb") as f:
        writer.write(f)
    return texts


def _pdf_text(pdf: Path) -> list[str]:
    n = len(PdfReader(str(pdf)).pages)
    pages = []
    for p in range(1, n + 1):
        r = subprocess.run(["pdftotext", "-layout", "-f", str(p), "-l", str(p), str(pdf), "-"],
                           capture_output=True, text=True)
        pages.append(r.stdout)
    return pages


def process(inputs: list[Path], out_pdf: Path) -> dict:
    """Gabungkan semua input (urut) jadi out_pdf. Return teks, jumlah halaman, metode."""
    with tempfile.TemporaryDirectory(dir=DATA) as tmp:
        work = Path(tmp)
        images = [p for p in inputs if p.suffix.lower() in IMAGE_EXT]
        pdfs = [p for p in inputs if p.suffix.lower() == ".pdf"]
        if images and pdfs:
            raise ValueError("Campur foto dan PDF dalam satu surat belum didukung — unggah salah satu jenis.")
        if not images and not pdfs:
            raise ValueError("Format file tidak dikenali (pakai PDF atau foto JPG/PNG/HEIC).")

        if images:
            texts = _ocr_images(images, out_pdf, work)
            return {"text": "\n\n".join(texts), "pages": len(texts), "method": "ocr-foto"}

        merged = work / "merged.pdf"
        if len(pdfs) == 1:
            shutil.copy(pdfs[0], merged)
        else:
            w = PdfWriter()
            for p in pdfs:
                w.append(str(p))
            with open(merged, "wb") as f:
                w.write(f)

        texts = _pdf_text(merged)
        if sum(len(t.strip()) for t in texts) >= MIN_CHARS_PER_PAGE * len(texts):
            shutil.copy(merged, out_pdf)
            return {"text": "\n\n".join(texts), "pages": len(texts), "method": "pdf-digital"}

        # PDF hasil scan: render tiap halaman lalu OCR
        subprocess.run(["pdftoppm", "-r", "300", "-jpeg", "-jpegopt", "quality=85",
                        str(merged), str(work / "r")], check=True, capture_output=True)
        rendered = sorted(work.glob("r-*.jpg"))
        texts = _ocr_images(rendered, out_pdf, work)
        return {"text": "\n\n".join(texts), "pages": len(texts), "method": "ocr-scan"}
