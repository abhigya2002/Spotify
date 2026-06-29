# Phase 1 Evaluation — Ingestion

> **Phase:** 1 — Ingestion  
> **Output artifact:** `data/raw_reviews.json`  
> **Implementation:** [implementation.md §3](../../implementation.md)  
> **Architecture:** [architecture.md §3.2](../../architecture.md)

---

## 1. Phase Objective

Fetch public user feedback about Spotify from App Store, Play Store, Reddit, and community forums. Produce a unified raw JSON dataset for Phase 2 cleaning.

---

## 2. Exit Criteria (Gate to Phase 2)

All criteria must pass before starting Phase 2.

| # | Criterion | Target | Blocking |
|---|-----------|--------|----------|
| E1.1 | Total raw records collected | ≥ 200 | Yes |
| E1.2 | Distinct sources with data | ≥ 2 of 4 | Yes |
| E1.3 | App Store OR Play Store has data | ≥ 1 store source active | Yes |
| E1.4 | All records have required fields | `source`, `date`, `title`, `text` present | Yes |
| E1.5 | Date values parseable | 100% valid ISO-8601 or convertible | Yes |
| E1.6 | No authenticated scraping used | Public endpoints / official APIs only | Yes |
| E1.7 | Raw file written to disk | `data/raw_reviews.json` exists | Yes |
| E1.8 | Per-source minimum (warning) | Each attempted source ≥ 50 records | No — expand window if failed |

---

## 3. Test Plan

### 3.1 Unit Tests

| Test ID | Module | Description | Assertion |
|---------|--------|-------------|-----------|
| T1.1 | `app_store.js` | Script runs without error | Exit code 0 |
| T1.2 | `app_store.js` | Output is valid JSON array | `json.loads()` succeeds |
| T1.3 | `play_store.js` | Output schema matches contract | Each item has `source`, `date`, `rating`, `title`, `text` |
| T1.4 | `reddit.py` | Respects date filter | All records `date >= since` |
| T1.5 | `reddit.py` | Subreddit list correct | Only configured subreddits |
| T1.6 | `community_forum.py` | Handles HTTP errors gracefully | Returns partial list, logs warning |
| T1.7 | `main.py` (phase 1) | Merges all sources | `len(result) == sum of sources` |

**Run:**

```bash
pytest tests/test_ingestion.py -v
```

### 3.2 Integration Test

```bash
python -c "
from main import phase_1_ingest
import json
raw = phase_1_ingest()
assert len(raw) >= 200, f'Only {len(raw)} reviews'
sources = {r['source'] for r in raw}
assert len(sources) >= 2, f'Only sources: {sources}'
store = sources & {'app_store', 'play_store'}
assert store, 'No app store data'
print('PASS:', len(raw), 'reviews from', sources)
"
```

### 3.3 Manual Verification

| Check | How |
|-------|-----|
| Spot-check 5 random reviews | Confirm text is about Spotify / music discovery |
| App Store sample | Rating 1–5, recent date |
| Reddit sample | Title + selftext populated |
| Forum sample | Public page only — no login required |

---

## 4. Evaluation Metrics

Record in this section after each eval run.

### Run: 2026-06-26 (initial production run)

| Metric | Value | Pass? |
|--------|-------|-------|
| Total raw records | 2890 | Yes |
| App Store count | 50 | Yes |
| Play Store count | 2685 | Yes |
| Reddit count | 0* | Warn — add REDDIT_CLIENT_ID or retry Arctic Shift |
| Community forum count | 155 | Yes |
| Distinct sources | 3 (app_store, play_store, community_forum) | Yes |
| Earliest record date | (within 12-week window) | Yes |
| Latest record date | 2026-06-25 | Yes |
| Date window (weeks) | 12 | Yes |
| Fetch duration (seconds) | ~49 | Yes |
| Errors / warnings | Play Store UTF-8 fixed; Reddit blocked without OAuth | — |

\*Reddit public APIs blocked in CI environment; Arctic Shift fallback added post-run. Re-run `python main.py` with network access for Reddit data.

---

## 5. Data Quality Checks

```python
# scripts/validate_phase1.py
import json
from datetime import datetime, timedelta, timezone

raw = json.load(open("data/raw_reviews.json"))
REQUIRED = {"source", "date", "title", "text"}
since = datetime.now(timezone.utc) - timedelta(weeks=12)

errors = []
for i, r in enumerate(raw):
    missing = REQUIRED - r.keys()
    if missing:
        errors.append(f"Record {i}: missing {missing}")
    try:
        datetime.fromisoformat(str(r["date"]).replace("Z", "+00:00"))
    except ValueError:
        errors.append(f"Record {i}: bad date {r['date']}")

sources = {}
for r in raw:
    sources[r["source"]] = sources.get(r["source"], 0) + 1

print("Sources:", sources)
print("Total:", len(raw))
print("Errors:", len(errors))
assert not errors, errors[:5]
assert len(raw) >= 200
assert len(sources) >= 2
print("PHASE 1 VALIDATION: PASS")
```

---

## 6. Failure Handling

| Failure | Action | Decision log? |
|---------|--------|---------------|
| Source returns < 50 reviews | Expand `REVIEW_WINDOW_WEEKS` to 12 | Yes — note in [decision.md](../../decision.md) |
| Scraper breaks (npm API change) | Pin version or patch wrapper | Yes |
| Reddit rate limited | Reduce `limit`, add sleep, retry | No |
| Forum blocks requests | Skip forum; proceed if E1.1–E1.2 still pass | Yes if permanent |
| Total < 200 after window expansion | Escalate — do not proceed to Phase 2 | — |

---

## 7. Sign-off

| Role | Name | Date | Result |
|------|------|------|--------|
| Implementer | | | Pass / Fail |
| Reviewer | | | Pass / Fail |

**Notes:**

---

## 8. Artifacts Produced

- [x] `data/raw_reviews.json`
- [ ] `tests/test_ingestion.py` (green)
- [x] Metrics table (§4) filled for this run
