"""Groq batch classifier with retry/backoff and token estimation."""

from __future__ import annotations

import json
import logging
import os
import re
import time
from dataclasses import asdict, dataclass, field
from typing import Any

from dotenv import load_dotenv
from groq import Groq, RateLimitError

from classification.config import (
    BATCH_DELAY_SECONDS,
    BATCH_SIZE,
    CLASSIFICATION_TEMPERATURE,
    GROQ_MODEL,
    INPUT_TOKENS_PER_REVIEW,
    MAX_RETRIES,
    OUTPUT_TOKENS_PER_REVIEW,
    SENTIMENTS,
    SYSTEM_PROMPT_EST_TOKENS,
    THEMES,
)
from classification.prompts import SYSTEM_PROMPT, build_user_prompt

logger = logging.getLogger("phase3.classifier")

VALID_THEMES = frozenset(THEMES)


@dataclass
class BatchPlan:
    total_reviews: int
    batch_size: int
    num_batches: int
    est_input_tokens: int
    est_output_tokens: int
    est_total_tokens: int
    est_cost_usd: float


@dataclass
class BatchLogEntry:
    batch_index: int
    review_count: int
    est_input_tokens: int
    est_output_tokens: int
    est_total_tokens: int
    actual_prompt_tokens: int | None = None
    actual_completion_tokens: int | None = None
    actual_total_tokens: int | None = None
    duration_seconds: float = 0.0
    retries: int = 0
    status: str = "pending"


@dataclass
class ClassificationRunStats:
    batches_sent: int = 0
    batches_failed: int = 0
    total_retries: int = 0
    est_total_tokens: int = 0
    actual_total_tokens: int = 0
    duration_seconds: float = 0.0
    batch_logs: list[BatchLogEntry] = field(default_factory=list)


def estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 characters per token for English."""
    return max(1, len(text) // 4)


def estimate_batch_tokens(batch: list[dict]) -> tuple[int, int, int]:
    user_prompt = build_user_prompt(batch)
    input_tokens = SYSTEM_PROMPT_EST_TOKENS + estimate_tokens(user_prompt)
    output_tokens = len(batch) * OUTPUT_TOKENS_PER_REVIEW
    return input_tokens, output_tokens, input_tokens + output_tokens


def plan_batches(reviews: list[dict], batch_size: int = BATCH_SIZE) -> BatchPlan:
    n = len(reviews)
    num_batches = (n + batch_size - 1) // batch_size if n else 0
    est_in = 0
    est_out = 0
    for i in range(0, n, batch_size):
        chunk = reviews[i : i + batch_size]
        batch_in, batch_out, _ = estimate_batch_tokens(chunk)
        est_in += batch_in
        est_out += batch_out
    est_total = est_in + est_out
    est_cost = (est_in * 0.59 + est_out * 0.79) / 1_000_000
    return BatchPlan(
        total_reviews=n,
        batch_size=batch_size,
        num_batches=num_batches,
        est_input_tokens=est_in,
        est_output_tokens=est_out,
        est_total_tokens=est_total,
        est_cost_usd=round(est_cost, 4),
    )


def split_batches(reviews: list[dict], batch_size: int = BATCH_SIZE) -> list[list[dict]]:
    return [reviews[i : i + batch_size] for i in range(0, len(reviews), batch_size)]


def _strip_json_fences(content: str) -> str:
    content = content.strip()
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", content, re.DOTALL | re.IGNORECASE)
    if fence:
        return fence.group(1).strip()
    return content


def parse_classification_response(content: str, batch: list[dict]) -> list[dict]:
    parsed = json.loads(_strip_json_fences(content))
    results = parsed.get("results", parsed) if isinstance(parsed, dict) else parsed
    if not isinstance(results, list):
        raise ValueError("Expected JSON array under 'results' key")

    if len(results) != len(batch):
        raise ValueError(f"Expected {len(batch)} results, got {len(results)}")

    validated: list[dict] = []
    for i, (raw_label, record) in enumerate(zip(results, batch)):
        theme = str(raw_label.get("theme", "")).strip()
        if theme not in VALID_THEMES:
            # Fuzzy match: find closest theme by prefix/substring
            matched = _fuzzy_theme(theme)
            if matched:
                theme = matched
            else:
                raise ValueError(f"Batch item {i}: invalid theme '{theme}'")

        confidence = float(raw_label.get("confidence", 0))
        confidence = max(0.0, min(1.0, confidence))

        sentiment = str(raw_label.get("sentiment", "neutral")).lower().strip()
        if sentiment not in SENTIMENTS:
            sentiment = "neutral"

        discovery_relevant = bool(raw_label.get("discovery_relevant", True))
        key_phrase = str(raw_label.get("key_phrase", "")).strip() or record.get("text", "")[:60]

        validated.append(
            {
                "theme": theme,
                "confidence": round(confidence, 3),
                "sentiment": sentiment,
                "discovery_relevant": discovery_relevant,
                "key_phrase": key_phrase,
            }
        )
    return validated


def _fuzzy_theme(theme: str) -> str | None:
    lower = theme.lower()
    for valid in THEMES:
        if valid.lower() == lower or valid.lower() in lower or lower in valid.lower():
            return valid
    aliases = {
        "recommendation": "Recommendation Quality",
        "discovery": "Discovery Friction",
        "friction": "Discovery Friction",
        "algorithm": "Algorithm Transparency",
        "transparency": "Algorithm Transparency",
        "playlist": "Playlist & Curation",
        "curation": "Playlist & Curation",
        "listening": "Listening Context",
        "context": "Listening Context",
        "mood": "Listening Context",
    }
    for key, value in aliases.items():
        if key in lower:
            return value
    return None


def _get_client() -> Groq:
    load_dotenv()
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key or api_key == "your_key_here":
        raise RuntimeError(
            "GROQ_API_KEY is not set. Add your key to .env (get one at console.groq.com)."
        )
    return Groq(api_key=api_key)


def classify_batch(
    client: Groq,
    batch: list[dict],
    *,
    batch_index: int = 0,
    stats: ClassificationRunStats | None = None,
) -> list[dict]:
    est_in, est_out, est_total = estimate_batch_tokens(batch)
    logger.info(
        "Batch %d: %d reviews | est tokens in=%d out=%d total=%d",
        batch_index,
        len(batch),
        est_in,
        est_out,
        est_total,
    )

    log_entry = BatchLogEntry(
        batch_index=batch_index,
        review_count=len(batch),
        est_input_tokens=est_in,
        est_output_tokens=est_out,
        est_total_tokens=est_total,
    )
    if stats:
        stats.est_total_tokens += est_total
        stats.batch_logs.append(log_entry)

    user_prompt = build_user_prompt(batch)
    delay = 1.0
    last_error: Exception | None = None

    for attempt in range(MAX_RETRIES):
        try:
            start = time.perf_counter()
            response = client.chat.completions.create(
                model=GROQ_MODEL,
                temperature=CLASSIFICATION_TEMPERATURE,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
            )
            elapsed = time.perf_counter() - start
            content = response.choices[0].message.content or ""
            labels = parse_classification_response(content, batch)

            usage = response.usage
            if usage:
                log_entry.actual_prompt_tokens = usage.prompt_tokens
                log_entry.actual_completion_tokens = usage.completion_tokens
                log_entry.actual_total_tokens = usage.total_tokens
                if stats:
                    stats.actual_total_tokens += usage.total_tokens or 0
                logger.info(
                    "Batch %d complete in %.1fs | actual tokens: %s",
                    batch_index,
                    elapsed,
                    usage.total_tokens,
                )

            log_entry.duration_seconds = elapsed
            log_entry.retries = attempt
            log_entry.status = "success"
            if stats:
                stats.batches_sent += 1
                stats.total_retries += attempt
            return labels

        except RateLimitError as exc:
            last_error = exc
            log_entry.retries = attempt + 1
            if stats:
                stats.total_retries += 1
            logger.warning(
                "Batch %d rate limited (429), retry %d/%d in %.1fs",
                batch_index,
                attempt + 1,
                MAX_RETRIES,
                delay,
            )
            time.sleep(delay)
            delay = min(delay * 2, 60.0)
        except (json.JSONDecodeError, ValueError, KeyError) as exc:
            last_error = exc
            logger.warning(
                "Batch %d parse error, retry %d/%d: %s",
                batch_index,
                attempt + 1,
                MAX_RETRIES,
                exc,
            )
            time.sleep(delay)
            delay = min(delay * 2, 30.0)
        except Exception as exc:
            last_error = exc
            logger.warning(
                "Batch %d API error, retry %d/%d: %s",
                batch_index,
                attempt + 1,
                MAX_RETRIES,
                exc,
            )
            time.sleep(delay)
            delay = min(delay * 2, 60.0)

    log_entry.status = "failed"
    if stats:
        stats.batches_failed += 1
    raise RuntimeError(f"Batch {batch_index} failed after {MAX_RETRIES} retries") from last_error


def merge_labels(batch: list[dict], labels: list[dict]) -> list[dict]:
    merged: list[dict] = []
    for record, label in zip(batch, labels):
        merged.append({**record, **label})
    return merged


def classify_all(
    reviews: list[dict],
    *,
    batch_size: int = BATCH_SIZE,
    write_output: bool = False,
) -> tuple[list[dict], ClassificationRunStats]:
    from classification.config import CLASSIFIED_REVIEWS_PATH, BATCH_LOG_PATH
    import json
    from pathlib import Path

    client = _get_client()
    stats = ClassificationRunStats()
    start = time.perf_counter()
    classified: list[dict] = []

    batches = split_batches(reviews, batch_size)
    for idx, batch in enumerate(batches):
        labels = classify_batch(client, batch, batch_index=idx + 1, stats=stats)
        classified.extend(merge_labels(batch, labels))
        if idx < len(batches) - 1 and BATCH_DELAY_SECONDS > 0:
            time.sleep(BATCH_DELAY_SECONDS)

    stats.duration_seconds = time.perf_counter() - start

    if write_output:
        out_path = CLASSIFIED_REVIEWS_PATH
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(classified, indent=2, ensure_ascii=False), encoding="utf-8")
        BATCH_LOG_PATH.write_text(
            json.dumps(
                {
                    "stats": {
                        "batches_sent": stats.batches_sent,
                        "batches_failed": stats.batches_failed,
                        "total_retries": stats.total_retries,
                        "est_total_tokens": stats.est_total_tokens,
                        "actual_total_tokens": stats.actual_total_tokens,
                        "duration_seconds": round(stats.duration_seconds, 2),
                    },
                    "batches": [asdict(b) for b in stats.batch_logs],
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    return classified, stats


def print_batch_plan(plan: BatchPlan) -> None:
    lines = [
        "",
        "=" * 58,
        "  PHASE 3 BATCH PLAN (proposed - not yet executed)",
        "=" * 58,
        f"  Total reviews:           {plan.total_reviews:>6}",
        f"  Batch size:              {plan.batch_size:>6}",
        f"  Number of API calls:     {plan.num_batches:>6}",
        f"  Est. input tokens:       {plan.est_input_tokens:>6,}",
        f"  Est. output tokens:      {plan.est_output_tokens:>6,}",
        f"  Est. total tokens:       {plan.est_total_tokens:>6,}",
        f"  Est. cost (USD):         ${plan.est_cost_usd:>.4f}",
        "=" * 58,
        "",
    ]
    print("\n".join(lines))
