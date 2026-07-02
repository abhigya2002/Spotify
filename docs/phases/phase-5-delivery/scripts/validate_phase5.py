"""Validate Phase 5 delivery artifacts."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUN_LOG = ROOT / "data" / "run_log.json"
REPORT = ROOT / "data" / "phase5_delivery_report.json"


def main() -> int:
    errors: list[str] = []
    if not RUN_LOG.exists():
        errors.append("run_log.json missing")
    if not REPORT.exists():
        errors.append("phase5_delivery_report.json missing")

    if errors:
        print("FAIL:")
        for err in errors:
            print(f"- {err}")
        return 1

    run = json.loads(RUN_LOG.read_text(encoding="utf-8"))
    report = json.loads(REPORT.read_text(encoding="utf-8"))

    required_run = {"status", "google_doc_url", "gmail_draft_id", "recipient_email"}
    missing_run = required_run - run.keys()
    if missing_run:
        errors.append(f"run_log missing {sorted(missing_run)}")

    if run.get("status") != "success":
        errors.append("run_log status is not success")
    if not str(run.get("google_doc_url", "")).startswith("https://docs.google.com/"):
        errors.append("google_doc_url invalid")
    if not str(run.get("gmail_draft_id", "")).strip():
        errors.append("gmail_draft_id missing")

    required_report = {"status", "google_doc_url", "gmail_draft_id", "recipient_email"}
    missing_report = required_report - report.keys()
    if missing_report:
        errors.append(f"delivery_report missing {sorted(missing_report)}")

    if errors:
        print("FAIL:")
        for err in errors:
            print(f"- {err}")
        return 1

    print("PHASE 5 VALIDATION: PASS")
    print(f"Doc:   {run['google_doc_url']}")
    print(f"Draft: {run['gmail_draft_id']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

