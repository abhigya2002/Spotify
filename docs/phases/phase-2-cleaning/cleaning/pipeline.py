"""Phase 2 cleaning pipeline and reporting."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cleaning.config import (
    CLEAN_REVIEWS_PATH,
    CLEANING_REPORT_PATH,
    DATA_DIR,
    MIN_DISCOVERY_RECORDS,
    PHASE1_RAW_PATH,
)
from cleaning.filters import (
    combined_review_text,
    is_discovery_relevant,
    is_empty_text,
    is_within_date_window,
    meets_min_word_count,
)
from cleaning.normalizer import (
    clean_text,
    is_english,
    make_record_id,
    normalize_date,
    strip_pii,
    word_count,
)

logger = logging.getLogger("phase2")


@dataclass
class CleaningReport:
    total_in: int = 0
    dropped_empty_text: int = 0
    dropped_outside_date_window: int = 0
    dropped_duplicate: int = 0
    dropped_min_words: int = 0
    dropped_non_english: int = 0
    dropped_not_discovery_relevant: int = 0
    passed: int = 0
    completed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    target_min_records: int = MIN_DISCOVERY_RECORDS
    target_met: bool = False

    @property
    def total_dropped(self) -> int:
        return (
            self.dropped_empty_text
            + self.dropped_outside_date_window
            + self.dropped_duplicate
            + self.dropped_min_words
            + self.dropped_non_english
            + self.dropped_not_discovery_relevant
        )


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def phase_2_clean(
    raw: list[dict],
    *,
    write_output: bool = True,
    reference_time: datetime | None = None,
) -> tuple[list[dict], CleaningReport]:
    """Filter and normalize raw reviews into discovery-relevant clean records."""
    report = CleaningReport(total_in=len(raw))
    clean: list[dict] = []
    seen_texts: set[str] = set()

    for record in raw:
        body = record.get("text")
        if is_empty_text(body):
            report.dropped_empty_text += 1
            continue

        original_text = str(body).strip()

        if not is_within_date_window(record["date"], reference=reference_time):
            report.dropped_outside_date_window += 1
            continue

        if original_text in seen_texts:
            report.dropped_duplicate += 1
            continue
        seen_texts.add(original_text)

        if not meets_min_word_count(original_text):
            report.dropped_min_words += 1
            continue

        searchable = combined_review_text(record)
        if not is_english(searchable):
            report.dropped_non_english += 1
            continue

        if not is_discovery_relevant(searchable):
            report.dropped_not_discovery_relevant += 1
            continue

        cleaned_text = clean_text(original_text)
        cleaned_title = strip_pii(str(record.get("title") or "").strip())

        clean_record: dict[str, Any] = {
            "id": make_record_id(record["source"], record["date"], original_text),
            "source": record["source"],
            "date": normalize_date(record["date"]),
            "rating": record.get("rating"),
            "title": cleaned_title,
            "text": cleaned_text,
            "word_count": word_count(cleaned_text),
            "language": "en",
            "discovery_relevant": True,
            "original_text": original_text,
        }
        clean.append(clean_record)

    report.passed = len(clean)
    report.target_met = report.passed >= MIN_DISCOVERY_RECORDS

    if write_output:
        write_json(CLEAN_REVIEWS_PATH, clean)
        write_json(CLEANING_REPORT_PATH, asdict(report))

    return clean, report


def print_cleaning_report(report: CleaningReport) -> None:
    """Print human-readable cleaning summary to stdout."""
    lines = [
        "",
        "=" * 52,
        "  PHASE 2 CLEANING REPORT",
        "=" * 52,
        f"  Total records in:              {report.total_in:>6}",
        "",
        "  Records dropped:",
        f"    - Empty / null / whitespace: {report.dropped_empty_text:>6}",
        f"    - Outside 12-week window:    {report.dropped_outside_date_window:>6}",
        f"    - Duplicate (exact text):      {report.dropped_duplicate:>6}",
        f"    - Fewer than 8 words:          {report.dropped_min_words:>6}",
        f"    - Non-English:                 {report.dropped_non_english:>6}",
        f"    - Not discovery-relevant:      {report.dropped_not_discovery_relevant:>6}",
        f"    - Total dropped:               {report.total_dropped:>6}",
        "",
        f"  Records passing to Phase 3:      {report.passed:>6}",
        f"  Target (min {report.target_min_records}):              "
        f"{'MET' if report.target_met else 'NOT MET'}",
        "=" * 52,
        "",
    ]
    print("\n".join(lines))


def run_cleaning_report(
    raw_path: Path | None = None,
    *,
    reference_time: datetime | None = None,
) -> tuple[list[dict], CleaningReport]:
    path = raw_path or PHASE1_RAW_PATH
    raw = json.loads(path.read_text(encoding="utf-8"))
    clean, report = phase_2_clean(raw, reference_time=reference_time)
    print_cleaning_report(report)
    logger.info("Wrote %s (%d records)", CLEAN_REVIEWS_PATH, len(clean))
    logger.info("Wrote %s", CLEANING_REPORT_PATH)
    return clean, report
