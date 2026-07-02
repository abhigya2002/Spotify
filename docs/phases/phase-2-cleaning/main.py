"""
Phase 2 orchestrator — cleaning and normalization for Spotify Discovery Agent.

Usage:
    python main.py
    python main.py --input ../phase-1-ingestion/data/raw_reviews.json
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

from cleaning.config import CLEAN_REVIEWS_PATH, MIN_DISCOVERY_RECORDS, PHASE1_RAW_PATH
from cleaning.pipeline import print_cleaning_report, run_cleaning_report

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("phase2.main")


def main() -> int:
    load_dotenv()

    parser = argparse.ArgumentParser(description="Spotify Discovery Agent — Phase 2 Cleaning")
    parser.add_argument(
        "--input",
        type=Path,
        default=PHASE1_RAW_PATH,
        help="Path to raw_reviews.json from Phase 1",
    )
    args = parser.parse_args()

    if not args.input.exists():
        logger.error("Input file not found: %s", args.input)
        return 1

    try:
        clean, report = run_cleaning_report(args.input)
    except Exception as exc:
        logger.exception("Phase 2 cleaning failed: %s", exc)
        return 1

    if report.passed == 0:
        logger.error("No records passed cleaning — check filters and input data")
        return 1

    if not report.target_met:
        logger.warning(
            "Passed %d records — below target of %d discovery-relevant records",
            report.passed,
            MIN_DISCOVERY_RECORDS,
        )

    logger.info("Phase 2 complete: %d clean records → %s", len(clean), CLEAN_REVIEWS_PATH)
    return 0


if __name__ == "__main__":
    sys.exit(main())
