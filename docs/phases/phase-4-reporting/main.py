"""
Phase 4 orchestrator — pulse report generation + MCP delivery.

Usage:
    python main.py                  # generate pulse + deliver
    python main.py --generate-only  # pulse_report.md only, no MCP
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from delivery.mcp_client import deliver_pulse
from reporting.aggregator import build_aggregation_payload
from reporting.config import (
    PHASE3_CLASSIFIED_PATH,
    PHASE3_ENV_PATH,
    PULSE_REPORT_PATH,
    RUN_LOG_PATH,
)
from reporting.pulse_generator import generate_pulse, validate_pulse_structure, word_count

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("phase4.main")


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def phase_4_report(classified: list[dict]) -> tuple[str, dict]:
    """Generate pulse report markdown from classified reviews."""
    payload = build_aggregation_payload(classified)
    pulse = generate_pulse(payload)
    validate_pulse_structure(pulse)
    wc = word_count(pulse)
    if wc > 250:
        raise ValueError(f"Pulse exceeds 250 words: {wc}")

    PULSE_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    PULSE_REPORT_PATH.write_text(pulse, encoding="utf-8")
    logger.info("Wrote %s (%d words)", PULSE_REPORT_PATH, wc)
    return pulse, payload


def main() -> int:
    load_dotenv()
    load_dotenv(PHASE3_ENV_PATH)  # reuse GROQ_API_KEY from Phase 3 if not set here
    load_dotenv()  # phase-4 .env overrides

    parser = argparse.ArgumentParser(description="Spotify Discovery Agent — Phase 4")
    parser.add_argument(
        "--input",
        type=Path,
        default=PHASE3_CLASSIFIED_PATH,
        help="Path to classified_reviews.json",
    )
    parser.add_argument(
        "--generate-only",
        action="store_true",
        help="Generate pulse_report.md only; skip MCP delivery",
    )
    parser.add_argument(
        "--deliver-only",
        action="store_true",
        help="Deliver existing pulse_report.md via MCP (skip Groq generation)",
    )
    args = parser.parse_args()

    if args.deliver_only:
        if not PULSE_REPORT_PATH.exists():
            logger.error("pulse_report.md not found — run without --deliver-only first")
            return 1
        pulse = PULSE_REPORT_PATH.read_text(encoding="utf-8")
        classified = (
            json.loads(args.input.read_text(encoding="utf-8")) if args.input.exists() else []
        )
        payload = build_aggregation_payload(classified) if classified else {
            "week_range": "24–28 June 2026",
            "total_analyzed": 300,
        }
        run_log = {
            "started_at": datetime.now(timezone.utc).isoformat(),
            "status": "running",
            "mode": "deliver_only",
        }
        try:
            week_range = payload.get("week_range", "24–28 June 2026")
            doc_title = f"Spotify Discovery Pulse — {week_range}"
            email_subject = f"Spotify Discovery Pulse — Week of {week_range}"
            delivery = deliver_pulse(pulse, doc_title=doc_title, email_subject=email_subject)
            run_log.update(
                {
                    "status": "success",
                    "google_doc_url": delivery["google_doc_url"],
                    "gmail_draft_id": delivery["gmail_draft_id"],
                    "recipient_email": delivery["recipient"],
                }
            )
            write_json(RUN_LOG_PATH, run_log)
            print("\n" + "=" * 62)
            print("  PHASE 4 DELIVERY COMPLETE")
            print("=" * 62)
            print(f"  Google Doc URL:  {delivery['google_doc_url']}")
            print(f"  Gmail draft ID:  {delivery['gmail_draft_id']}")
            print(f"  Recipient:       {delivery['recipient']}")
            print("=" * 62 + "\n")
            return 0
        except Exception as exc:
            run_log["status"] = "failed"
            run_log["error"] = str(exc)
            write_json(RUN_LOG_PATH, run_log)
            logger.exception("Delivery failed: %s", exc)
            return 1

    if not args.input.exists():
        logger.error("Input not found: %s", args.input)
        return 1

    classified = json.loads(args.input.read_text(encoding="utf-8"))
    relevant_count = sum(1 for r in classified if r.get("discovery_relevant"))
    logger.info("Loaded %d classified records (%d discovery-relevant)", len(classified), relevant_count)

    run_log: dict = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "status": "running",
        "classified_total": len(classified),
        "discovery_relevant_count": relevant_count,
    }

    try:
        pulse, payload = phase_4_report(classified)
        week_range = payload["week_range"]
        run_log["week_range"] = week_range
        run_log["pulse_word_count"] = word_count(pulse)
        run_log["pulse_report_path"] = str(PULSE_REPORT_PATH)

        if args.generate_only:
            run_log["status"] = "success"
            run_log["delivery"] = "skipped"
            write_json(RUN_LOG_PATH, run_log)
            print(f"\nPulse generated ({run_log['pulse_word_count']} words) -> {PULSE_REPORT_PATH}\n")
            return 0

        doc_title = f"Spotify Discovery Pulse — {week_range}"
        email_subject = f"Spotify Discovery Pulse — Week of {week_range}"
        delivery = deliver_pulse(pulse, doc_title=doc_title, email_subject=email_subject)

        run_log.update(
            {
                "status": "success",
                "google_doc_url": delivery["google_doc_url"],
                "google_doc_id": delivery["google_doc_id"],
                "gmail_draft_id": delivery["gmail_draft_id"],
                "recipient_email": delivery["recipient"],
                "mcp_server": delivery["mcp_server"],
            }
        )
        write_json(RUN_LOG_PATH, run_log)

        print("\n" + "=" * 62)
        print("  PHASE 4 DELIVERY COMPLETE")
        print("=" * 62)
        print(f"  Google Doc URL:  {delivery['google_doc_url']}")
        print(f"  Gmail draft ID:  {delivery['gmail_draft_id']}")
        print(f"  Recipient:       {delivery['recipient']}")
        print(f"  Draft status:    {delivery['draft_mcp_status']} (not sent)")
        print(f"  Pulse words:     {run_log['pulse_word_count']}")
        print(f"  Reviews analyzed:{payload['total_analyzed']}")
        print("=" * 62 + "\n")
        return 0

    except Exception as exc:
        run_log["status"] = "failed"
        run_log["error"] = str(exc)
        write_json(RUN_LOG_PATH, run_log)
        logger.exception("Phase 4 failed: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
