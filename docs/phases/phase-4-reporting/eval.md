# Phase 4 Evaluation — Pulse Report Generation

> **Phase:** 4 — Pulse Report Generation  
> **Input:** `data/classified_reviews.json`  
> **Output artifact:** `data/pulse_report.md`  
> **Implementation:** [implementation.md §6](../../implementation.md)  
> **Architecture:** [architecture.md §3.5](../../architecture.md)  
> **Decision:** [DEC-004, DEC-007](../../decision.md)

---

## 1. Phase Objective

Aggregate classified reviews into top themes, select representative quotes, generate three PM action ideas, and produce a ≤250-word weekly pulse note as Markdown.

---

## 2. Exit Criteria (Gate to Phase 5)

| # | Criterion | Target | Blocking |
|---|-----------|--------|----------|
| E4.1 | Word count | ≤ 250 words | Yes |
| E4.2 | Top themes section | Exactly 3 themes with summary + volume + sentiment | Yes |
| E4.3 | User quotes | Exactly 3 verbatim quotes, PII-free | Yes |
| E4.4 | Action ideas | Exactly 3 prioritized PM recommendations | Yes |
| E4.5 | Header present | Product name + week range | Yes |
| E4.6 | Footer present | Total reviews analyzed + generation date | Yes |
| E4.7 | Quote attribution | Each quote labeled with source (+ rating if available) | Yes |
| E4.8 | PII scan on pulse | 0 PII patterns in final markdown | Yes |
| E4.9 | Output file written | `data/pulse_report.md` exists | Yes |
| E4.10 | PM readability | Human reviewer rates ≥ 4/5 scannability | No — recommended |

---

## 3. Test Plan

### 3.1 Unit Tests

| Test ID | Module | Description | Assertion |
|---------|--------|-------------|-----------|
| T4.1 | `aggregator.py` | Top 3 themes by volume | Correct ordering |
| T4.2 | `aggregator.py` | Sentiment breakdown | Sums to theme count |
| T4.3 | `aggregator.py` | Quote selection diversity | 3 quotes from ≥ 2 sources or themes |
| T4.4 | `aggregator.py` | Min confidence filter | Quotes have confidence ≥ 0.6 |
| T4.5 | `pulse_generator.py` | Word count enforcement | Reject/regenerate if > 250 |
| T4.6 | `pulse_generator.py` | Required sections present | Parse headers successfully |

**Run:**

```bash
pytest tests/test_reporting.py -v
```

### 3.2 Structural Validation

```bash
python -c "
from pathlib import Path
import re

pulse = Path('data/pulse_report.md').read_text()
words = len(pulse.split())
assert words <= 250, f'{words} words'

required_sections = ['Top Themes', 'User Quotes', 'Action Ideas']
for s in required_sections:
    assert s.lower() in pulse.lower(), f'Missing: {s}'

# Rough quote count (lines starting with > or bullet quotes)
quotes = re.findall(r'^> |\".+\"', pulse, re.M)
assert len(quotes) >= 3, 'Expected 3 quotes'

pii = [r'@\\w+', r'[\\w.+-]+@[\\w-]+\\.[\\w.-]+']
for p in pii:
    assert not re.search(p, pulse), f'PII: {p}'

print('STRUCTURE: PASS', words, 'words')
"
```

### 3.3 Integration Test

```bash
python -c "
import json
from main import phase_4_report
classified = json.load(open('data/classified_reviews.json'))
path = phase_4_report(classified)
from pathlib import Path
assert Path(path).exists()
print('PASS:', path)
"
```

### 3.4 Manual PM Review Rubric

| Dimension | 1 (Poor) | 3 (Acceptable) | 5 (Excellent) | Score |
|-----------|----------|----------------|---------------|-------|
| Scannability | Wall of text | Some structure | Clear headers, bullets | |
| Insight quality | Generic | Some specificity | Clear Spotify discovery insight | |
| Actionability | Vague ideas | Reasonable ideas | Prioritized, PM-ready actions | |
| Quote relevance | Off-topic | Mostly relevant | Strong theme representation | |
| Brevity | Too long/short | Near limit | Crisp, complete in ≤250 words | |

**Pass:** Average score ≥ 4.0 (recommended, E4.10).

---

## 4. Evaluation Metrics

### Run: _[YYYY-MM-DD / run_id]_

| Metric | Value | Pass? |
|--------|-------|-------|
| Classified input count | | |
| Discovery-relevant input count | | |
| Top 3 themes (names) | | |
| Word count | | |
| Quote sources used | | |
| Regeneration attempts (word limit) | | |
| PII leaks in pulse | | |
| Generation duration (seconds) | | |
| Manual PM review score (avg) | | |

---

## 5. Content Checklist

Verify pulse contains PM-ready content for downstream capstone parts:

- [ ] Themes map to research questions in [ProblemStatement.md](../../../ProblemStatement.md) §2.1
- [ ] Action ideas are testable hypotheses for Part 2 interviews
- [ ] Quotes are quotable in Part 3 problem definition deck
- [ ] Week range in header matches `run_log.json`

---

## 6. Failure Handling

| Failure | Action |
|---------|--------|
| Word count > 250 | Regenerate with stricter prompt (max 2 attempts) |
| Missing section | Fix `pulse_generator.py` template; re-run Phase 4 only |
| PII in pulse | Re-strip quotes in aggregator; re-run Phase 4 |
| Low PM review score | Tune pulse prompt; document in [decision.md](../../decision.md) |
| Duplicate quotes | Enforce diversity constraint in `aggregator.py` |

---

## 7. Sign-off

| Role | Name | Date | Result |
|------|------|------|--------|
| Implementer | | | Pass / Fail |
| Reviewer | | | Pass / Fail |

**Notes:**

---

## 8. Artifacts Produced

- [ ] `data/pulse_report.md`
- [ ] `tests/test_reporting.py` (green)
- [ ] Structural validation PASS (§3.2)
- [ ] Metrics table (§4) filled
- [ ] Optional: PM review rubric completed (§3.4)
