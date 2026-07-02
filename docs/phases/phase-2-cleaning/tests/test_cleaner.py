"""Unit tests for Phase 2 cleaning."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

import pytest

from cleaning.config import MIN_WORD_COUNT
from cleaning.filters import (
    combined_review_text,
    is_discovery_relevant,
    is_empty_text,
    is_within_date_window,
    meets_min_word_count,
)
from cleaning.normalizer import (
    clean_text,
    make_record_id,
    normalize_date,
    strip_pii,
    word_count,
)
from cleaning.pipeline import phase_2_clean


class TestStripPii:
    def test_strips_email(self) -> None:
        assert "[REDACTED]" in strip_pii("Contact me at user@test.com please")

    def test_strips_handle(self) -> None:
        assert "[REDACTED]" in strip_pii("Follow @spotifyfan for updates")

    def test_strips_phone(self) -> None:
        assert "[REDACTED]" in strip_pii("Call 555-123-4567 anytime")

    def test_strips_url(self) -> None:
        assert "[REDACTED]" in strip_pii("See https://example.com/page for info")


class TestTextCleaning:
    def test_strips_emojis(self) -> None:
        cleaned = clean_text("Love this playlist 😂🔥 so good")
        assert "😂" not in cleaned
        assert "🔥" not in cleaned

    def test_normalizes_whitespace(self) -> None:
        assert clean_text("too   many    spaces") == "too many spaces"

    def test_keeps_allowed_punctuation(self) -> None:
        cleaned = clean_text("Great! Why is this? Don't know.")
        assert "!" in cleaned
        assert "?" in cleaned
        assert "'" in cleaned


class TestFilters:
    def test_empty_text(self) -> None:
        assert is_empty_text(None)
        assert is_empty_text("   ")
        assert not is_empty_text("hello world")

    def test_min_word_count(self) -> None:
        short = "one two three four five six seven"
        assert word_count(short) == 7
        assert not meets_min_word_count(short)
        long = short + " eight"
        assert meets_min_word_count(long)

    def test_date_window(self) -> None:
        now = datetime(2026, 6, 28, tzinfo=timezone.utc)
        recent = (now - timedelta(weeks=4)).isoformat()
        old = (now - timedelta(weeks=20)).isoformat()
        assert is_within_date_window(recent, reference=now)
        assert not is_within_date_window(old, reference=now)

    def test_discovery_relevant_playlist(self) -> None:
        assert is_discovery_relevant("The playlist recommendations are stale")

    def test_discovery_irrelevant(self) -> None:
        assert not is_discovery_relevant("The app crashes on startup every time")

    def test_combined_review_text(self) -> None:
        text = combined_review_text({"title": "Radio bug", "text": "Song radio repeats"})
        assert "Radio bug" in text
        assert "Song radio repeats" in text


class TestNormalizer:
    def test_stable_id_hash(self) -> None:
        a = make_record_id("app_store", "2026-01-01T00:00:00+00:00", "same text")
        b = make_record_id("app_store", "2026-01-01T00:00:00+00:00", "same text")
        assert a == b
        assert len(a) == 64

    def test_normalize_date_iso(self) -> None:
        assert normalize_date("2026-06-27T07:45:38-07:00").endswith("+00:00")


class TestPipeline:
  @pytest.fixture
  def sample_raw(self) -> list[dict]:
      now = datetime.now(timezone.utc)
      recent = (now - timedelta(weeks=2)).isoformat()
      return [
          {
              "source": "app_store",
              "date": recent,
              "rating": 4,
              "title": "Playlist issue",
              "text": "My discover weekly playlist keeps playing the same songs over and over again every week",
          },
          {
              "source": "play_store",
              "date": recent,
              "rating": 3,
              "title": "Duplicate",
              "text": "My discover weekly playlist keeps playing the same songs over and over again every week",
          },
          {
              "source": "reddit",
              "date": recent,
              "rating": None,
              "title": "Short",
              "text": "too short",
          },
          {
              "source": "app_store",
              "date": recent,
              "rating": 2,
              "title": "Crash",
              "text": "The application crashes immediately when I open it on my phone every single time",
          },
          {
              "source": "app_store",
              "date": (now - timedelta(weeks=20)).isoformat(),
              "rating": 1,
              "title": "Old",
              "text": "Old review about playlist recommendations being bad for discovery purposes",
          },
      ]

  def test_phase_2_clean_dedup_and_schema(self, sample_raw: list[dict]) -> None:
      clean, report = phase_2_clean(sample_raw, write_output=False)
      assert len(clean) == 1
      assert report.dropped_duplicate == 1
      assert report.dropped_min_words == 1
      assert report.dropped_not_discovery_relevant == 1
      assert report.dropped_outside_date_window == 1

      record = clean[0]
      assert record["discovery_relevant"] is True
      assert record["language"] == "en"
      assert record["word_count"] >= MIN_WORD_COUNT
      assert record["original_text"]
      assert "id" in record

  def test_pii_removed_from_output(self, sample_raw: list[dict]) -> None:
      now = datetime.now(timezone.utc)
      raw = [
          {
              "source": "reddit",
              "date": (now - timedelta(weeks=1)).isoformat(),
              "rating": None,
              "title": "Email",
              "text": "My daily mix playlist is boring contact me at fan@example.com for more info please thanks",
          }
      ]
      clean, _ = phase_2_clean(raw, write_output=False)
      blob = clean[0]["title"] + " " + clean[0]["text"]
      patterns = [
          re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),
          re.compile(r"@\w+"),
          re.compile(r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b"),
      ]
      for pattern in patterns:
          assert not pattern.search(blob)
