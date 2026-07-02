"""Classification summary report for Phase 3."""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from classification.config import CLASSIFICATION_REPORT_PATH, THEMES


@dataclass
class ThemeStats:
    count: int = 0
    sentiments: list[str] = field(default_factory=list)
    confidences: list[float] = field(default_factory=list)
    quotes: list[dict[str, Any]] = field(default_factory=list)


def _sentiment_score(sentiment: str) -> float:
    return {"positive": 1.0, "neutral": 0.0, "negative": -1.0}.get(sentiment, 0.0)


def build_classification_report(classified: list[dict]) -> dict[str, Any]:
    by_theme: dict[str, ThemeStats] = {t: ThemeStats() for t in THEMES}

    for record in classified:
        theme = record.get("theme", "Unknown")
        if theme not in by_theme:
            by_theme[theme] = ThemeStats()
        stats = by_theme[theme]
        stats.count += 1
        stats.sentiments.append(record.get("sentiment", "neutral"))
        stats.confidences.append(float(record.get("confidence", 0)))

    # Top 3 quotes per theme by confidence
    theme_records: dict[str, list[dict]] = defaultdict(list)
    for record in classified:
        theme_records[record.get("theme", "")].append(record)

    top_quotes: dict[str, list[dict]] = {}
    for theme, records in theme_records.items():
        ranked = sorted(records, key=lambda r: float(r.get("confidence", 0)), reverse=True)
        top = []
        for r in ranked[:3]:
            top.append(
                {
                    "id": r.get("id"),
                    "source": r.get("source"),
                    "rating": r.get("rating"),
                    "confidence": r.get("confidence"),
                    "sentiment": r.get("sentiment"),
                    "key_phrase": r.get("key_phrase"),
                    "text": (r.get("text") or "")[:300],
                }
            )
        top_quotes[theme] = top

    theme_summary = {}
    for theme, stats in by_theme.items():
        if stats.count == 0:
            continue
        avg_sentiment = sum(_sentiment_score(s) for s in stats.sentiments) / stats.count
        theme_summary[theme] = {
            "count": stats.count,
            "pct": round(100 * stats.count / len(classified), 1) if classified else 0,
            "avg_sentiment": round(avg_sentiment, 3),
            "avg_confidence": round(sum(stats.confidences) / stats.count, 3),
            "sentiment_breakdown": {
                "positive": stats.sentiments.count("positive"),
                "neutral": stats.sentiments.count("neutral"),
                "negative": stats.sentiments.count("negative"),
            },
            "top_quotes": top_quotes.get(theme, []),
        }

    discovery_relevant = sum(1 for r in classified if r.get("discovery_relevant"))
    return {
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "total_classified": len(classified),
        "discovery_relevant_count": discovery_relevant,
        "themes": theme_summary,
    }


def print_classification_report(report: dict[str, Any]) -> None:
    lines = [
        "",
        "=" * 62,
        "  PHASE 3 CLASSIFICATION REPORT",
        "=" * 62,
        f"  Total classified:          {report['total_classified']:>6}",
        f"  Discovery-relevant:        {report['discovery_relevant_count']:>6}",
        "",
        "  Theme distribution:",
    ]

    for theme in THEMES:
        stats = report["themes"].get(theme)
        if not stats:
            lines.append(f"    {theme}: 0")
            continue
        lines.append(
            f"    {theme}: {stats['count']} ({stats['pct']}%)"
            f" | avg confidence {stats['avg_confidence']}"
            f" | avg sentiment {stats['avg_sentiment']:+.2f}"
        )
        bd = stats["sentiment_breakdown"]
        lines.append(
            f"      sentiment: +{bd['positive']} / ~{bd['neutral']} / -{bd['negative']}"
        )

    lines.append("")
    lines.append("  Top 3 quotes per theme (by confidence):")
    for theme in THEMES:
        quotes = report["themes"].get(theme, {}).get("top_quotes", [])
        if not quotes:
            continue
        lines.append(f"\n  --- {theme} ---")
        for i, q in enumerate(quotes, 1):
            lines.append(f"    {i}. [{q['source']}|{q['sentiment']}|conf={q['confidence']}]")
            lines.append(f"       \"{q['key_phrase']}\"")
            snippet = q["text"][:200] + ("..." if len(q["text"]) > 200 else "")
            lines.append(f"       {snippet}")

    lines.extend(["", "=" * 62, ""])
    print("\n".join(lines))


def save_classification_report(report: dict[str, Any], path: Path | None = None) -> Path:
    path = path or CLASSIFICATION_REPORT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return path
