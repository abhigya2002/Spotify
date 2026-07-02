"""Hard filters and discovery-relevance matching."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from cleaning.config import DISCOVERY_PHRASES, MIN_WORD_COUNT, REVIEW_WINDOW_WEEKS
from cleaning.normalizer import is_english, parse_date, word_count

# Longest phrases first so multi-word clusters match before substrings.
_SORTED_PHRASES = sorted(DISCOVERY_PHRASES, key=len, reverse=True)
_DISCOVERY_PATTERNS = tuple(
    re.compile(rf"\b{re.escape(phrase)}\b", re.IGNORECASE) for phrase in _SORTED_PHRASES
)


def is_empty_text(text: str | None) -> bool:
    return text is None or not str(text).strip()


def is_within_date_window(date_str: str, *, reference: datetime | None = None) -> bool:
    reference = reference or datetime.now(timezone.utc)
    since = reference - timedelta(weeks=REVIEW_WINDOW_WEEKS)
    return parse_date(date_str) >= since


def meets_min_word_count(text: str) -> bool:
    return word_count(text) >= MIN_WORD_COUNT


def is_discovery_relevant(text: str) -> bool:
    """True if text contains at least one discovery topic phrase."""
    for pattern in _DISCOVERY_PATTERNS:
        if pattern.search(text):
            return True
    return False


def combined_review_text(record: dict) -> str:
    title = str(record.get("title") or "").strip()
    body = str(record.get("text") or "").strip()
    if title and body:
        return f"{title} {body}"
    return title or body
