"""
Phase 1 orchestrator — multi-source ingestion for Spotify Discovery Agent.

Usage:
    python main.py
    python main.py --sources app_store,reddit
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from ingestion.community_forum import fetch_community_forum
from ingestion.config import DATA_DIR, RAW_REVIEWS_PATH
from ingestion.reddit import fetch_reddit
from ingestion.store_scrapers import fetch_app_store, fetch_play_store

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("phase1")


ALL_SOURCES = ("app_store", "play_store", "reddit", "community_forum")


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def phase_1_ingest(sources: tuple[str, ...] | None = None) -> list[dict]:
    """Run Phase 1 ingestion from all (or selected) sources."""
    sources = sources or ALL_SOURCES
    all_reviews: list[dict] = []
    stats: dict[str, int] = {}

    if "app_store" in sources:
        try:
            batch = fetch_app_store()
            all_reviews.extend(batch)
            stats["app_store"] = len(batch)
        except Exception as exc:
            logger.error("App Store ingestion failed: %s", exc)
            stats["app_store"] = 0

    if "play_store" in sources:
        try:
            batch = fetch_play_store()
            all_reviews.extend(batch)
            stats["play_store"] = len(batch)
        except Exception as exc:
            logger.error("Play Store ingestion failed: %s", exc)
            stats["play_store"] = 0

    if "reddit" in sources:
        try:
            batch = fetch_reddit()
            all_reviews.extend(batch)
            stats["reddit"] = len(batch)
        except Exception as exc:
            logger.error("Reddit ingestion failed: %s", exc)
            stats["reddit"] = 0

    if "community_forum" in sources:
        try:
            batch = fetch_community_forum()
            all_reviews.extend(batch)
            stats["community_forum"] = len(batch)
        except Exception as exc:
            logger.error("Community forum ingestion failed: %s", exc)
            stats["community_forum"] = 0

    # Normalize: ensure rating key exists (null for non-rated sources)
    for r in all_reviews:
        if "rating" not in r:
            r["rating"] = None
        # Drop extra fields for raw contract (keep score out of required schema)
        r.pop("score", None)

    write_json(RAW_REVIEWS_PATH, all_reviews)

    ingest_meta = {
        "phase": 1,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "total_records": len(all_reviews),
        "source_counts": stats,
        "output_path": str(RAW_REVIEWS_PATH),
    }
    write_json(DATA_DIR / "phase1_ingest_log.json", ingest_meta)

    logger.info("Phase 1 complete: %d total records", len(all_reviews))
    logger.info("Source breakdown: %s", stats)
    logger.info("Wrote %s", RAW_REVIEWS_PATH)

    return all_reviews


def main() -> int:
    load_dotenv()

    parser = argparse.ArgumentParser(description="Spotify Discovery Agent — Phase 1 Ingestion")
    parser.add_argument(
        "--sources",
        type=str,
        default=",".join(ALL_SOURCES),
        help="Comma-separated sources to fetch (default: all)",
    )
    args = parser.parse_args()
    sources = tuple(s.strip() for s in args.sources.split(",") if s.strip())

    invalid = set(sources) - set(ALL_SOURCES)
    if invalid:
        logger.error("Unknown sources: %s", invalid)
        return 1

    reviews = phase_1_ingest(sources=sources)
    if len(reviews) == 0:
        logger.error("No reviews collected — check network and dependencies")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
