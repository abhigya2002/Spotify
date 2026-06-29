"""Unit tests for Phase 1 ingestion."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from ingestion.community_forum import _parse_forum_date, _to_record as forum_to_record
from ingestion.config import COMMUNITY_FORUM_URLS, REDDIT_SUBREDDITS, REDDIT_THREAD_URLS
from ingestion.reddit import fetch_reddit


REQUIRED_FIELDS = {"source", "date", "rating", "title", "text"}


class TestConfig:
    def test_reddit_subreddits(self):
        assert "spotify" in REDDIT_SUBREDDITS
        assert "SpotifyPlaylists" in REDDIT_SUBREDDITS
        assert "truespotify" in REDDIT_SUBREDDITS

    def test_reddit_thread_urls(self):
        assert any("r/Music" in u for u in REDDIT_THREAD_URLS)

    def test_community_forum_urls(self):
        assert len(COMMUNITY_FORUM_URLS) == 4
        assert all("community.spotify.com" in u for u in COMMUNITY_FORUM_URLS)


class TestForumHelpers:
    def test_parse_forum_date(self):
        result = _parse_forum_date("2021-03-18 04:01 PM")
        assert "2021-03-18" in result

    def test_forum_record_schema(self):
        record = forum_to_record(
            title="Song Radio echo chamber",
            text="Radio plays same songs",
            date_str="2021-03-18 04:01 PM",
            likes=3396,
            thread_url="https://community.spotify.com/t5/Live-Ideas/test/idi-p/5170824",
        )
        assert record["source"] == "community_forum"
        assert record["rating"] == 3396


class TestRedditFetch:
    @patch("ingestion.reddit.time.sleep", return_value=None)
    @patch("ingestion.reddit.requests.get")
    def test_fetch_reddit(self, mock_get, mock_sleep):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": {
                "children": [
                    {
                        "data": {
                            "title": "Mock Post Title",
                            "selftext": "Mock post text body.",
                            "created_utc": 1600000000.0,
                            "score": 123,
                            "subreddit": "spotify",
                        }
                    }
                ]
            }
        }
        mock_get.return_value = mock_response

        # Execute
        records = fetch_reddit()

        # We have 4 subreddits and 2 sorts (hot/top) each, so 8 requests.
        assert mock_get.call_count == 8
        assert mock_sleep.call_count == 8

        # Verify output list
        assert len(records) == 8
        first = records[0]
        assert first["source"] == "reddit"
        assert first["rating"] is None
        assert first["title"] == "Mock Post Title"
        assert first["text"] == "Mock post text body."
        assert first["score"] == 123
        assert first["subreddit"] == "spotify"
        assert "date" in first


class TestCommunityForum:
    @patch("ingestion.community_forum.requests.get")
    def test_handles_http_error_gracefully(self, mock_get):
        from ingestion.community_forum import fetch_community_forum

        mock_get.side_effect = Exception("connection error")
        records = fetch_community_forum(urls=["https://community.spotify.com/t5/test"])
        assert records == []


class TestMainMerge:
    @patch("ingestion.store_scrapers.fetch_play_store")
    @patch("ingestion.store_scrapers.fetch_app_store")
    @patch("ingestion.reddit.fetch_reddit")
    @patch("ingestion.community_forum.fetch_community_forum")
    def test_phase_1_merges_all_sources(
        self, mock_forum, mock_reddit, mock_app, mock_play, tmp_path, monkeypatch
    ):
        import ingestion.config as cfg

        monkeypatch.setattr(cfg, "DATA_DIR", tmp_path)
        monkeypatch.setattr(cfg, "RAW_REVIEWS_PATH", tmp_path / "raw_reviews.json")

        sample = {
            "source": "app_store",
            "date": "2026-01-01T00:00:00+00:00",
            "rating": 5,
            "title": "t",
            "text": "x",
        }
        mock_app.return_value = [sample] * 50
        mock_play.return_value = [{**sample, "source": "play_store"}] * 50
        mock_reddit.return_value = [{**sample, "source": "reddit", "rating": None}] * 50
        mock_forum.return_value = [{**sample, "source": "community_forum"}] * 50

        from main import phase_1_ingest

        result = phase_1_ingest()
        assert len(result) == 200
        assert (tmp_path / "raw_reviews.json").exists()
        loaded = json.loads((tmp_path / "raw_reviews.json").read_text())
        sources = {r["source"] for r in loaded}
        assert len(sources) == 4
