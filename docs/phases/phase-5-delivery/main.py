"""Phase 5 entrypoint: MCP delivery from phase-4 pulse report."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from delivery.config import PHASE4_PULSE_PATH
from delivery.mcp_delivery import phase_5_deliver

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("phase5.main")


def _extract_week_range(pulse_path: Path) -> str:
    first_line = pulse_path.read_text(encoding="utf-8").splitlines()[0].strip()
    if "—" in first_line:
        return first_line.split("—", maxsplit=1)[1].strip()
    return datetime.now().strftime("%d %B %Y")


def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Spotify Discovery Agent — Phase 5 Delivery")
    parser.add_argument(
        "--pulse",
        type=Path,
        default=PHASE4_PULSE_PATH,
        help="Path to pulse_report.md",
    )
    parser.add_argument(
        "--week-range",
        type=str,
        default="",
        help="Override week range (default: parse from pulse header)",
    )
    args = parser.parse_args()

    if not args.pulse.exists():
        logger.error("pulse_report.md not found: %s", args.pulse)
        return 1

    week_range = args.week_range or _extract_week_range(args.pulse)
    try:
        doc_url, draft_id = phase_5_deliver(str(args.pulse), week_range)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Phase 5 failed: %s", exc)
        return 1

    print("\n" + "=" * 60)
    print("  PHASE 5 DELIVERY COMPLETE")
    print("=" * 60)
    print(f"  Google Doc URL: {doc_url}")
    print(f"  Gmail Draft ID: {draft_id}")
    print("=" * 60 + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

