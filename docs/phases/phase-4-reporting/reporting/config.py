"""Configuration for Phase 4 reporting and delivery."""

from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
PHASE3_CLASSIFIED_PATH = (
    PROJECT_ROOT.parent / "phase-3-classification" / "data" / "classified_reviews.json"
)
PHASE3_ENV_PATH = PROJECT_ROOT.parent / "phase-3-classification" / ".env"
PULSE_REPORT_PATH = DATA_DIR / "pulse_report.md"
RUN_LOG_PATH = DATA_DIR / "run_log.json"

GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
PULSE_TEMPERATURE = float(os.getenv("PULSE_TEMPERATURE", "0.2"))
MAX_PULSE_WORDS = int(os.getenv("MAX_PULSE_WORDS", "250"))

MCP_SERVER_URL = os.getenv(
    "MCP_SERVER_URL",
    "https://saksham-mcp-server-production-4691.up.railway.app",
).rstrip("/")
GOOGLE_DOC_ID = os.getenv("GOOGLE_DOC_ID", "")
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL", "")

THEMES_ORDER = (
    "Discovery Friction",
    "Playlist & Curation",
    "Algorithm Transparency",
    "Listening Context",
    "Recommendation Quality",
)
