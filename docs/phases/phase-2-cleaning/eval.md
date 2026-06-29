# Phase 2 Evaluation — Cleaning & Normalization

> **Phase:** 2 — Cleaning & Normalization  
> **Input:** `data/raw_reviews.json`  
> **Output artifact:** `data/clean_reviews.json`  
> **Implementation:** [implementation.md §4](../../implementation.md)  
> **Architecture:** [architecture.md §3.3](../../architecture.md)

---

## 1. Phase Objective

Transform raw ingested records into a clean, deduplicated, PII-stripped, schema-normalized dataset filtered to the configured date window.

---

## 2. Exit Criteria (Gate to Phase 3)

| # | Criterion | Target | Blocking |
|---|-----------|--------|----------|
| E2.1 | Clean record count | ≥ 200 (or ≥ 90% of raw if raw was marginal) | Yes |
| E2.2 | PII scan on `text` + `title` | 0 matches (email, phone, @handle) | Yes |
| E2.3 | Canonical schema | Every record has `id`, `source`, `date`, `rating`, `title`, `text` | Yes |
| E2.4 | Unique IDs | No duplicate `id` values | Yes |
| E2.5 | Date window compliance | 100% of records within 8–12 week window | Yes |
| E2.6 | Empty text removed | No records with blank `text` | Yes |
| E2.7 | Output file written | `data/clean_reviews.json` exists | Yes |
| E2.8 | Dedup reduction logged | `raw_count - clean_count` recorded in metrics | No |

---

## 3. Test Plan

### 3.1 Unit Tests

| Test ID | Module | Description | Assertion |
|---------|--------|-------------|-----------|
| T2.1 | `normalizer.strip_pii` | Strips email | `user@test.com` → `[REDACTED]` |
| T2.2 | `normalizer.strip_pii` | Strips @handle | `@spotifyfan` → `[REDACTED]` |
| T2.3 | `normalizer.strip_pii` | Strips phone | `555-123-4567` → `[REDACTED]` |
| T2.4 | `normalizer.normalize_record` | Stable ID hash | Same input → same `id` |
| T2.5 | `normalizer.deduplicate` | Removes dupes | 3 identical → 1 record |
| T2.6 | `normalizer` | Date filter | Records outside window excluded |
| T2.7 | `normalizer` | Rating nullable | Reddit records have `rating: null` |

**Run:**

```bash
pytest tests/test_normalizer.py -v
```

### 3.2 PII Regression Test

```bash
python -c "
import json, re
clean = json.load(open('data/clean_reviews.json'))
patterns = [
    re.compile(r'[\w.+-]+@[\w-]+\.[\w.-]+'),
    re.compile(r'@\w+'),
    re.compile(r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b'),
]
hits = []
for r in clean:
    blob = r['title'] + ' ' + r['text']
    for p in patterns:
        if p.search(blob):
            hits.append((r['id'], p.pattern))
assert not hits, f'PII found: {hits[:3]}'
print('PII SCAN: PASS')
"
```

### 3.3 Integration Test

```bash
python -c "
from main import phase_2_clean
import json
raw = json.load(open('data/raw_reviews.json'))
clean = phase_2_clean(raw)
assert len(clean) >= 200
ids = [r['id'] for r in clean]
assert len(ids) == len(set(ids))
print('PASS:', len(clean), 'clean records')
"
```

---

## 4. Evaluation Metrics

### Run: _[YYYY-MM-DD / run_id]_

| Metric | Value | Pass? |
|--------|-------|-------|
| Raw input count | | |
| Clean output count | | |
| Records removed (date filter) | | |
| Records removed (dedup) | | |
| Records removed (empty text) | | |
| PII redactions applied | | |
| PII leaks detected (post-scan) | | |
| Unique sources in clean set | | |
| Date range (min → max) | | |

---

## 5. Schema Validation

```python
import json

clean = json.load(open("data/clean_reviews.json"))
REQUIRED = {"id", "source", "date", "rating", "title", "text"}
VALID_SOURCES = {"app_store", "play_store", "reddit", "community_forum"}

for i, r in enumerate(clean):
    assert REQUIRED <= r.keys(), f"Record {i} missing fields"
    assert r["source"] in VALID_SOURCES
    assert isinstance(r["text"], str) and len(r["text"].strip()) > 0
    assert len(r["id"]) == 64  # sha256 hex

print("SCHEMA: PASS")
```

---

## 6. Failure Handling

| Failure | Action |
|---------|--------|
| PII detected after cleaning | Fix `strip_pii` patterns; re-run Phase 2 only |
| Clean count < 200 | Re-run Phase 1 with wider window; do not weaken PII rules |
| High dedup rate (> 30%) | Investigate source overlap; log in metrics |
| Date parse failures | Fix `normalize_date`; re-run from raw |

---

## 7. Sign-off

| Role | Name | Date | Result |
|------|------|------|--------|
| Implementer | | | Pass / Fail |
| Reviewer | | | Pass / Fail |

**Notes:**

---

## 8. Artifacts Produced

- [ ] `data/clean_reviews.json`
- [ ] `tests/test_normalizer.py` (green)
- [ ] PII scan PASS (§3.2)
- [ ] Metrics table (§4) filled
