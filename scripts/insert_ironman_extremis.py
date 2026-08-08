#!/usr/bin/env python3
"""Insert 100% Marvel #44 — Iron Man: Extremis before Iron Man e i Vendicatori #85.

The public Iron Man archive is stored as gzip/base64 parts. This maintenance
script keeps the migration reproducible, updates the lightweight manifests and
adds a display-number override so the inserted physical edition can show its
real Italian number without colliding with the main series numbering.
"""

from __future__ import annotations

import base64
import gzip
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CHUNK_SIZE = 7_500
SPECIAL_ID = "100M:44"
SPECIAL_INTERNAL_NUMBER = 44085
TARGET_SERIES = "IM_VEN"
TARGET_NUMBER = 85


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: dict) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )


def unpack_ironman() -> dict:
    spec = read_json(DATA / "encoded" / "ironman.json")
    encoded = "".join(
        (ROOT / source).read_text(encoding="ascii").strip()
        for source in spec["sources"]
    )
    return json.loads(gzip.decompress(base64.b64decode(encoded)).decode("utf-8"))


def pack_ironman(character: dict) -> None:
    raw = json.dumps(character, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    encoded = base64.b64encode(gzip.compress(raw, compresslevel=9, mtime=0)).decode("ascii")
    parts = [encoded[index : index + CHUNK_SIZE] for index in range(0, len(encoded), CHUNK_SIZE)]

    b64_dir = DATA / "b64"
    for old_part in b64_dir.glob("ironman-*.b64"):
        old_part.unlink()

    sources: list[str] = []
    for index, part in enumerate(parts, start=1):
        relative = f"data/b64/ironman-{index:02d}.b64"
        (ROOT / relative).write_text(part, encoding="ascii")
        sources.append(relative)

    write_json(
        DATA / "encoded" / "ironman.json",
        {"encoding": "gzip-base64-parts", "sources": sources},
    )


def patch_display_number_support() -> None:
    app_path = ROOT / "js" / "app.js"
    source = app_path.read_text(encoding="utf-8")
    old = '<div class="num">#<b>${String(i.n).padStart(2,"0")}</b></div>'
    new = '<div class="num">#<b>${esc(i.displayNumber??String(i.n).padStart(2,"0"))}</b></div>'
    if new in source:
        return
    if old not in source:
        raise RuntimeError("Impossibile trovare il renderer del numero albo in js/app.js")
    app_path.write_text(source.replace(old, new, 1), encoding="utf-8")


def update_totals(total_required: int) -> None:
    meta_path = DATA / "characters" / "ironman.json"
    meta = read_json(meta_path)
    meta["totalRequired"] = total_required
    meta["issueSources"] = ["data/encoded/ironman.json"]
    meta["description"] = (
        "Percorso italiano di Tony Stark con gli inserti cronologici necessari alla lettura narrativa."
    )
    if meta.get("series"):
        meta["series"][0]["range"] = "#1–84 → Extremis → #85–89"
    write_json(meta_path, meta)

    manifest_path = DATA / "characters.json"
    manifest = read_json(manifest_path)
    ironman = next(item for item in manifest["characters"] if item["id"] == "ironman")
    ironman["totalRequired"] = total_required
    write_json(manifest_path, manifest)


def main() -> None:
    character = unpack_ironman()
    issues = character["issues"]
    existing = next((issue for issue in issues if issue.get("id") == SPECIAL_ID), None)

    target = next(
        issue
        for issue in issues
        if issue.get("seriesId") == TARGET_SERIES and issue.get("n") == TARGET_NUMBER
    )

    if existing is None:
        target_seq = target.get("seq")
        if not isinstance(target_seq, int):
            raise RuntimeError("Iron Man e i Vendicatori #85 non ha una sequenza intera valida")

        for issue in issues:
            seq = issue.get("seq")
            if (
                issue.get("required") is not False
                and not issue.get("future")
                and isinstance(seq, int)
                and seq >= target_seq
            ):
                issue["seq"] = seq + 1

        special = {
            "id": SPECIAL_ID,
            "seq": target_seq,
            "seriesId": target["seriesId"],
            "series": target["series"],
            "publisher": "Marvel Italia",
            "n": SPECIAL_INTERNAL_NUMBER,
            "displayNumber": "44",
            "name": "100% Marvel #44 — Iron Man: Extremis",
            "title": "Extremis — The Invincible Iron Man #1-6",
            "date": "Novembre 2006",
            "era": target["era"],
            "eraSub": target.get("eraSub", ""),
            "cover": "https://www.comicsbox.it/cover/100M_044.jpg",
            "url": "https://www.comicsbox.it/albo/100M_044",
            "required": True,
            "skip": False,
            "instruction": (
                "INSERTO CRONOLOGICO OBBLIGATORIO: leggi l'intero volume, che raccoglie "
                "The Invincible Iron Man #1-6, prima di Iron Man e i Vendicatori #85 — House of M."
            ),
            "sourceIssues": [
                "The Invincible Iron Man Vol 1 #1",
                "The Invincible Iron Man Vol 1 #2",
                "The Invincible Iron Man Vol 1 #3",
                "The Invincible Iron Man Vol 1 #4",
                "The Invincible Iron Man Vol 1 #5",
                "The Invincible Iron Man Vol 1 #6",
            ],
        }
        issues.insert(issues.index(target), special)
        print(f"Inserito Extremis alla sequenza {target_seq}, prima di {target['name']}.")
    else:
        print("Extremis è già presente: nessuna seconda inserzione eseguita.")

    issues.sort(
        key=lambda issue: (
            issue.get("seq") if isinstance(issue.get("seq"), int) else 10**9,
            issue.get("n") if isinstance(issue.get("n"), int) else 10**9,
        )
    )

    if character.get("series"):
        character["series"][0]["range"] = "#1–84 → Extremis → #85–89"
    character["description"] = (
        "Percorso italiano di Tony Stark con gli inserti cronologici necessari alla lettura narrativa."
    )
    total_required = sum(
        1 for issue in issues if issue.get("required") is not False and not issue.get("future")
    )
    character["totalRequired"] = total_required

    pack_ironman(character)
    update_totals(total_required)
    patch_display_number_support()

    target_after = next(
        issue
        for issue in character["issues"]
        if issue.get("seriesId") == TARGET_SERIES and issue.get("n") == TARGET_NUMBER
    )
    special_after = next(issue for issue in character["issues"] if issue.get("id") == SPECIAL_ID)
    if special_after["seq"] + 1 != target_after["seq"]:
        raise RuntimeError("La sequenza finale non colloca Extremis immediatamente prima del #85")

    print(
        f"Iron Man: {len(character['issues'])} voci, {total_required} richieste; "
        f"Extremis #{special_after['seq']} → House of M #{target_after['seq']}."
    )


if __name__ == "__main__":
    main()
