"""Phase 5 orchestration from pulse_report.md to Google Doc + Gmail draft."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from delivery.config import (
    DELIVERY_REPORT_PATH,
    RUN_LOG_PATH,
    get_env,
)
from delivery.gdocs_client import build_doc_url, create_document, write_formatted_content
from delivery.gmail_client import create_draft
from delivery.mcp_client import MCPClient


def _write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def phase_5_deliver(pulse_path: str, week_range: str) -> tuple[str, str]:
    pulse = Path(pulse_path).read_text(encoding="utf-8")
    recipient = get_env("RECIPIENT_EMAIL")
    if not recipient:
        raise RuntimeError("RECIPIENT_EMAIL is not configured")

    client = MCPClient()
    tool_list = client.list_tools()

    doc_title = f"Spotify Discovery Pulse — {week_range}"
    doc_id, doc_create_result = create_document(client, doc_title)
    doc_write_result = write_formatted_content(client, doc_id, pulse, doc_title)
    doc_url = build_doc_url(doc_id)

    subject = f"Spotify Discovery Pulse — Week of {week_range}"
    body = f"{pulse}\n\nFull report: {doc_url}"
    draft_id, draft_result = create_draft(
        client,
        to=recipient,
        subject=subject,
        body=body,
    )

    report: dict[str, Any] = {
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "status": "success",
        "mcp_server": client.base_url,
        "available_tools": tool_list,
        "doc_title": doc_title,
        "doc_id": doc_id,
        "google_doc_url": doc_url,
        "gmail_draft_id": draft_id,
        "recipient_email": recipient,
        "doc_create_latency_ms": doc_create_result.get("_latency_ms"),
        "doc_write_latency_ms": doc_write_result.get("_latency_ms"),
        "gmail_draft_latency_ms": draft_result.get("_latency_ms"),
        "pulse_chars_written": len(pulse),
    }

    _write_json(DELIVERY_REPORT_PATH, report)

    run_log = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "status": "success",
        "week_range": week_range,
        "google_doc_url": doc_url,
        "gmail_draft_id": draft_id,
        "recipient_email": recipient,
    }
    _write_json(RUN_LOG_PATH, run_log)
    return doc_url, draft_id

