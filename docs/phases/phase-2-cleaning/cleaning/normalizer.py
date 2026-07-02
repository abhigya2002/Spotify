"""Text normalization, PII stripping, and date helpers."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone

from langdetect import LangDetectException, detect

PII_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),  # email
    re.compile(r"@\w+"),  # handles
    re.compile(r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b"),  # phone
    re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE),  # URLs
)

EMOJI_PATTERN = re.compile(
    "["
    "\U0001F600-\U0001F64F"
    "\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F6FF"
    "\U0001F1E0-\U0001F1FF"
    "\U00002702-\U000027B0"
    "\U000024C2-\U0001F251"
    "\u200d"
    "\ufe0f"
    "]+",
    flags=re.UNICODE,
)

SPECIAL_CHAR_PATTERN = re.compile(r"[^\w\s.,!?\'\-]", flags=re.UNICODE)
WHITESPACE_PATTERN = re.compile(r"\s+")


def strip_pii(text: str) -> str:
    for pattern in PII_PATTERNS:
        text = pattern.sub("[REDACTED]", text)
    return text


def strip_emojis(text: str) -> str:
    return EMOJI_PATTERN.sub("", text)


def strip_special_chars(text: str) -> str:
    return SPECIAL_CHAR_PATTERN.sub("", text)


def normalize_whitespace(text: str) -> str:
    return WHITESPACE_PATTERN.sub(" ", text).strip()


def clean_text(text: str) -> str:
    """Apply full text-cleaning pipeline (PII last so URLs/emails are removed)."""
    text = strip_emojis(text)
    text = strip_special_chars(text)
    text = normalize_whitespace(text)
    text = strip_pii(text)
    return normalize_whitespace(text)


def word_count(text: str) -> int:
    text = text.strip()
    if not text:
        return 0
    return len(text.split())


def parse_date(date_str: str) -> datetime:
    normalized = str(date_str).replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def normalize_date(date_str: str) -> str:
    return parse_date(date_str).isoformat()


def detect_language(text: str) -> str | None:
    """Return ISO 639-1 language code, or None if detection fails."""
    sample = text.strip()
    if len(sample) < 20:
        return None
    try:
        return detect(sample)
    except LangDetectException:
        return None


def is_english(text: str) -> bool:
    lang = detect_language(text)
    return lang == "en"


def make_record_id(source: str, date: str, original_text: str) -> str:
    payload = f"{source}|{date}|{original_text}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
