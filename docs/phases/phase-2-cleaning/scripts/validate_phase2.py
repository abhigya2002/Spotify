"""Validate Phase 2 exit criteria against clean_reviews.json."""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
CLEAN_PATH = DATA_DIR / "clean_reviews.json"

REQUIRED_FIELDS = {
    "id",
    "source",
    "date",
    "rating",
    "title",
    "text",
    "word_count",
    "language",
    "discovery_relevant",
    "original_text",
}
VALID_SOURCES = {"app_store", "play_store", "reddit", "community_forum"}
PII_PATTERNS = [
    re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),
    re.compile(r"@\w+"),
    re.compile(r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE),
]


def main() -> int:
    if not CLEAN_PATH.exists():
        print(f"ERROR: {CLEAN_PATH} not found — run python main.py first")
        return 1

    clean = json.loads(CLEAN_PATH.read_text(encoding="utf-8"))
    errors: list[str] = []
    since = datetime.now(timezone.utc) - timedelta(weeks=12)

    for i, record in enumerate(clean):
        missing = REQUIRED_FIELDS - record.keys()
        if missing:
            errors.append(f"Record {i}: missing fields {missing}")
        if record.get("source") not in VALID_SOURCES:
            errors.append(f"Record {i}: invalid source {record.get('source')}")
        if not str(record.get("text", "")).strip():
            errors.append(f"Record {i}: empty text")
        if record.get("language") != "en":
            errors.append(f"Record {i}: language is not en")
        if record.get("discovery_relevant") is not True:
            errors.append(f"Record {i}: discovery_relevant is not true")
        if record.get("word_count", 0) < 8:
            errors.append(f"Record {i}: word_count below minimum")

        try:
            parsed = datetime.fromisoformat(str(record["date"]).replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            if parsed.astimezone(timezone.utc) < since:
                errors.append(f"Record {i}: outside 12-week window")
        except ValueError:
            errors.append(f"Record {i}: unparseable date")

        blob = f"{record.get('title', '')} {record.get('text', '')}"
        for pattern in PII_PATTERNS:
            if pattern.search(blob):
                errors.append(f"Record {i}: PII leak ({pattern.pattern})")

    ids = [r["id"] for r in clean]
    if len(ids) != len(set(ids)):
        errors.append("Duplicate id values detected")

    print(f"Clean records: {len(clean)}")
    print(f"Schema / PII errors: {len(errors)}")

    if errors:
        for err in errors[:10]:
            print(f"  - {err}")
        return 1

    if len(clean) < 200:
        print("WARNING: fewer than 200 clean records (eval E2.1)")

    print("PHASE 2 VALIDATION: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
