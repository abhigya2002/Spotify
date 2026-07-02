"""Low-level MCP HTTP client.

Supports both:
1) Generic MCP-style tool names (`docs_create`, `docs_writeText`, `gmail_createDraft`)
2) saksham-mcp-server endpoints (`append_to_doc`, `create_email_draft`)
"""

from __future__ import annotations

import logging
from time import perf_counter
from typing import Any

import requests

from delivery.config import get_env

logger = logging.getLogger("phase5.mcp_client")

FORBIDDEN_TOOLS = {"gmail_send", "gmail_sendDraft", "send_email"}


class MCPClient:
    """HTTP client wrapper for MCP server."""

    def __init__(self, base_url: str | None = None, timeout_seconds: int = 120) -> None:
        self.base_url = (base_url or get_env("MCP_SERVER_URL")).rstrip("/")
        self.timeout_seconds = timeout_seconds
        if not self.base_url:
            raise RuntimeError("MCP_SERVER_URL is not configured")

    def list_tools(self) -> list[dict[str, Any]]:
        response = requests.get(f"{self.base_url}/tools", timeout=self.timeout_seconds)
        response.raise_for_status()
        body = response.json()
        if isinstance(body, list):
            return body
        return []

    def invoke_tool(self, tool_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        if tool_name in FORBIDDEN_TOOLS:
            raise RuntimeError("Auto-send is forbidden. Use draft-only delivery.")

        start = perf_counter()
        endpoint, normalized_payload = self._resolve_endpoint(tool_name, payload)
        url = f"{self.base_url}{endpoint}"
        logger.info("MCP invoke %s -> %s", tool_name, endpoint)

        response = requests.post(url, json=normalized_payload, timeout=self.timeout_seconds)
        response.raise_for_status()
        result = response.json()
        elapsed_ms = int((perf_counter() - start) * 1000)
        result["_latency_ms"] = elapsed_ms
        result["_tool"] = tool_name
        result["_endpoint"] = endpoint
        return result

    def _resolve_endpoint(
        self, tool_name: str, payload: dict[str, Any]
    ) -> tuple[str, dict[str, Any]]:
        """Map abstract tool names to server endpoints.

        - Preferred: docs_create/docs_writeText/gmail_createDraft
        - Fallback for saksham server: append_to_doc/create_email_draft
        """
        if tool_name in {"docs_writeText", "docs_append_text"}:
            return "/append_to_doc", {
                "doc_id": payload["doc_id"],
                "content": payload["content"],
            }
        if tool_name == "gmail_createDraft":
            return "/create_email_draft", {
                "to": payload["to"],
                "subject": payload["subject"],
                "body": payload["body"],
            }
        if tool_name == "docs_create":
            # saksham server does not support doc creation endpoint.
            raise NotImplementedError(
                "docs_create is not available on this MCP server. "
                "Set GOOGLE_DOC_ID and use docs_writeText fallback path."
            )
        if tool_name == "append_to_doc":
            return "/append_to_doc", payload
        if tool_name == "create_email_draft":
            return "/create_email_draft", payload

        raise ValueError(f"Unsupported MCP tool: {tool_name}")

