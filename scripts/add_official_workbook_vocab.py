#!/usr/bin/env python3
"""Add vocabulary explicitly identified in the official N3 workbooks report.

The report distinguishes workbook publication year from an exam year. These
cards therefore carry official workbook evidence but do not claim appearance
in a particular JLPT administration.
"""
import hashlib
import json
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CARDS = ROOT / "data" / "cards.json"

ITEMS = [
    ("2012", "首都", "しゅと", "thủ đô", "lemma listed in workbook"),
    ("2012", "大量", "たいりょう", "số lượng lớn", "lemma listed in workbook"),
    ("2012", "インタビュー", "インタビュー", "phỏng vấn", "lemma listed in workbook"),
    ("2012", "主張", "しゅちょう", "khẳng định; chủ trương", "lemma listed in workbook"),
    ("2012", "からから", "からから", "khô khốc; khô rang", "lemma listed in workbook"),
    ("2012", "貯める", "ためる", "tiết kiệm; dành dụm", "workbook form is ためて; normalized to dictionary form"),
    ("2012", "訳", "わけ", "lý do", "workbook form is わけ; normalized to dictionary form"),
    ("2018", "訓練", "くんれん", "huấn luyện", "lemma listed in workbook"),
    ("2018", "豆", "まめ", "đậu; hạt đậu", "lemma listed in workbook"),
    ("2018", "波", "なみ", "sóng", "workbook uses なみ and includes kanji option 波"),
    ("2018", "組む", "くむ", "khoanh; ghép; tổ chức", "workbook form is くんで; normalized to dictionary form"),
    ("2018", "イメージ", "イメージ", "hình ảnh; ấn tượng", "lemma listed in workbook"),
    ("2018", "囲む", "かこむ", "bao quanh", "workbook form is 囲み; normalized to dictionary form"),
    ("2018", "姿勢", "しせい", "tư thế", "lemma listed in workbook"),
    ("2018", "輝く", "かがやく", "tỏa sáng", "workbook form is かがやいて; normalized to dictionary form"),
    ("2018", "余る", "あまる", "dư; thừa", "workbook form is あまりました; normalized to dictionary form"),
    ("2018", "沸騰", "ふっとう", "sôi", "lemma listed in workbook"),
    ("2018", "慰める", "なぐさめる", "an ủi", "lemma listed in workbook"),
]


def reading_key(value):
    value = unicodedata.normalize("NFKC", value)
    return "".join(chr(ord(char) - 96) if "ァ" <= char <= "ヶ" else char for char in value)


def card_id(year, term, reading):
    digest = hashlib.sha256((year + "\0" + term + "\0" + reading_key(reading)).encode()).hexdigest()[:18]
    return "official-wb-%s-%s" % (year, digest)


def main():
    cards = json.loads(CARDS.read_text(encoding="utf-8"))
    known = {(c["term"], reading_key(c["reading"]), c["meaning"]) for c in cards}
    added = []
    skipped = []
    for year, term, reading, meaning, form_note in ITEMS:
        key = (term, reading_key(reading), meaning)
        if key in known:
            skipped.append(term)
            continue
        url = "https://www.jlpt.jp/samples/sample%s/pdf/N3V.pdf" % year
        card = {
            "id": card_id(year, term, reading),
            "term": term,
            "reading": reading,
            "meaning": meaning.split(";")[0].strip(),
            "meaning_aliases": [part.strip() for part in meaning.split(";")[1:] if part.strip()],
            "kind": "vocab",
            "tier": "core",
            "topic": "JLPT Official Practice Workbook N3",
            "source": "JLPT Official Practice Workbook %s · N3 Vocabulary" % year,
            "verified": False,
            "curated": True,
            "source_type": "official_workbook",
            "source_year": int(year),
            "source_page": None,
            "source_url": url,
            "source_form": form_note,
            "verification_status": "official_workbook_report_checked; image_page_not_independently_verified",
            "exam_priority": "high",
            "exam_year_claim": None,
            "source_refs": [{
                "type": "official_workbook",
                "year": int(year),
                "url": url,
                "page": None,
                "form_note": form_note,
            }],
        }
        cards.append(card)
        known.add(key)
        added.append(card)
    CARDS.write_text(json.dumps(cards, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "before": len(cards) - len(added),
        "added": len(added),
        "skipped": skipped,
        "after": len(cards),
        "added_terms": [card["term"] for card in added],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
