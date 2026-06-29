"""Fetch App Store reviews via iTunes RSS (reliable public API)."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import requests

from ingestion.config import REVIEW_WINDOW_WEEKS

logger = logging.getLogger(__name__)

APP_ID = 324684580
ITUNES_RSS_BASE = f"https://itunes.apple.com/us/rss/customerreviews/page={{page}}/id={APP_ID}/sortby=mostrecent/json"
MAX_PAGES = 15


def _parse_entry(entry: dict) -> dict | None:
    """Parse one iTunes RSS review entry (skip feed metadata entry at index 0)."""
    if "im:rating" not in entry:
        return None

    title = ""
    if "title" in entry:
        t = entry["title"]
        title = t.get("label", "") if isinstance(t, dict) else str(t)

    text = ""
    if "content" in entry:
        c = entry["content"]
        if isinstance(c, dict):
            text = c.get("label", "")
        elif isinstance(c, list) and c:
            text = c[0].get("label", "") if isinstance(c[0], dict) else str(c[0])

    updated = ""
    if "updated" in entry:
        u = entry["updated"]
        updated = u.get("label", "") if isinstance(u, dict) else str(u)

    rating_raw = entry.get("im:rating", {})
    rating = int(rating_raw.get("label", 0)) if isinstance(rating_raw, dict) else 0

    if not text and not title:
        return None

    try:
        date_iso = datetime.fromisoformat(updated.replace("Z", "+00:00")).isoformat()
    except ValueError:
        date_iso = datetime.now(timezone.utc).isoformat()

    return {
        "source": "app_store",
        "date": date_iso,
        "rating": rating,
        "title": title,
        "text": text or title,
    }


def fetch_app_store_rss(since: datetime | None = None) -> list[dict]:
    """Paginate iTunes customer review RSS feeds."""
    since = since or (datetime.now(timezone.utc) - timedelta(weeks=REVIEW_WINDOW_WEEKS))
    records: list[dict] = []
    seen: set[str] = set()

    for page in range(1, MAX_PAGES + 1):
        url = ITUNES_RSS_BASE.format(page=page)
        try:
            resp = requests.get(url, timeout=30, headers={"User-Agent": "spotify-discovery-agent/1.0"})
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as exc:
            logger.warning("iTunes RSS page %d failed: %s", page, exc)
            break

        entries = data.get("feed", {}).get("entry", [])
        if not entries:
            break

        page_oldest = None
        for entry in entries:
            record = _parse_entry(entry)
            if not record:
                continue

            try:
                dt = datetime.fromisoformat(record["date"].replace("Z", "+00:00"))
            except ValueError:
                continue

            if page_oldest is None or dt < page_oldest:
                page_oldest = dt

            if dt < since:
                continue

            key = f"{record['title']}|{record['text']}"
            if key in seen:
                continue
            seen.add(key)
            records.append(record)

        logger.info("iTunes RSS page %d: %d cumulative records", page, len(records))

        if page_oldest and page_oldest < since:
            break
        if len(entries) < 2:
            break

        # iTunes returns 50 review entries per page (plus metadata); keep paginating
        if len(entries) < 10:
            break

    return records
