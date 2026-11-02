#!/usr/bin/env python3
"""Attach official-workbook metadata to the 64-item comparison set."""
import csv
import io
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = Path("/Users/thutrang/Downloads/JLPT_N3_Kiem_Tra_64_Tu_Official.zip")
CARDS = ROOT / "data" / "cards.json"


def main():
    cards = json.loads(CARDS.read_text(encoding="utf-8"))
    by_key = {(c["term"], c["reading"]): c for c in cards}
    with zipfile.ZipFile(str(ARCHIVE)) as archive:
        rows = list(csv.DictReader(io.TextIOWrapper(
            archive.open("JLPT_N3_kiem_tra_de_thi/kiem_tra_64_tu_de_chinh_thuc_vs_v9.csv"),
            encoding="utf-8-sig",
        )))
    annotated = 0
    for row in rows:
        card = by_key.get((row["term"], row["reading"]))
        if not card:
            continue
        year = int(row["source"].split()[4])
        ref = {
            "type": "official_workbook",
            "year": year,
            "url": row["source_pdf_url"],
            "page": None,
            "form_note": row["source_form_note"],
        }
        refs = card.setdefault("source_refs", [])
        if not any(x.get("type") == ref["type"] and x.get("year") == year for x in refs):
            refs.append(ref)
        card.setdefault("source_type", "official_workbook")
        card.setdefault("source_year", year)
        card.setdefault("source_page", None)
        card.setdefault("source_url", row["source_pdf_url"])
        card.setdefault("source_form", row["source_form_note"])
        card.setdefault("verification_status", "official_workbook_report_checked; image_page_not_independently_verified")
        card.setdefault("exam_priority", "high")
        card.setdefault("exam_year_claim", None)
        annotated += 1
    CARDS.write_text(json.dumps(cards, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"comparison_rows": len(rows), "annotated_cards": annotated}, ensure_ascii=False))


if __name__ == "__main__":
    main()
