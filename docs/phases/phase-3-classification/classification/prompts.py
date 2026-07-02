"""Prompt templates for Groq classification."""

from __future__ import annotations

import json

from classification.config import MAX_REVIEW_CHARS, THEMES

SYSTEM_PROMPT = f"""You are a product analyst for Spotify music discovery.
Classify each user review into exactly ONE of these themes:

1. Recommendation Quality — accuracy of Discover Weekly, Daily Mix, Radio, autoplay, and "For You" suggestions
2. Discovery Friction — difficulty finding new artists, genres, or moods; repetitive loops; stale recommendations
3. Algorithm Transparency — lack of control, not understanding why suggestions appear, random or irrelevant picks
4. Playlist & Curation — editorial playlists, AI DJ, collaborative playlists, playlist management
5. Listening Context — mood, activity (workout, study, sleep, driving), social discovery, vibe/energy needs unmet

Rules:
- Return a JSON object with key "results": an array with one object per input review, in the SAME ORDER as the input.
- Each result object must have: id, theme, confidence, sentiment, discovery_relevant, key_phrase
- theme must be exactly one of: {", ".join(f'"{t}"' for t in THEMES)}
- confidence: float from 0.0 to 1.0
- sentiment: exactly "positive", "neutral", or "negative"
- discovery_relevant: true if the review is genuinely about music discovery; false if off-topic (bugs, billing, UI, etc.)
- key_phrase: one short phrase (3-8 words) from the review that best captures the core issue or praise
- Do not include markdown fences or commentary — JSON only.
"""


def build_user_prompt(batch: list[dict]) -> str:
    payload = [
        {
            "id": r["id"],
            "source": r.get("source"),
            "rating": r.get("rating"),
            "title": (r.get("title") or "")[:200],
            "text": (r.get("text") or "")[:MAX_REVIEW_CHARS],
        }
        for r in batch
    ]
    return json.dumps({"reviews": payload}, ensure_ascii=False)
