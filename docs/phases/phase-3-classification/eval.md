# Phase 3 Evaluation — LLM Classification

> **Phase:** 3 — LLM Classification  
> **Input:** `data/clean_reviews.json`  
> **Output artifact:** `data/classified_reviews.json`  
> **Implementation:** [implementation.md §5](../../implementation.md)  
> **Architecture:** [architecture.md §3.4](../../architecture.md)  
> **Decision:** [DEC-002, DEC-007](../../decision.md)

---

## 1. Phase Objective

Classify each clean review into a music-discovery theme with confidence score, discovery relevance flag, and sentiment using Groq `llama-3.3-70b-versatile`.

---

## 2. Exit Criteria (Gate to Phase 4)

| # | Criterion | Target | Blocking |
|---|-----------|--------|----------|
| E3.1 | All clean reviews classified | 100% have `theme`, `confidence`, `discovery_relevant`, `sentiment` | Yes |
| E3.2 | Unique discovery themes | ≤ 5 (excluding `Other`) | Yes |
| E3.3 | Confidence range valid | All `confidence` in [0.0, 1.0] | Yes |
| E3.4 | Sentiment values valid | Only `positive`, `neutral`, `negative` | Yes |
| E3.5 | Discovery-relevant subset | ≥ 50 reviews with `discovery_relevant: true` | Yes |
| E3.6 | Model compliance | Groq `llama-3.3-70b-versatile`, temp ≤ 0.1 | Yes |
| E3.7 | Output file written | `data/classified_reviews.json` exists | Yes |
| E3.8 | Batch error rate | < 5% batches failed after retry | Yes |
| E3.9 | JSON parse success | 100% batches return parseable JSON | Yes |

---

## 3. Test Plan

### 3.1 Unit Tests

| Test ID | Module | Description | Assertion |
|---------|--------|-------------|-----------|
| T3.1 | `prompts.py` | System prompt includes JSON schema | Keywords present |
| T3.2 | `classifier.py` | Batch splitting | 55 reviews → 3 batches (size 25) |
| T3.3 | `classifier.py` | Merge labels to records | Output count == input count |
| T3.4 | `classifier.py` | Retry on API error | Mock 429 → retries then succeeds |
| T3.5 | `classifier.py` | Theme cap enforcement | 8 themes → collapsed to ≤ 5 |
| T3.6 | `classifier.py` | `Other` for irrelevant | `discovery_relevant: false` → theme `Other` |

**Run:**

```bash
pytest tests/test_classifier.py -v
```

### 3.2 Golden Set Evaluation (Quality)

Maintain `tests/fixtures/golden_reviews.json` — 20 hand-labeled reviews.

| Metric | Target | Method |
|--------|--------|--------|
| Theme accuracy | ≥ 70% match human label | Compare `theme` field |
| Discovery relevance accuracy | ≥ 80% | Compare boolean |
| Sentiment accuracy | ≥ 75% | Compare sentiment |

```bash
pytest tests/test_classifier_golden.py -v
```

### 3.3 Integration Test

```bash
python -c "
import json
from main import phase_3_classify
clean = json.load(open('data/clean_reviews.json'))
classified = phase_3_classify(clean)
assert len(classified) == len(clean)
themes = {r['theme'] for r in classified if r.get('discovery_relevant')}
themes.discard('Other')
assert len(themes) <= 5, themes
relevant = sum(1 for r in classified if r.get('discovery_relevant'))
assert relevant >= 50
print('PASS:', len(classified), 'classified,', relevant, 'relevant,', len(themes), 'themes')
"
```

### 3.4 Manual Spot Check

Review 10 random classified records:

| Review ID | Theme reasonable? | Sentiment reasonable? | Confidence plausible? |
|-----------|-------------------|----------------------|----------------------|
| | Y/N | Y/N | Y/N |

Target: ≥ 8/10 marked reasonable on all columns.

---

## 4. Evaluation Metrics

### Run: _[YYYY-MM-DD / run_id]_

| Metric | Value | Pass? |
|--------|-------|-------|
| Input clean count | | |
| Output classified count | | |
| Discovery-relevant count | | |
| `Other` / irrelevant count | | |
| Unique themes (excl. Other) | | |
| Theme distribution | | |
| Sentiment breakdown (% neg/neu/pos) | | |
| Mean confidence (relevant only) | | |
| Batches sent | | |
| Batches failed (after retry) | | |
| Groq tokens used (if logged) | | |
| Classification duration (seconds) | | |
| Golden set theme accuracy | | |

**Theme distribution template:**

| Theme | Count | % | Avg Sentiment |
|-------|-------|---|---------------|
| | | | |

---

## 5. Classification Quality Rubric

Use for manual review when golden set is not yet built.

| Score | Theme assignment | Sentiment | Discovery flag |
|-------|------------------|-----------|----------------|
| 2 — Good | Clearly correct theme | Matches tone | Correct |
| 1 — Acceptable | Related theme | Close enough | Borderline OK |
| 0 — Poor | Wrong theme | Wrong | Wrong |

**Pass:** Mean score ≥ 1.5 across 10-sample manual review.

---

## 6. Failure Handling

| Failure | Action |
|---------|--------|
| Groq rate limit | Exponential backoff; reduce batch size to 20 |
| JSON parse failure | Strip markdown fences; retry batch once |
| Theme count > 5 | Run theme collapse post-processor |
| Relevant count < 50 | Review prompt; check if data is off-topic |
| Golden accuracy < 70% | Tune system prompt in `prompts.py`; log decision |

---

## 7. Sign-off

| Role | Name | Date | Result |
|------|------|------|--------|
| Implementer | | | Pass / Fail |
| Reviewer | | | Pass / Fail |

**Notes:**

---

## 8. Artifacts Produced

- [ ] `data/classified_reviews.json`
- [ ] `tests/test_classifier.py` (green)
- [ ] Golden set eval results (§3.2) — or manual rubric (§5)
- [ ] Metrics table (§4) filled
- [ ] Theme distribution documented
