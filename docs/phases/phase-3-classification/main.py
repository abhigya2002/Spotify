"""
Phase 3 orchestrator — LLM classification via Groq.

Usage:
    python main.py --plan              # Show batch plan only (default)
    python main.py --run               # Classify all clean reviews (requires GROQ_API_KEY)
    python main.py --run --sample 5    # Classify 5 reviews for a quick test
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from classification.classifier import (
    classify_all,
    plan_batches,
    print_batch_plan,
)
from classification.config import (
    BATCH_SIZE,
    CLASSIFIED_REVIEWS_PATH,
    PHASE2_CLEAN_PATH,
)
from classification.report import (
    build_classification_report,
    print_classification_report,
    save_classification_report,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("phase3.main")


def load_clean_reviews(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    load_dotenv()

    parser = argparse.ArgumentParser(description="Spotify Discovery Agent — Phase 3 Classification")
    parser.add_argument(
        "--input",
        type=Path,
        default=PHASE2_CLEAN_PATH,
        help="Path to clean_reviews.json from Phase 2",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=int(os.getenv("BATCH_SIZE", str(BATCH_SIZE))),
        help="Reviews per Groq API call (default: 20)",
    )
    parser.add_argument(
        "--plan",
        action="store_true",
        help="Print batch plan and exit (no API calls)",
    )
    parser.add_argument(
        "--run",
        action="store_true",
        help="Execute classification (requires GROQ_API_KEY in .env)",
    )
    parser.add_argument(
        "--sample",
        type=int,
        default=0,
        help="Classify only N reviews (use with --run for a quick test)",
    )
    args = parser.parse_args()

    if not args.input.exists():
        logger.error("Input file not found: %s", args.input)
        return 1

    reviews = load_clean_reviews(args.input)
    if args.sample > 0:
        reviews = reviews[: args.sample]

    plan = plan_batches(reviews, batch_size=args.batch_size)
    print_batch_plan(plan)

    if not args.run:
        print(
            "No API calls made. To classify, add GROQ_API_KEY to .env then run:\n"
            "  python main.py --run\n"
            "  python main.py --run --sample 5   # quick test first\n"
        )
        return 0

    try:
        classified, stats = classify_all(
            reviews,
            batch_size=args.batch_size,
            write_output=True,
        )
    except RuntimeError as exc:
        logger.error("%s", exc)
        return 1
    except Exception as exc:
        logger.exception("Classification failed: %s", exc)
        return 1

    report = build_classification_report(classified)
    save_classification_report(report)
    print_classification_report(report)

    logger.info(
        "Phase 3 complete: %d classified | %d batches | %.1fs | tokens=%s",
        len(classified),
        stats.batches_sent,
        stats.duration_seconds,
        stats.actual_total_tokens or stats.est_total_tokens,
    )
    logger.info("Wrote %s", CLASSIFIED_REVIEWS_PATH)
    return 0


if __name__ == "__main__":
    sys.exit(main())
