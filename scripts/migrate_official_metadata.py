#!/usr/bin/env python3
"""Merge official-workbook metadata into existing card rows without touching progress."""
import json
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import server

CARDS = Path(__file__).resolve().parents[1] / "data" / "cards.json"
METADATA_KEYS = (
    "source_type", "source_year", "source_page", "source_url", "source_form",
    "verification_status", "exam_priority", "exam_year_claim", "source_refs",
)


def main():
    cards = json.loads(CARDS.read_text(encoding="utf-8"))
    official = {card["id"]: card for card in cards if card.get("source_type") == "official_workbook"}
    updated = 0
    with server.connect() as conn:
        before_progress = conn.execute("SELECT COUNT(*) FROM progress").fetchone()[0]
        before_events = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        for card_id, source in official.items():
            row = conn.execute("SELECT body FROM cards WHERE id=?", (card_id,)).fetchone()
            if not row:
                continue
            current = json.loads(row["body"])
            changed = False
            for key in METADATA_KEYS:
                if key in source and current.get(key) != source[key]:
                    current[key] = source[key]
                    changed = True
            if changed:
                conn.execute("UPDATE cards SET body=? WHERE id=?",
                             (json.dumps(current, ensure_ascii=False), card_id))
                updated += 1
        after_progress = conn.execute("SELECT COUNT(*) FROM progress").fetchone()[0]
        after_events = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    print(json.dumps({
        "official_cards_considered": len(official),
        "existing_cards_metadata_updated": updated,
        "progress_unchanged": before_progress == after_progress,
        "events_unchanged": before_events == after_events,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
