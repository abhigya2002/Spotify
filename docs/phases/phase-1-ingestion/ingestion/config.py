"""Shared configuration for Phase 1 ingestion."""

from __future__ import annotations

import os
from pathlib import Path

# Project root: docs/phases/phase-1-ingestion/
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
INGESTION_DIR = PROJECT_ROOT / "ingestion"

REVIEW_WINDOW_WEEKS = int(os.getenv("REVIEW_WINDOW_WEEKS", "12"))
MIN_REVIEW_COUNT = int(os.getenv("MIN_REVIEW_COUNT", "200"))

RAW_REVIEWS_PATH = DATA_DIR / "raw_reviews.json"

# Reddit sources (user-specified)
REDDIT_SUBREDDITS = [
    "spotify",
    "SpotifyPlaylists",
    "truespotify",
]

# Specific thread to include (r/Music discovery discussion)
REDDIT_THREAD_URLS = [
    "https://www.reddit.com/r/Music/comments/1qyfi9g/why_does_music_sound_so_much_better_on_youtube/",
]

# Spotify Community forum idea threads (user-specified)
COMMUNITY_FORUM_URLS = [
    "https://community.spotify.com/t5/Live-Ideas/Spotify-amp-quot-Song-Radio-quot-is-Essentially-Just-an-Echo/idi-p/5170824",
    "https://community.spotify.com/t5/Implemented-Ideas/All-Platforms-quot-Don-t-Like-Button-quot-should-be-added-to-all/idi-p/4850114",
    "https://community.spotify.com/t5/Live-Ideas/Podcasts-Split-out-podcasts-into-separate-app/idi-p/4938692",
    "https://community.spotify.com/t5/Live-Ideas/World-Map-as-a-New-Way-to-Discover-Music/idi-p/7293225",
]

REQUIRED_FIELDS = frozenset({"source", "date", "rating", "title", "text"})
