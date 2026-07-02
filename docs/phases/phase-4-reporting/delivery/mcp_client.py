"""HTTP client for saksham-mcp-server on Railway."""

from __future__ import annotations

import logging
import os
from typing import Any

import requests
from dotenv import load_dotenv

from reporting.config import GOOGLE_DOC_ID, MCP_SERVER_URL, PHASE3_ENV_PATH, RECIPIENT_EMAIL

logger = logging.getLogger("phase4.mcp")

FORBIDDEN_ENDPOINTS = {"/send_email"}


def _doc_url(doc_id: str) -> str:
    return f"https://docs.google.com/document/d/{doc_id}/edit"


def _load_config() -> tuple[str, str, str]:
    load_dotenv(PHASE3_ENV_PATH)
    load_dotenv()
    base = os.getenv("MCP_SERVER_URL", MCP_SERVER_URL).rstrip("/")
    doc_id = os.getenv("GOOGLE_DOC_ID", GOOGLE_DOC_ID)
    recipient = os.getenv("RECIPIENT_EMAIL", RECIPIENT_EMAIL)
    if not doc_id or doc_id == "your_google_doc_id_here":
        raise RuntimeError(
            "GOOGLE_DOC_ID is not set. Create a Google Doc and add its ID to .env"
        )
    if not recipient or recipient == "your-email@example.com":
        raise RuntimeError("RECIPIENT_EMAIL is not set in .env")
    return base, doc_id, recipient


def mcp_append_to_doc(doc_id: str, content: str, *, base_url: str | None = None) -> dict[str, Any]:
    base = (base_url or MCP_SERVER_URL).rstrip("/")
    url = f"{base}/append_to_doc"
    payload = {"doc_id": doc_id, "content": content}
    logger.info("MCP append_to_doc → %s", url)
    response = requests.post(url, json=payload, timeout=120)
    response.raise_for_status()
    result = response.json()
    if result.get("status") != "success":
        raise RuntimeError(f"append_to_doc failed: {result}")
    return result


def mcp_create_email_draft(
    to: str,
    subject: str,
    body: str,
    *,
    base_url: str | None = None,
) -> dict[str, Any]:
    base = (base_url or MCP_SERVER_URL).rstrip("/")
    endpoint = f"{base}/create_email_draft"
    if endpoint.endswith("/send_email"):
        raise RuntimeError("Auto-send is forbidden")
    payload = {"to": to, "subject": subject, "body": body}
    logger.info("MCP create_email_draft → %s", endpoint)
    response = requests.post(endpoint, json=payload, timeout=120)
    response.raise_for_status()
    result = response.json()
    if result.get("status") != "success":
        raise RuntimeError(f"create_email_draft failed: {result}")
    return result


def deliver_pulse(
    pulse: str,
    *,
    doc_title: str,
    email_subject: str,
) -> dict[str, str]:
    """Deliver pulse to Google Doc (append) and Gmail draft via MCP."""
    base, doc_id, recipient = _load_config()
    doc_content = f"{doc_title}\n\n{'=' * 60}\n\n{pulse}"
    doc_result = mcp_append_to_doc(doc_id, doc_content, base_url=base)
    doc_url = _doc_url(doc_id)

    email_body = f"{pulse}\n\n---\nFull report: {doc_url}"
    draft_result = mcp_create_email_draft(
        to=recipient,
        subject=email_subject,
        body=email_body,
        base_url=base,
    )

    return {
        "google_doc_url": doc_url,
        "google_doc_id": doc_id,
        "gmail_draft_id": str(draft_result.get("draft_id", "")),
        "mcp_server": base,
        "recipient": recipient,
        "doc_mcp_status": doc_result.get("status", ""),
        "draft_mcp_status": draft_result.get("status", ""),
    }
