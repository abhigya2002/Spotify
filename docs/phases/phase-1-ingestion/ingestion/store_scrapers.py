"""Invoke Node.js store scrapers from Python."""

from __future__ import annotations

import json
import logging
import os
import subprocess
from pathlib import Path

from ingestion.app_store_rss import fetch_app_store_rss
from ingestion.config import INGESTION_DIR, PROJECT_ROOT, REVIEW_WINDOW_WEEKS

logger = logging.getLogger(__name__)


def _node_env() -> dict[str, str]:
    env = os.environ.copy()
    env["REVIEW_WINDOW_WEEKS"] = str(REVIEW_WINDOW_WEEKS)
    return env


def _run_node_scraper(script_name: str) -> list[dict]:
    script = INGESTION_DIR / script_name
    if not script.exists():
        raise FileNotFoundError(f"Scraper not found: {script}")

    result = subprocess.run(
        ["node", str(script)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        cwd=str(PROJECT_ROOT),
        env=_node_env(),
    )

    if result.returncode != 0:
        stderr = result.stderr.strip()
        raise RuntimeError(f"{script_name} failed (exit {result.returncode}): {stderr}")

    stdout = result.stdout.strip()
    if not stdout:
        logger.warning("%s returned empty output", script_name)
        return []

    return json.loads(stdout)


def fetch_app_store() -> list[dict]:
    logger.info("Fetching App Store reviews (iTunes RSS)...")
    records = fetch_app_store_rss()
    if len(records) < 50:
        logger.info("iTunes RSS returned few records; trying app-store-scraper fallback...")
        try:
            node_records = _run_node_scraper("app_store.js")
            if len(node_records) > len(records):
                records = node_records
        except Exception as exc:
            logger.warning("app-store-scraper fallback failed: %s", exc)
    logger.info("App Store: %d records", len(records))
    return records


def fetch_play_store() -> list[dict]:
    logger.info("Fetching Play Store reviews...")
    records = _run_node_scraper("play_store.js")
    logger.info("Play Store: %d records", len(records))
    return records
