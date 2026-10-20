"""Ekstraksi berbasis aturan (tanpa AI): poin penting, usulan metadata, rujukan surat lain."""
import re
from datetime import date
from difflib import SequenceMatcher

MONTHS = {
    "januari": 1, "jan": 1, "january": 1,
    "februari": 2, "feb": 2, "pebruari": 2, "february": 2,
    "maret": 3, "mar": 3, "march": 3,
    "april": 4, "apr": 4,
    "mei": 5, "may": 5,
    "juni": 6, "jun": 6, "june": 6,
    "juli": 7, "jul": 7, "july": 7,
    "agustus": 8, "agu": 8, "agt": 8, "ags": 8, "aug": 8, "august": 8,
    "september": 9, "sep": 9, "sept": 9,
    "oktober": 10, "okt": 10, "oct": 10, "october": 10,
    "november": 11, "nov": 11, "nopember": 11,
    "desember": 12, "des": 12, "dec": 12, "december": 12,
}
_MONTH_RE = "|".join(sorted(MONTHS, key=len, reverse=True))
DATE_TEXT = re.compile(rf"\b(\d{{1,2}})\s+({_MONTH_RE})\.?\s+(\d{{4}})\b", re.I)
DATE_NUM = re.compile(r"\b(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})\b")
MONEY = re.compile(r"\bRp\.?\s?[\d.,]+(?:\s?(?:juta|ribu|miliar|jt))?", re.I)

# kata yang menandai kalimat penting, beserta bobotnya
KEYWORDS = {
    3: ["paling lambat", "selambat-lambatnya", "batas waktu", "jatuh tempo", "tenggat",
        "wajib", "denda", "sanksi", "segera", "terakhir", "dibatalkan", "ditolak", "disetujui"],
    2: ["mohon", "diminta", "harap", "agar", "harus", "kewajiban", "tagihan", "pembayaran",
        "membayar", "sebesar", "melengkapi", "menyerahkan", "mengirimkan", "hadir", "undangan",
        "ditetapkan", "keputusan", "persetujuan", "pemberitahuan", "perubahan", "berlaku",
        "klaim", "pengembalian", "permohonan", "menginformasikan", "memberitahukan"],
    1: ["sehubungan", "berdasarkan", "terkait", "dilampirkan", "lampiran", "tanggal",
        "pukul", "tempat", "nomor rekening", "kontak", "hubungi"],
}
BOILERPLATE = re.compile(
    r"^(dengan hormat|hormat kami|hormat saya|demikian|atas perhatian|terima kasih|yth|"
    r"kepada\b|nomor\s*:|no\.?\s*:|lampiran\s*:|perihal\s*:|hal\s*:|sifat\s*:|tembusan|"
    r"salam|wassalam|assalamu|"
    r"[A-Z][A-Za-z .]{2,30},\s*\d{1,2}[\s/-])", re.I)   # "Jakarta, 8 Oktober 2026"
ACTION = re.compile(r"paling lambat|selambat|batas waktu|jatuh tempo|mohon|diminta|harap|wajib|agar|harus", re.I)

CATEGORIES = {
    "Pajak": ["pajak", "npwp", "djp", "spt", "kpp", "pph", "ppn"],
    "Bank": ["bank", "rekening", "kredit", "kartu kredit", "pinjaman", "angsuran", "tabungan"],
    "Asuransi": ["asuransi", "polis", "premi", "klaim", "tertanggung"],
    "BPJS": ["bpjs", "jkn", "ketenagakerjaan", "jaminan hari tua"],
    "Properti": ["sertifikat", "pbb", "tanah", "rumah", "sewa", "apartemen", "imb", "pbg"],
    "Kendaraan": ["stnk", "bpkb", "samsat", "kendaraan", "tilang", "nopol"],
    "Pekerjaan": ["kepegawaian", "pegawai", "dinas", "jabatan", "gaji", "mutasi", "cuti", "kantor", "asn"],
    "Legal": ["somasi", "pengadilan", "notaris", "perjanjian", "kuasa hukum", "gugatan", "akta"],
    "Pendidikan": ["sekolah", "universitas", "kampus", "beasiswa", "mahasiswa", "pendidikan"],
    "Kesehatan": ["rumah sakit", "klinik", "dokter", "medis", "pasien"],
}
CATEGORY_LIST = list(CATEGORIES) + ["Pribadi", "Lainnya"]


def _to_iso(d, m, y):
    try:
        return date(int(y), int(m), int(d)).isoformat()
    except ValueError:
        return None


def find_dates(text):
    """Semua tanggal (iso, posisi) yang ada di teks."""
    out = []
    for m in DATE_TEXT.finditer(text):
        iso = _to_iso(m.group(1), MONTHS[m.group(2).lower()], m.group(3))
        if iso:
            out.append((iso, m.start()))
    for m in DATE_NUM.finditer(text):
        iso = _to_iso(m.group(1), m.group(2), m.group(3))
        if iso:
            out.append((iso, m.start()))
    return sorted(out, key=lambda x: x[1])


def sentences(text):
    # OCR memotong kalimat per baris -> sambung baris dalam satu paragraf
    paras = []
    for p in re.split(r"\n\s*\n", text):
        p = re.sub(r"[ \t]+", " ", p.replace("\n", " ")).strip()
        if not p:
            continue
        # OCR kadang memberi jarak paragraf di tengah kalimat: sambung kalau
        # paragraf sebelumnya belum berakhir tanda baca dan ini diawali huruf kecil
        if paras and not re.search(r"[.!?:;]$", paras[-1]) and p[0].islower():
            paras[-1] += " " + p
        else:
            paras.append(p)
    out = []
    for p in paras:
        for s in re.split(r"(?<=[.!?;])\s+(?=[A-Z0-9(])", p):
            s = s.strip(" -•·")
            if s:
                out.append(s)
    return out


def _score(s):
    low = s.lower()
    score = 0
    for w, words in KEYWORDS.items():
        score += w * sum(1 for k in words if k in low)
    if DATE_TEXT.search(s) or DATE_NUM.search(s):
        score += 2
    if MONEY.search(s):
        score += 3
    if re.match(r"^(\d+|[a-z])[.)]\s", s):
        score += 1
    return score


def highlights(text, limit=5):
    cands = []
    for i, s in enumerate(sentences(text)):
        if len(s) < 25 or BOILERPLATE.match(s):
            continue
        if len(s) > 320:
            s = s[:317].rstrip() + "…"
        cands.append((i, s, _score(s)))
    best = sorted([c for c in cands if c[2] > 0], key=lambda c: -c[2])[:limit]
    if not best:
        best = cands[:3]
    return [s for _, s, _ in sorted(best, key=lambda c: c[0])]


def suggest(text):
    """Usulan metadata dari isi surat. Semua bisa salah — tetap dicek user."""
    head = "\n".join(text.splitlines()[:40])
    out = {"number": "", "subject": "", "letter_date": None, "due_date": None,
           "party": "", "category": "Lainnya", "references": []}

    m = re.search(r"(?:Nomor|No\.?)\s*[:.]\s*([A-Za-z0-9][\w./\-]{2,})", head)
    if m:
        out["number"] = m.group(1).strip(".")
    m = re.search(r"(?:Perihal|Hal)\s*[:.]\s*(.+)", head, re.I)
    if m:
        out["subject"] = m.group(1).strip()[:160]

    dates = find_dates(head)
    if dates:
        out["letter_date"] = dates[0][0]

    m = re.search(r"(paling lambat|selambat-lambatnya|batas waktu|jatuh tempo|sebelum tanggal|tenggat)(.{0,80})",
                  text, re.I | re.S)
    if m:
        d = find_dates(m.group(2))
        if d:
            out["due_date"] = d[0][0]

    for line in text.splitlines()[:8]:
        line = line.strip()
        if len(line) >= 5 and sum(ch.isalpha() for ch in line) >= 5 and not BOILERPLATE.match(line):
            out["party"] = line[:120]
            break

    low = text.lower()
    scores = {c: sum(low.count(k) for k in kws) for c, kws in CATEGORIES.items()}
    best = max(scores, key=scores.get)
    if scores[best] > 0:
        out["category"] = best

    # nomor surat lain yang disebut ("sehubungan dengan surat ... nomor X")
    refs = set()
    for m in re.finditer(r"surat\b.{0,60}?(?:nomor|no\.?)\s*[:.]?\s*([A-Za-z0-9][\w./\-]{3,})", text, re.I | re.S):
        refs.add(m.group(1).strip(".,"))
    refs.discard(out["number"])
    out["references"] = sorted(refs)
    return out


def _name_variants(owners):
    """'Budi Santoso Wijaya' -> {nama lengkap, 'budi wijaya'} (kata ≥4 huruf saja)."""
    out = set()
    for o in owners:
        words = [w for w in re.findall(r"[a-z]+", o.lower())]
        if len(" ".join(words)) >= 4:
            out.add(" ".join(words))
        if len(words) >= 2 and len(words[0]) >= 4 and len(words[-1]) >= 4:
            out.add(f"{words[0]} {words[-1]}")
    return out


def detect_direction(text, owners):
    """Masuk kalau namamu ada di blok tujuan (Yth./Kepada); keluar kalau di kop atau tanda tangan."""
    names = _name_variants(owners)
    if not names or not text.strip():
        return None
    low = re.sub(r"[^a-z]+", " ", text.lower())   # samakan spasi/tanda baca hasil OCR
    has = lambda zone: any(n in zone for n in names)
    m = re.search(r"\b(yth|kepada)\b", low)
    if m and has(low[m.start(): m.start() + 220]):
        return "masuk"
    if has(low[:200]) or has(low[int(len(low) * 0.65):]):
        return "keluar"
    if has(low):
        return "masuk"
    return None


def addressee(text):
    """Pihak tujuan dari blok 'Yth.' / 'Kepada'."""
    lines = [l.strip() for l in text.splitlines()]
    for i, line in enumerate(lines[:60]):
        m = re.match(r"^(?:kepada\s*)?(?:yth\.?|kepada)\s*:?\s*(.*)$", line, re.I)
        if not m:
            continue
        rest = m.group(1).strip(" .:")
        if len(rest) < 3:
            rest = next((l for l in lines[i + 1:i + 4] if len(l) >= 3), "")
        rest = re.sub(r"^(bapak|ibu|sdr\.?|saudara)\s+", "", rest, flags=re.I)
        return rest[:120]
    return ""


def norm_number(n):
    return re.sub(r"[^a-z0-9]", "", (n or "").lower())


def same_number(a, b):
    """Cocokkan nomor surat, toleran terhadap salah baca OCR (mis. IX terbaca TX)."""
    a, b = norm_number(a), norm_number(b)
    if not a or not b:
        return False
    if a == b:
        return True
    return min(len(a), len(b)) >= 6 and SequenceMatcher(None, a, b).ratio() >= 0.85


def is_action(point):
    return bool(ACTION.search(point))
