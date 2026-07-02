"""Configuration for Phase 3 LLM classification."""

from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
PHASE2_CLEAN_PATH = PROJECT_ROOT.parent / "phase-2-cleaning" / "data" / "clean_reviews.json"
CLASSIFIED_REVIEWS_PATH = DATA_DIR / "classified_reviews.json"
CLASSIFICATION_REPORT_PATH = DATA_DIR / "phase3_classification_report.json"
BATCH_LOG_PATH = DATA_DIR / "phase3_batch_log.json"

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "20"))
MAX_REVIEW_CHARS = int(os.getenv("MAX_REVIEW_CHARS", "500"))
CLASSIFICATION_TEMPERATURE = float(os.getenv("CLASSIFICATION_TEMPERATURE", "0.1"))
BATCH_DELAY_SECONDS = float(os.getenv("BATCH_DELAY_SECONDS", "2"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "5"))

# Groq llama-3.3-70b-versatile limits (for batch planning)
CONTEXT_WINDOW_TOKENS = 131_072
MAX_COMPLETION_TOKENS = 32_768
RATE_LIMIT_TPM = 300_000
RATE_LIMIT_RPM = 1_000

THEMES: tuple[str, ...] = (
    "Recommendation Quality",
    "Discovery Friction",
    "Algorithm Transparency",
    "Playlist & Curation",
    "Listening Context",
)

SENTIMENTS: frozenset[str] = frozenset({"positive", "neutral", "negative"})

# Token estimation heuristics (chars / 4 ≈ tokens for English)
SYSTEM_PROMPT_EST_TOKENS = 550
OUTPUT_TOKENS_PER_REVIEW = 90
INPUT_TOKENS_PER_REVIEW = 85  # title + truncated text in JSON
