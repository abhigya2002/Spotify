"""Gmail draft wrapper for Phase 5."""

from __future__ import annotations

from typing import Any

from delivery.mcp_client import MCPClient


def create_draft(
    client: MCPClient,
    *,
    to: str,
    subject: str,
    body: str,
) -> tuple[str, dict[str, Any]]:
    result = client.invoke_tool(
        "gmail_createDraft",
        {"to": to, "subject": subject, "body": body},
    )
    draft_id = str(result.get("draft_id") or result.get("id") or "")
    if not draft_id:
        raise RuntimeError(f"gmail_createDraft response missing draft id: {result}")
    return draft_id, result

