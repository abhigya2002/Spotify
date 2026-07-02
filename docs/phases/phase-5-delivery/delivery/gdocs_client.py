"""Google Docs delivery wrapper for Phase 5."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from delivery.config import get_env
from delivery.mcp_client import MCPClient


def build_doc_url(doc_id: str) -> str:
    return f"https://docs.google.com/document/d/{doc_id}/edit"


def create_document(client: MCPClient, title: str) -> tuple[str, dict[str, Any]]:
    """Create a new Google Doc using docs_create if available.

    Fallback: use GOOGLE_DOC_ID from env if server lacks docs_create.
    """
    try:
        result = client.invoke_tool("docs_create", {"title": title})
        doc_id = str(result.get("document_id") or result.get("doc_id") or "")
        if not doc_id:
            raise RuntimeError(f"docs_create response missing document id: {result}")
        return doc_id, result
    except NotImplementedError:
        fallback_doc_id = get_env("GOOGLE_DOC_ID")
        if not fallback_doc_id:
            raise
        return fallback_doc_id, {"status": "success", "mode": "fallback_existing_doc"}


def _section_headers() -> tuple[str, ...]:
    return ("Top 3 Themes:", "User Quotes:", "Action Ideas:", "Based on ")


def write_formatted_content(client: MCPClient, doc_id: str, pulse_text: str, title: str) -> dict[str, Any]:
    """Write pulse content into the target doc.

    For saksham server we append plaintext. For richer MCP servers, this wrapper
    still uses docs_writeText-compatible payload.
    """
    timestamp = datetime.now(timezone.utc).strftime("%d %B %Y, %H:%M UTC")
    content = f"{title}\n\n{pulse_text}\n\nRun Metadata:\n- Delivered: {timestamp}\n"
    result = client.invoke_tool(
        "docs_writeText",
        {
            "doc_id": doc_id,
            "content": content,
        },
    )
    return result

