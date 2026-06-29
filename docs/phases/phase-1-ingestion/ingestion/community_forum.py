"""Fetch Spotify Community forum idea threads and comments (public pages)."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from html import unescape
from typing import Any

import requests
from bs4 import BeautifulSoup

from ingestion.config import COMMUNITY_FORUM_URLS

logger = logging.getLogger(__name__)

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; spotify-discovery-agent/1.0; "
        "+https://github.com/nextleap-capstone)"
    ),
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
}


def _parse_forum_date(raw: str) -> str:
    """Best-effort parse of Spotify community date strings."""
    raw = raw.strip()
    if not raw:
        return datetime.now(timezone.utc).isoformat()

    # e.g. "2021-03-18 04:01 PM" or "2026-01-06 03:02 PM"
    for fmt in (
        "%Y-%m-%d %I:%M %p",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
    ):
        try:
            dt = datetime.strptime(raw, fmt).replace(tzinfo=timezone.utc)
            return dt.isoformat()
        except ValueError:
            continue

    return datetime.now(timezone.utc).isoformat()


def _clean_text(text: str) -> str:
    text = unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _extract_likes(soup: BeautifulSoup) -> int | None:
    """Parse like count from idea header area."""
    for node in soup.find_all(string=re.compile(r"^\s*\d[\d,]*\s+Likes\s*$", re.I)):
        match = re.search(r"([\d,]+)", node)
        if match:
            return int(match.group(1).replace(",", ""))
    return None


def _to_record(
    *,
    title: str,
    text: str,
    date_str: str,
    likes: int | None = None,
    thread_url: str = "",
) -> dict:
    prefix = ""
    if thread_url:
        slug = thread_url.rstrip("/").split("/")[-1]
        prefix = f"[forum:{slug}] "
    return {
        "source": "community_forum",
        "date": _parse_forum_date(date_str),
        "rating": likes,
        "title": f"{prefix}{title}".strip(),
        "text": text,
    }


def _parse_idea_page(html: str, url: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    records: list[dict] = []

    # Main idea title — usually in h1 or title-like heading
    title_el = soup.find("h1") or soup.find("title")
    idea_title = _clean_text(title_el.get_text()) if title_el else "Spotify Community Idea"

    # Strip site suffix from title
    idea_title = re.sub(r"\s*-\s*The Spotify Community\s*$", "", idea_title, flags=re.I)

    # Main post body — first substantial message block after idea header
    main_body = ""
    likes = _extract_likes(soup)
    submitted_date = ""

    # Submitted date pattern: "Submitted by user on 2021-03-18 04:01 PM"
    for text in soup.stripped_strings:
        if "Submitted by" in text and " on " in text:
            match = re.search(r"on\s+(.+)$", text)
            if match:
                submitted_date = match.group(1).strip()
            break

    # Idea description — look for paragraph blocks in main content
    content_candidates = soup.select(
        "div.lia-message-body-content, div.message-body, "
        "div.lia-component-message-view-widget-body, article p"
    )
    paragraphs = []
    for el in content_candidates:
        t = _clean_text(el.get_text())
        if len(t) > 40 and t not in paragraphs:
            paragraphs.append(t)
    if paragraphs:
        main_body = "\n\n".join(paragraphs[:3])
    else:
        # Fallback: meta description
        meta = soup.find("meta", attrs={"name": "description"})
        if meta and meta.get("content"):
            main_body = _clean_text(meta["content"])

    if main_body or idea_title:
        records.append(
            _to_record(
                title=idea_title,
                text=main_body or idea_title,
                date_str=submitted_date,
                likes=likes,
                thread_url=url,
            )
        )

    # Comments — community uses message list items
    comment_blocks = soup.select(
        "div.lia-message-view-wrapper, div.MessageView, "
        "div[class*='message-view'], div.lia-component-comments"
    )

    seen_text: set[str] = set()
    for block in comment_blocks:
        author_date = block.find(string=re.compile(r"20\d{2}-\d{2}-\d{2}"))
        date_str = ""
        if author_date:
            match = re.search(r"(20\d{2}-\d{2}-\d{2}\s+\d{1,2}:\d{2}\s*(?:AM|PM)?)", str(author_date))
            if match:
                date_str = match.group(1)

        body_el = block.select_one(
            "div.lia-message-body-content, div.message-body, div.lia-message-body"
        )
        if not body_el:
            continue
        body = _clean_text(body_el.get_text())
        if len(body) < 20 or body in seen_text:
            continue
        seen_text.add(body)

        # Skip boilerplate / staff replies that are only status updates
        if body.startswith("Hello and thanks for bringing your feedback"):
            continue
        if "Status changed to:" in body and len(body) < 200:
            continue

        records.append(
            _to_record(
                title=f"Comment on: {idea_title[:80]}",
                text=body,
                date_str=date_str or submitted_date,
                likes=None,
                thread_url=url,
            )
        )

    return records


def _page_url(base_url: str, page: int) -> str:
    """Build paginated Spotify Community URL (Khoros /page/N pattern)."""
    base = base_url.rstrip("/")
    if page <= 1:
        return base
    return f"{base}/page/{page}"


def fetch_community_forum(urls: list[str] | None = None, max_pages_per_thread: int = 5) -> list[dict]:
    """Fetch configured Spotify Community forum idea threads with pagination."""
    urls = urls or COMMUNITY_FORUM_URLS
    records: list[dict] = []
    seen_text: set[str] = set()
    warnings: list[str] = []

    for url in urls:
        thread_records: list[dict] = []
        for page in range(1, max_pages_per_thread + 1):
            page_url = _page_url(url, page)
            try:
                logger.info("Fetching forum thread page %d: %s", page, page_url)
                resp = requests.get(page_url, headers=REQUEST_HEADERS, timeout=45)
                if resp.status_code == 404:
                    break
                resp.raise_for_status()
                batch = _parse_idea_page(resp.text, url)
                if not batch:
                    break
                new_on_page = 0
                for rec in batch:
                    key = rec["text"][:200]
                    if key not in seen_text:
                        seen_text.add(key)
                        thread_records.append(rec)
                        new_on_page += 1
                if new_on_page == 0:
                    break
            except requests.RequestException as exc:
                msg = f"HTTP error for {page_url}: {exc}"
                logger.warning(msg)
                warnings.append(msg)
                break
            except Exception as exc:
                msg = f"Parse error for {page_url}: {exc}"
                logger.warning(msg)
                warnings.append(msg)
                break

        records.extend(thread_records)
        logger.info("Forum %s: %d records (all pages)", url.split("/")[-1], len(thread_records))

    if warnings:
        logger.warning("Forum fetch completed with %d warning(s)", len(warnings))

    logger.info("Community forum total: %d records", len(records))
    return records
