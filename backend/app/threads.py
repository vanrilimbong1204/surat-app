"""Benang surat: kumpulan surat yang terhubung lewat relasi, plus ringkasan perkembangannya."""
import hashlib
import json
from datetime import date

from . import extract
from .db import row_to_letter

RELATION_LABEL = {
    "membalas": "membalas",
    "menindaklanjuti": "menindaklanjuti",
    "merujuk": "merujuk",
    "meralat": "meralat/mencabut",
}


def components(conn):
    """Union-find atas relasi -> {letter_id: root_id} (root = id terkecil)."""
    parent = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for r in conn.execute("SELECT from_id, to_id FROM relations"):
        a, b = find(r["from_id"]), find(r["to_id"])
        if a != b:
            parent[max(a, b)] = min(a, b)
    return {x: find(x) for x in list(parent)}


def members(conn, letter_id):
    comp = components(conn)
    if letter_id not in comp:
        return []
    root = comp[letter_id]
    return sorted(i for i, r in comp.items() if r == root)


def eff_date(l):
    return l.get("io_date") or l.get("letter_date") or (l.get("created_at") or "")[:10]


BULAN = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]


def fmt(iso):
    try:
        d = date.fromisoformat(iso)
        return f"{d.day} {BULAN[d.month - 1]} {d.year}"
    except (TypeError, ValueError):
        return iso or "?"


def _days_since(iso):
    try:
        return (date.today() - date.fromisoformat(iso)).days
    except (TypeError, ValueError):
        return None


def build(conn, ids):
    """Ringkasan berbasis aturan untuk benang berisi `ids`."""
    q = ",".join("?" * len(ids))
    letters = [row_to_letter(r) for r in conn.execute(f"SELECT * FROM letters WHERE id IN ({q})", ids)]
    rels = [dict(r) for r in conn.execute(
        f"SELECT * FROM relations WHERE from_id IN ({q}) OR to_id IN ({q})", ids + ids)]
    letters.sort(key=lambda l: (eff_date(l), l["id"]))
    by_id = {l["id"]: l for l in letters}

    timeline = []
    for l in letters:
        outgoing = [r for r in rels if r["from_id"] == l["id"] and r["to_id"] in by_id]
        rel_txt = ", ".join(f"{RELATION_LABEL.get(r['type'], r['type'])} #{r['to_id']}" for r in outgoing)
        timeline.append({
            "id": l["id"], "date": eff_date(l), "direction": l["direction"], "party": l["party"],
            "subject": l["subject"], "status": l["status"], "due_date": l["due_date"],
            "points": l["highlights"], "relation": rel_txt,
        })

    first, last = letters[0], letters[-1]
    open_letters = [l for l in letters if l["status"] in ("perlu_tindakan", "menunggu_balasan")]
    if not open_letters:
        state, position = "selesai", "Selesai — semua surat di benang ini sudah ditutup."
    elif last["direction"] == "masuk" and last["status"] == "perlu_tindakan":
        n = _days_since(eff_date(last))
        state = "giliranmu"
        position = (f"Giliranmu: surat dari {last['party'] or 'pihak terkait'} ({fmt(eff_date(last))}) "
                    f"belum ditanggapi" + (f", sudah {n} hari" if n else "") + ".")
    elif last["direction"] == "keluar":
        n = _days_since(eff_date(last))
        state = "menunggu"
        position = (f"Menunggu tanggapan {last['party'] or 'pihak terkait'} atas suratmu "
                    f"tanggal {fmt(eff_date(last))}" + (f" ({n} hari)" if n is not None else "") + ".")
    else:
        state = "berjalan"
        position = f"Masih berjalan — {len(open_letters)} surat belum ditutup."

    # kronologi singkat dalam kalimat (tanpa AI)
    story = []
    for i, (l, t) in enumerate(zip(letters, timeline)):
        who = "Kamu mengirim surat" if l["direction"] == "keluar" else f"{l['party'] or 'Pihak lain'} mengirim surat"
        what = l["subject"] or "(tanpa perihal)"
        if i == 0:
            story.append(f"{fmt(t['date'])}: {who} perihal “{what}”.")
        else:
            gap = None
            try:
                gap = (date.fromisoformat(t["date"]) - date.fromisoformat(timeline[i - 1]["date"])).days
            except ValueError:
                pass
            outgoing = [r for r in rels if r["from_id"] == l["id"] and r["to_id"] in by_id]
            rel = ", ".join(f"{RELATION_LABEL.get(r['type'], r['type'])} surat {fmt(eff_date(by_id[r['to_id']]))}"
                            for r in outgoing)
            rel = f" yang {rel}" if rel else ""
            after = f" ({gap} hari kemudian)" if gap is not None else ""
            story.append(f"{fmt(t['date'])}{after}: {who}{rel} — “{what}”.")

    dues = sorted(l["due_date"] for l in open_letters if l["due_date"])
    open_points = [p for p in last["highlights"] if extract.is_action(p)][:3]

    start, end = eff_date(first), eff_date(last)
    try:
        span = (date.fromisoformat(end) - date.fromisoformat(start)).days
    except ValueError:
        span = None

    return {
        "root_id": ids[0],
        "title": first["subject"] or f"Surat #{first['id']}",
        "parties": sorted({l["party"] for l in letters if l["party"]}),
        "stats": {
            "count": len(letters),
            "masuk": sum(l["direction"] == "masuk" for l in letters),
            "keluar": sum(l["direction"] == "keluar" for l in letters),
            "start": start, "last": end, "span_days": span,
        },
        "state": state,
        "position": position,
        "next_due": dues[0] if dues else None,
        "open_points": open_points,
        "story": story,
        "timeline": timeline,
        "signature": signature(letters, rels),
    }


def signature(letters, rels):
    raw = json.dumps([[l["id"], l["updated_at"]] for l in letters] +
                     sorted([r["from_id"], r["to_id"], r["type"]] for r in rels))
    return hashlib.sha1(raw.encode()).hexdigest()


def with_ai(conn, summary):
    row = conn.execute("SELECT * FROM thread_summaries WHERE root_id = ?", (summary["root_id"],)).fetchone()
    if row:
        summary["ai"] = {"text": row["summary"], "created_at": row["created_at"],
                         "stale": row["signature"] != summary["signature"]}
    else:
        summary["ai"] = None
    return summary


def all_threads(conn):
    comp = components(conn)
    groups = {}
    for i, r in comp.items():
        groups.setdefault(r, []).append(i)
    return [with_ai(conn, build(conn, sorted(ids))) for ids in groups.values() if len(ids) > 1]
