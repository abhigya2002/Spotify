"""Generate weekly pulse note via Groq with word-count enforcement."""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timezone

from dotenv import load_dotenv
from groq import Groq

from reporting.config import GROQ_MODEL, MAX_PULSE_WORDS, PHASE3_ENV_PATH, PULSE_TEMPERATURE

logger = logging.getLogger("phase4.pulse")


PULSE_SYSTEM_PROMPT = f"""You are a Spotify product manager writing a weekly discovery pulse note.
Write a scannable pulse note in plain text (no markdown headers with #).
Maximum {MAX_PULSE_WORDS} words total — this is a hard limit.

Required structure exactly:
1. Header line: Spotify Discovery Pulse — [week range]
2. Blank line
3. Top 3 Themes: (section label)
   - For each of the 3 themes: theme name, one sentence summary, review count, sentiment split (positive/neutral/negative counts)
4. Blank line
5. User Quotes: (section label)
   - Exactly 3 verbatim quotes from the provided data, each on its own bullet with source and rating label
6. Blank line
7. Action Ideas: (section label)
   - Exactly 3 numbered PM-style prioritized recommendations derived from the dominant themes
8. Blank line
9. Footer line: Based on X reviews analyzed | Generated [today's date in DD Month YYYY format]

Rules:
- Use ONLY the provided aggregation data for facts, counts, and quotes
- Quotes must be verbatim from the quotes list (already PII-stripped)
- Be concise and PM-ready; no filler
- Do not exceed {MAX_PULSE_WORDS} words
"""


def word_count(text: str) -> int:
    return len(text.split())


def _get_client() -> Groq:
    load_dotenv()
    load_dotenv(PHASE3_ENV_PATH)
    load_dotenv()
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key or api_key == "your_key_here":
        raise RuntimeError("GROQ_API_KEY is not set in .env")
    return Groq(api_key=api_key)


def _format_quote_line(quote: dict) -> str:
    rating = quote.get("rating")
    rating_label = f"rating {rating}" if rating is not None else "no rating"
    return f'"{quote["text"][:280]}" — {quote["source"]}, {rating_label}'


def _build_fallback_pulse(payload: dict[str, object]) -> str:
    """Deterministic pulse if Groq exceeds word limit after retries."""
    week_range = payload["week_range"]
    total = payload["total_analyzed"]
    today = datetime.now(timezone.utc).strftime("%d %B %Y")
    lines = [f"Spotify Discovery Pulse — {week_range}", "", "Top 3 Themes:"]
    for t in payload["top_themes"]:  # type: ignore[index]
        lines.append(
            f"- {t['theme']}: Users report {t['theme'].lower()} issues. "
            f"{t['count']} reviews ({t['sentiment_positive']}+ / {t['sentiment_neutral']}~ / {t['sentiment_negative']}-)."
        )
    lines.extend(["", "User Quotes:"])
    for q in payload["quotes"]:  # type: ignore[index]
        lines.append(f"- {_format_quote_line(q)}")
    lines.extend(
        [
            "",
            "Action Ideas:",
            "1. Fix shuffle and radio repeat loops — users hear the same 20 songs despite large libraries.",
            "2. Add discovery controls — let users tune recommendation freshness vs familiarity.",
            "3. Improve algorithm transparency — explain why songs appear in mixes and playlists.",
            "",
            f"Based on {total} reviews analyzed | Generated {today}",
        ]
    )
    text = "\n".join(lines)
    if word_count(text) > MAX_PULSE_WORDS:
        # Trim quotes if needed
        lines_short = lines[:10] + lines[13:]
        text = "\n".join(lines_short)
    return text


def generate_pulse(payload: dict[str, object], *, max_attempts: int = 3) -> str:
    client = _get_client()
    today = datetime.now(timezone.utc).strftime("%d %B %Y")
    user_content = json.dumps({**payload, "generation_date": today}, ensure_ascii=False)

    for attempt in range(1, max_attempts + 1):
        extra = ""
        if attempt > 1:
            extra = f"\nPrevious attempt was too long. You MUST stay under {MAX_PULSE_WORDS} words."

        response = client.chat.completions.create(
            model=GROQ_MODEL,
            temperature=PULSE_TEMPERATURE,
            messages=[
                {"role": "system", "content": PULSE_SYSTEM_PROMPT + extra},
                {"role": "user", "content": user_content},
            ],
        )
        pulse = (response.choices[0].message.content or "").strip()
        count = word_count(pulse)
        logger.info("Pulse generation attempt %d: %d words", attempt, count)
        if count <= MAX_PULSE_WORDS:
            return pulse

    logger.warning("Groq exceeded word limit; using deterministic fallback")
    return _build_fallback_pulse(payload)


def validate_pulse_structure(pulse: str) -> None:
    lower = pulse.lower()
    for section in ("top 3 themes", "user quotes", "action ideas"):
        if section not in lower:
            raise ValueError(f"Missing section: {section}")
    if not pulse.strip().lower().startswith("spotify discovery pulse"):
        raise ValueError("Missing header")
    if "based on" not in lower:
        raise ValueError("Missing footer")
