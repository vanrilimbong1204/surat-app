"""AI opsional (endpoint OpenAI-compatible, default CLIProxyAPI lokal).

Hanya dipanggil saat user menekan tombol "Ringkas dengan AI", dan hasilnya di-cache,
jadi token terpakai sekali per surat / per perubahan benang. Tanpa AI semua fitur
tetap jalan dengan versi berbasis aturan.
"""
import os

import httpx

BASE_URL = os.getenv("AI_BASE_URL", "http://localhost:8317/v1").rstrip("/")
API_KEY = os.getenv("AI_API_KEY", "")
MODEL = os.getenv("AI_MODEL", "gemini-2.5-flash")
MAX_INPUT_CHARS = 6000


def available() -> bool:
    try:
        r = httpx.get(f"{BASE_URL}/models", headers=_headers(), timeout=2)
        return r.status_code == 200
    except httpx.HTTPError:
        return False


def _headers():
    return {"Authorization": f"Bearer {API_KEY}"} if API_KEY else {}


def chat(system: str, user: str, max_tokens=700) -> str:
    r = httpx.post(
        f"{BASE_URL}/chat/completions",
        headers=_headers(),
        json={"model": MODEL, "temperature": 0.2, "max_tokens": max_tokens,
              "messages": [{"role": "system", "content": system},
                           {"role": "user", "content": user}]},
        timeout=90,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()


def letter_points(text: str) -> list[str]:
    out = chat(
        "Kamu asisten arsip surat pribadi. Tulis 3-6 poin penting dari surat: inti isi, "
        "permintaan/kewajiban, tanggal & tenggat, nominal uang, dan konsekuensi. "
        "Satu poin per baris diawali '- '. Bahasa Indonesia, ringkas, tanpa pembuka.",
        text[:MAX_INPUT_CHARS],
    )
    pts = [ln.strip().lstrip("-•* ").strip() for ln in out.splitlines()]
    return [p for p in pts if p][:6]


def thread_narrative(items: list[dict]) -> str:
    lines = []
    for it in items:
        pts = "; ".join(it["points"][:4]) or "-"
        lines.append(f"[{it['date'] or '?'}] {it['direction'].upper()} | {it['party'] or '?'} | "
                     f"{it['subject'] or '(tanpa perihal)'} | relasi: {it['relation'] or '-'} | "
                     f"status: {it['status']} | poin: {pts}")
    return chat(
        "Kamu asisten arsip surat pribadi. Diberi kronologi surat masuk/keluar yang saling berkaitan. "
        "Tulis ringkasan perkembangan dalam Bahasa Indonesia: 1 paragraf (3-5 kalimat) tentang apa "
        "perkaranya dan bagaimana perkembangannya sampai sekarang, lalu baris 'Posisi sekarang:' dan "
        "'Langkah berikutnya:' masing-masing satu kalimat. Jangan mengarang fakta di luar data.",
        "\n".join(lines)[:MAX_INPUT_CHARS],
    )
