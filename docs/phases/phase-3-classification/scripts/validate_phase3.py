"""Validate Phase 3 exit criteria against classified_reviews.json."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CLASSIFIED_PATH = PROJECT_ROOT / "data" / "classified_reviews.json"

REQUIRED_LABEL_FIELDS = {"theme", "confidence", "sentiment", "discovery_relevant", "key_phrase"}
VALID_THEMES = {
    "Recommendation Quality",
    "Discovery Friction",
    "Algorithm Transparency",
    "Playlist & Curation",
    "Listening Context",
}
VALID_SENTIMENTS = {"positive", "neutral", "negative"}


def main() -> int:
    if not CLASSIFIED_PATH.exists():
        print(f"ERROR: {CLASSIFIED_PATH} not found — run python main.py --run first")
        return 1

    classified = json.loads(CLASSIFIED_PATH.read_text(encoding="utf-8"))
    errors: list[str] = []

    for i, record in enumerate(classified):
        missing = REQUIRED_LABEL_FIELDS - record.keys()
        if missing:
            errors.append(f"Record {i}: missing {missing}")
        theme = record.get("theme")
        if theme not in VALID_THEMES:
            errors.append(f"Record {i}: invalid theme '{theme}'")
        conf = record.get("confidence")
        if not isinstance(conf, (int, float)) or not (0.0 <= float(conf) <= 1.0):
            errors.append(f"Record {i}: confidence out of range")
        if record.get("sentiment") not in VALID_SENTIMENTS:
            errors.append(f"Record {i}: invalid sentiment")

    themes = {r["theme"] for r in classified if r.get("discovery_relevant")}
    relevant = sum(1 for r in classified if r.get("discovery_relevant"))

    print(f"Classified: {len(classified)}")
    print(f"Discovery-relevant: {relevant}")
    print(f"Unique themes (relevant): {len(themes)}")
    print(f"Errors: {len(errors)}")

    if errors:
        for err in errors[:10]:
            print(f"  - {err}")
        return 1

    if relevant < 50:
        print("WARNING: fewer than 50 discovery-relevant records")
    if len(themes) > 5:
        print("FAIL: more than 5 themes")
        return 1

    print("PHASE 3 VALIDATION: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
