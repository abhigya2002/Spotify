# Phase 1 — Ingestion

Multi-source data ingestion for the Spotify Discovery Agent.

## Sources

| Source | Module | Details |
|--------|--------|---------|
| App Store | `ingestion/app_store.js` | Spotify app id `324684580` |
| Play Store | `ingestion/play_store.js` | `com.spotify.music` |
| Reddit | `ingestion/reddit.py` | [r/spotify](https://www.reddit.com/r/spotify/), [r/SpotifyPlaylists](https://www.reddit.com/r/SpotifyPlaylists/), [r/truespotify](https://www.reddit.com/r/truespotify/), [r/Music thread](https://www.reddit.com/r/Music/comments/1qyfi9g/why_does_music_sound_so_much_better_on_youtube/) |
| Community | `ingestion/community_forum.py` | [Song Radio echo chamber](https://community.spotify.com/t5/Live-Ideas/Spotify-amp-quot-Song-Radio-quot-is-Essentially-Just-an-Echo/idi-p/5170824), [Don't Like Button](https://community.spotify.com/t5/Implemented-Ideas/All-Platforms-quot-Don-t-Like-Button-quot-should-be-added-to-all/idi-p/4850114), [Podcasts split](https://community.spotify.com/t5/Live-Ideas/Podcasts-Split-out-podcasts-into-separate-app/idi-p/4938692), [World Map discovery](https://community.spotify.com/t5/Live-Ideas/World-Map-as-a-New-Way-to-Discover-Music/idi-p/7293225) |

## Setup

```bash
cd docs/phases/phase-1-ingestion
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
npm install
```

Optional: copy `.env.example` to `.env` and add Reddit API credentials (PRAW). Without credentials, Reddit public JSON API is used.

## Run

```bash
python main.py
python main.py --sources app_store,reddit,community_forum
```

Output: `data/raw_reviews.json`

## Validate

```bash
python scripts/validate_phase1.py
pytest tests/ -v
```

## Exit criteria

See [eval.md](./eval.md) — ≥200 records, ≥2 sources, ≥1 app store source.
