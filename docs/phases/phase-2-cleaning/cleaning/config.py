"""Shared configuration for Phase 2 cleaning."""

from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
PHASE1_RAW_PATH = PROJECT_ROOT.parent / "phase-1-ingestion" / "data" / "raw_reviews.json"
CLEAN_REVIEWS_PATH = DATA_DIR / "clean_reviews.json"
CLEANING_REPORT_PATH = DATA_DIR / "phase2_cleaning_report.json"

REVIEW_WINDOW_WEEKS = int(os.getenv("REVIEW_WINDOW_WEEKS", "12"))
MIN_WORD_COUNT = int(os.getenv("MIN_WORD_COUNT", "8"))
MIN_DISCOVERY_RECORDS = int(os.getenv("MIN_DISCOVERY_RECORDS", "300"))

DISCOVERY_PHRASES: tuple[str, ...] = (
    # Algorithm / Recommendation
    "discover weekly",
    "daily mix",
    "for you",
    "algorithm",
    "recommend",
    "suggestion",
    "discover",
    "autoplay",
    "playlist",
    "curated",
    "radio",
    # Repetition / Loop
    "same songs",
    "keeps playing",
    "over and over",
    "again and again",
    "repeat",
    "boring",
    "stale",
    "stuck",
    "loop",
    # Discovery
    "new music",
    "new artist",
    "find music",
    "underground",
    "variety",
    "different",
    "explore",
    "diverse",
    "fresh",
    "indie",
    # Control / Transparency
    "don't understand",
    "doesn't know",
    "customize",
    "irrelevant",
    "preference",
    "how does",
    "control",
    "random",
    "why is",
    "taste",
    # Mood / Context
    "background",
    "workout",
    "driving",
    "energy",
    "focus",
    "party",
    "sleep",
    "study",
    "vibe",
    "mood",
)

VALID_SOURCES = frozenset({"app_store", "play_store", "reddit", "community_forum"})
