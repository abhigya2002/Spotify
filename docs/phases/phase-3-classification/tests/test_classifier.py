"""Unit tests for Phase 3 classification (no live API calls)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from groq import RateLimitError

from classification.classifier import (
    classify_batch,
    merge_labels,
    parse_classification_response,
    plan_batches,
    split_batches,
)
from classification.config import THEMES
from classification.prompts import SYSTEM_PROMPT, build_user_prompt
from classification.report import build_classification_report


SAMPLE_BATCH = [
    {
        "id": "aaa",
        "source": "app_store",
        "rating": 2,
        "title": "Radio repeats",
        "text": "Song radio keeps playing the same tracks over and over",
    },
    {
        "id": "bbb",
        "source": "reddit",
        "rating": None,
        "title": "Discover weekly",
        "text": "My discover weekly playlist feels stale and boring lately",
    },
]


def _mock_response(content: str) -> MagicMock:
    mock = MagicMock()
    mock.choices = [MagicMock(message=MagicMock(content=content))]
    mock.usage = MagicMock(prompt_tokens=500, completion_tokens=200, total_tokens=700)
    return mock


class TestPrompts:
    def test_system_prompt_has_json_schema(self) -> None:
        assert "confidence" in SYSTEM_PROMPT
        assert "discovery_relevant" in SYSTEM_PROMPT
        assert "key_phrase" in SYSTEM_PROMPT
        for theme in THEMES:
            assert theme in SYSTEM_PROMPT

    def test_user_prompt_is_json(self) -> None:
        payload = json.loads(build_user_prompt(SAMPLE_BATCH))
        assert len(payload["reviews"]) == 2
        assert payload["reviews"][0]["id"] == "aaa"


class TestBatching:
    def test_split_batches(self) -> None:
        reviews = [{"id": str(i)} for i in range(55)]
        batches = split_batches(reviews, batch_size=25)
        assert len(batches) == 3
        assert len(batches[0]) == 25
        assert len(batches[2]) == 5

    def test_plan_batches_410(self) -> None:
        reviews = [{"id": str(i), "title": "t", "text": "word " * 40} for i in range(410)]
        plan = plan_batches(reviews, batch_size=20)
        assert plan.total_reviews == 410
        assert plan.num_batches == 21
        assert plan.est_total_tokens < 131_072  # well under context window
        assert plan.est_total_tokens < 300_000  # under TPM if sent in one minute


class TestParseResponse:
    def test_parse_valid_json(self) -> None:
        content = json.dumps(
            {
                "results": [
                    {
                        "id": "aaa",
                        "theme": "Discovery Friction",
                        "confidence": 0.92,
                        "sentiment": "negative",
                        "discovery_relevant": True,
                        "key_phrase": "same tracks over and over",
                    },
                    {
                        "id": "bbb",
                        "theme": "Recommendation Quality",
                        "confidence": 0.85,
                        "sentiment": "negative",
                        "discovery_relevant": True,
                        "key_phrase": "discover weekly feels stale",
                    },
                ]
            }
        )
        labels = parse_classification_response(content, SAMPLE_BATCH)
        assert len(labels) == 2
        assert labels[0]["theme"] == "Discovery Friction"
        assert labels[0]["confidence"] == 0.92

    def test_parse_markdown_fences(self) -> None:
        inner = json.dumps(
            {
                "results": [
                    {
                        "theme": "Listening Context",
                        "confidence": 0.7,
                        "sentiment": "neutral",
                        "discovery_relevant": True,
                        "key_phrase": "sleep playlist",
                    }
                ]
            }
        )
        content = f"```json\n{inner}\n```"
        batch = [SAMPLE_BATCH[0]]
        labels = parse_classification_response(content, batch)
        assert labels[0]["theme"] == "Listening Context"

    def test_merge_labels(self) -> None:
        labels = [
            {
                "theme": "Discovery Friction",
                "confidence": 0.9,
                "sentiment": "negative",
                "discovery_relevant": True,
                "key_phrase": "repeat loop",
            }
        ]
        merged = merge_labels([SAMPLE_BATCH[0]], labels)
        assert merged[0]["id"] == "aaa"
        assert merged[0]["theme"] == "Discovery Friction"


class TestRetry:
    def test_retry_on_rate_limit(self) -> None:
        client = MagicMock()
        good = _mock_response(
            json.dumps(
                {
                    "results": [
                        {
                            "theme": "Discovery Friction",
                            "confidence": 0.8,
                            "sentiment": "negative",
                            "discovery_relevant": True,
                            "key_phrase": "same songs",
                        }
                    ]
                }
            )
        )
        client.chat.completions.create.side_effect = [
            RateLimitError("rate limit", response=MagicMock(status_code=429), body=None),
            good,
        ]
        with patch("classification.classifier.time.sleep"):
            labels = classify_batch(client, [SAMPLE_BATCH[0]], batch_index=1)
        assert labels[0]["theme"] == "Discovery Friction"
        assert client.chat.completions.create.call_count == 2


class TestReport:
    def test_build_report(self) -> None:
        classified = [
            {
                "id": "1",
                "source": "app_store",
                "rating": 1,
                "text": "discover weekly is bad",
                "theme": "Recommendation Quality",
                "confidence": 0.95,
                "sentiment": "negative",
                "discovery_relevant": True,
                "key_phrase": "discover weekly is bad",
            },
            {
                "id": "2",
                "source": "play_store",
                "rating": 2,
                "text": "same songs repeat",
                "theme": "Discovery Friction",
                "confidence": 0.88,
                "sentiment": "negative",
                "discovery_relevant": True,
                "key_phrase": "same songs repeat",
            },
        ]
        report = build_classification_report(classified)
        assert report["total_classified"] == 2
        assert report["themes"]["Recommendation Quality"]["count"] == 1
        assert len(report["themes"]["Recommendation Quality"]["top_quotes"]) == 1
