"""Configuration for Phase 5 MCP delivery."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"

PHASE4_DIR = PROJECT_ROOT.parent / "phase-4-reporting"
PHASE4_PULSE_PATH = PHASE4_DIR / "data" / "pulse_report.md"
PHASE4_RUN_LOG_PATH = PHASE4_DIR / "data" / "run_log.json"
PHASE4_ENV_PATH = PHASE4_DIR / ".env"

RUN_LOG_PATH = DATA_DIR / "run_log.json"
DELIVERY_REPORT_PATH = DATA_DIR / "phase5_delivery_report.json"


def load_env() -> None:
    """Load phase-specific env with phase-4 env fallback."""
    load_dotenv(PHASE4_ENV_PATH)
    load_dotenv()


def get_env(name: str, default: str = "") -> str:
    load_env()
    return os.getenv(name, default)

