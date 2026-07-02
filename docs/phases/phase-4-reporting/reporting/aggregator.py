"""Aggregate classified reviews into pulse-ready summaries."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any


def filter_discovery_relevant(records: list[dict]) -> list[dict]:
    return [r for r in records if r.get("discovery_relevant") is True]


def compute_week_range(records: list[dict]) -> str:
    dates = [
        datetime.fromisoformat(str(r["date"]).replace("Z", "+00:00"))
        for r in records
    ]
    if not dates:
        today = datetime.now(timezone.utc).date()
        return today.strftime("%d %B %Y")
    start = min(dates).date()
    end = max(dates).date()
    if start.year == end.year:
        if start.month == end.month:
            return f"{start.day}–{end.day} {end.strftime('%B %Y')}"
        return f"{start.day} {start.strftime('%B')}–{end.day} {end.strftime('%B %Y')}"
    return f"{start.strftime('%d %b %Y')}–{end.strftime('%d %b %Y')}"


def aggregate_themes(records: list[dict]) -> list[dict[str, Any]]:
    """Return top 3 themes by volume with sentiment breakdown."""
    by_theme: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        by_theme[r["theme"]].append(r)

    ranked = sorted(by_theme.items(), key=lambda x: len(x[1]), reverse=True)[:3]
    result = []
    for theme, items in ranked:
        sentiments = Counter(r.get("sentiment", "neutral") for r in items)
        result.append(
            {
                "theme": theme,
                "count": len(items),
                "sentiment_positive": sentiments.get("positive", 0),
                "sentiment_neutral": sentiments.get("neutral", 0),
                "sentiment_negative": sentiments.get("negative", 0),
                "avg_confidence": round(
                    sum(float(r.get("confidence", 0)) for r in items) / len(items), 2
                ),
            }
        )
    return result


def select_quotes(records: list[dict], *, min_confidence: float = 0.6) -> list[dict]:
    """Pick 3 high-confidence quotes with theme diversity."""
    eligible = sorted(
        [r for r in records if float(r.get("confidence", 0)) >= min_confidence],
        key=lambda r: float(r.get("confidence", 0)),
        reverse=True,
    )
    chosen: list[dict] = []
    used_themes: set[str] = set()

    for record in eligible:
        theme = record.get("theme", "")
        if theme in used_themes and len(chosen) < 2:
            continue
        chosen.append(record)
        used_themes.add(theme)
        if len(chosen) == 3:
            break

    if len(chosen) < 3:
        for record in eligible:
            if record in chosen:
                continue
            chosen.append(record)
            if len(chosen) == 3:
                break
    return chosen[:3]


def build_aggregation_payload(records: list[dict]) -> dict[str, Any]:
    relevant = filter_discovery_relevant(records)
    top_themes = aggregate_themes(relevant)
    quotes = select_quotes(relevant)
    week_range = compute_week_range(relevant)
    return {
        "week_range": week_range,
        "total_analyzed": len(relevant),
        "top_themes": top_themes,
        "quotes": [
            {
                "text": q.get("original_text") or q.get("text", ""),
                "source": q.get("source"),
                "rating": q.get("rating"),
                "theme": q.get("theme"),
                "key_phrase": q.get("key_phrase"),
                "confidence": q.get("confidence"),
            }
            for q in quotes
        ],
    }
