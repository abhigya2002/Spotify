from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from delivery.gdocs_client import build_doc_url, create_document, write_formatted_content
from delivery.gmail_client import create_draft
from delivery.mcp_client import MCPClient


def test_build_doc_url() -> None:
    assert build_doc_url("abc123").endswith("/d/abc123/edit")


def test_forbidden_send_guard() -> None:
    client = MCPClient(base_url="https://example.com")
    with pytest.raises(RuntimeError):
        client.invoke_tool("send_email", {})


def test_create_document_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    client = MCPClient(base_url="https://example.com")
    monkeypatch.setenv("GOOGLE_DOC_ID", "fallbackDoc")

    def _raise(*_args, **_kwargs):
        raise NotImplementedError("no docs_create")

    monkeypatch.setattr(client, "invoke_tool", _raise)
    doc_id, meta = create_document(client, "Title")
    assert doc_id == "fallbackDoc"
    assert meta["status"] == "success"


def test_write_formatted_content_calls_docs_write() -> None:
    client = MCPClient(base_url="https://example.com")
    mock = MagicMock(return_value={"status": "success"})
    client.invoke_tool = mock  # type: ignore[method-assign]
    result = write_formatted_content(client, "doc1", "hello pulse", "Pulse title")
    assert result["status"] == "success"
    mock.assert_called_once()
    assert mock.call_args[0][0] == "docs_writeText"


def test_create_draft_uses_gmail_tool() -> None:
    client = MCPClient(base_url="https://example.com")
    mock = MagicMock(return_value={"status": "success", "draft_id": "draft1"})
    client.invoke_tool = mock  # type: ignore[method-assign]
    draft_id, _ = create_draft(
        client,
        to="user@example.com",
        subject="subject",
        body="body",
    )
    assert draft_id == "draft1"
    assert mock.call_args[0][0] == "gmail_createDraft"

