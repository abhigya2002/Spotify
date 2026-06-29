"""Phase 1 validation script — see eval.md §5."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_PATH = PROJECT_ROOT / "data" / "raw_reviews.json"

REQUIRED = {"source", "date", "title", "text"}


def main() -> int:
    if not RAW_PATH.exists():
        print(f"ERROR: {RAW_PATH} not found — run python main.py first")
        return 1

    raw = json.loads(RAW_PATH.read_text(encoding="utf-8"))
    since = datetime.now(timezone.utc) - timedelta(weeks=12)

    errors: list[str] = []
    for i, r in enumerate(raw):
        missing = REQUIRED - r.keys()
        if missing:
            errors.append(f"Record {i}: missing {missing}")
        try:
            datetime.fromisoformat(str(r["date"]).replace("Z", "+00:00"))
        except ValueError:
            errors.append(f"Record {i}: bad date {r['date']}")

    sources: dict[str, int] = {}
    for r in raw:
        sources[r["source"]] = sources.get(r["source"], 0) + 1

    print("Sources:", sources)
    print("Total:", len(raw))
    print("Errors:", len(errors))

    if errors:
        print("Sample errors:", errors[:5])
        return 1

    if len(raw) < 200:
        print(f"FAIL: need >= 200 records, got {len(raw)}")
        return 1

    if len(sources) < 2:
        print(f"FAIL: need >= 2 sources, got {sources}")
        return 1

    store = sources.keys() & {"app_store", "play_store"}
    if not store:
        print("FAIL: no app_store or play_store data")
        return 1

    print("PHASE 1 VALIDATION: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
