# Architecture — Spotify Discovery Agent

> **Project:** NextLeap PM Graduation Capstone (Part 1)  
> **Last updated:** June 2026  
> **Related:** [ProblemStatement.md](../ProblemStatement.md) · [implementation.md](./implementation.md) · [decision.md](./decision.md)

---

## 1. System Overview

The Spotify Discovery Agent is a **batch pipeline** that ingests public user feedback from multiple sources, classifies it with an LLM, generates a weekly PM-ready pulse note, and delivers it via **Google Workspace MCP tools** (Docs + Gmail draft).

It is designed as an **intelligence layer** for a four-part PM capstone. Part 1 automates signal collection and synthesis; Parts 2–4 consume its outputs for interviews, problem definition, and MVP build.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SPOTIFY DISCOVERY AGENT                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────┐   ┌──────────┐   ┌──────────────┐   ┌──────────┐   ┌───────┐ │
│  │ Phase 1  │──►│ Phase 2  │──►│   Phase 3    │──►│ Phase 4  │──►│Phase 5│ │
│  │ Ingestion│   │ Cleaning │   │Classification│   │ Reporting│   │  MCP  │ │
│  └────┬─────┘   └────┬─────┘   └──────┬───────┘   └────┬─────┘   └───┬───┘ │
│       │              │                │                │             │      │
│       ▼              ▼                ▼                ▼             ▼      │
│  raw_reviews   clean_reviews   classified_reviews  pulse_report   Doc+Draft │
│     .json          .json             .json            .md                   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
         │              │                │                │             │
         ▼              ▼                ▼                ▼             ▼
    App Store      PII strip         Groq API          Groq API      Google Workspace
    Play Store     Dedup             llama-3.3         Aggregation   MCP Server
    Reddit         Normalize         70b-versatile     Pulse gen     (Docs + Gmail)
    Forums
```

---

## 2. Architectural Principles

| Principle | Rationale |
|-----------|-----------|
| **Phase isolation** | Each phase reads/writes a single artifact file. Phases can be re-run independently for debugging. |
| **Artifact-first** | JSON/Markdown files on disk are the contract between phases — not in-memory-only state. |
| **MCP for delivery only** | Phases 1–4 use direct API/library calls. Phase 5 uses MCP — keeps Google OAuth out of pipeline code. |
| **No auth scraping** | Only public endpoints. Reddit uses official PRAW API with credentials. |
| **PII by design** | Stripped in Phase 2; re-validated in Phases 3–5 before any external delivery. |
| **PM-ready outputs** | Structured, quotable, archivable — feeds Parts 2–4 of the capstone. |

---

## 3. Component Architecture

### 3.1 Orchestrator (`main.py`)

Single entry point. Responsibilities:

- Load environment via `python-dotenv`
- Execute phases 1 → 5 sequentially
- Write/update `data/run_log.json` with timestamps, counts, Doc URL, errors
- Exit non-zero on phase failure (for CI/Railway health checks)

```python
# Pseudocode flow
run_log = init_run_log()
raw = phase_1_ingest()
clean = phase_2_clean(raw)
classified = phase_3_classify(clean)
pulse = phase_4_report(classified)
doc_url, draft_id = phase_5_deliver(pulse)
finalize_run_log(run_log, doc_url, draft_id)
```

### 3.2 Phase 1 — Ingestion (`ingestion/`)

| Module | Runtime | External Dependency |
|--------|---------|-------------------|
| `app_store.js` | Node.js | `app-store-scraper` — App ID `324684580` |
| `play_store.js` | Node.js | `google-play-scraper` — `com.spotify.music` |
| `reddit.py` | Python | PRAW — `r/spotify`, `r/SpotifyPlaylists`, `r/ifyoulikeblank` |
| `community_forum.py` | Python | `requests` + `BeautifulSoup` — public forum pages |

**Bridge pattern:** Node scrapers are invoked via `subprocess` from Python orchestrator; stdout returns JSON array.

### 3.3 Phase 2 — Cleaning (`ingestion/normalizer.py`)

- Date window filter (8–12 weeks, configurable via env)
- Schema normalization to canonical record shape
- PII stripping (regex + heuristics)
- Deduplication by hash of `(source, title, text)`

**Canonical record schema:**

```json
{
  "id": "sha256-hash",
  "source": "app_store | play_store | reddit | community_forum",
  "date": "ISO-8601",
  "rating": 4.0,
  "title": "string",
  "text": "string"
}
```

### 3.4 Phase 3 — Classification (`classification/`)

| Module | Responsibility |
|--------|----------------|
| `prompts.py` | System/user prompt templates, theme seeds, JSON schema instructions |
| `classifier.py` | Batch splitting (20–30 reviews), Groq API calls, response parsing, retry logic |

**Groq configuration:**

- Model: `llama-3.3-70b-versatile`
- Temperature: `0.1`
- Response format: structured JSON per review

**Enriched record schema (output):**

```json
{
  "...canonical fields...",
  "theme": "Discovery Friction",
  "confidence": 0.87,
  "discovery_relevant": true,
  "sentiment": "negative"
}
```

### 3.5 Phase 4 — Reporting (`reporting/`)

| Module | Responsibility |
|--------|----------------|
| `aggregator.py` | Theme counts, sentiment breakdown, quote shortlisting |
| `pulse_generator.py` | LLM call to produce ≤250-word pulse; enforce structure |

**Quote selection criteria:** high `confidence`, `discovery_relevant: true`, diverse themes/sources, verbatim text (PII already stripped).

### 3.6 Phase 5 — Delivery (`delivery/` + MCP)

```
┌─────────────────┐     MCP JSON-RPC      ┌──────────────────────────┐
│ mcp_delivery.py │ ◄──────────────────► │ Google Workspace MCP     │
│ gdocs_client.py │                       │ Server                   │
│ gmail_client.py │                       │  • docs_create           │
└─────────────────┘                       │  • docs_writeText        │
                                          │  • gmail_createDraft     │
                                          └──────────┬───────────────┘
                                                     │
                                          ┌──────────▼───────────────┐
                                          │ Google Cloud APIs          │
                                          │  • Docs API                │
                                          │  • Drive API               │
                                          │  • Gmail API (compose)     │
                                          └──────────────────────────┘
```

**Two invocation modes:**

1. **Development (Cursor):** Agent invokes MCP tools directly from `.cursor/mcp.json`
2. **Production (Railway):** `mcp_delivery.py` connects to co-hosted MCP server via stdio or HTTP transport

---

## 4. Data Flow & Artifacts

| Artifact | Producer | Consumer | Retention |
|----------|----------|----------|-----------|
| `data/raw_reviews.json` | Phase 1 | Phase 2 | Keep for audit |
| `data/clean_reviews.json` | Phase 2 | Phase 3 | Keep |
| `data/classified_reviews.json` | Phase 3 | Phase 4 | Keep — feeds Part 2 interviews |
| `data/pulse_report.md` | Phase 4 | Phase 5 | Keep — single source of truth for delivery |
| `data/run_log.json` | Orchestrator | Humans, Part 2 archive | Append per run |

**`run_log.json` entry shape:**

```json
{
  "run_id": "2026-06-15T10:00:00Z",
  "week_range": "9–15 June 2026",
  "review_counts": { "raw": 312, "clean": 287, "classified": 287, "relevant": 241 },
  "themes": ["Discovery Friction", "Recommendation Quality", "..."],
  "google_doc_url": "https://docs.google.com/document/d/...",
  "gmail_draft_id": "...",
  "status": "success",
  "duration_seconds": 142
}
```

---

## 5. External Dependencies

```
                    ┌─────────────┐
                    │  main.py    │
                    └──────┬──────┘
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
    ┌────────────┐  ┌───────────┐  ┌──────────────┐
    │ App/Play   │  │ Groq API  │  │ MCP Server   │
    │ Scrapers   │  │           │  │ (Google WS)  │
    └────────────┘  └───────────┘  └──────────────┘
           │               │               │
    ┌──────┴──────┐        │        ┌──────┴──────┐
    │ Reddit API  │        │        │ Google APIs │
    │ Forum HTTP  │        │        │ Docs/Gmail  │
    └─────────────┘        │        └─────────────┘
                           │
                    llama-3.3-70b-versatile
```

| Service | Auth | Rate Limits | Failure Mode |
|---------|------|-------------|--------------|
| Groq | API key | Per-tier TPM/RPM | Retry with backoff; fail phase |
| Reddit (PRAW) | OAuth app creds | 60 req/min | Retry; log partial results |
| App/Play scrapers | None (public) | Informal | Retry; continue with other sources |
| Community forum | None (public) | Respectful crawling | Skip on 4xx/5xx; log warning |
| Google (via MCP) | OAuth / service account | API quotas | Fail phase 5; pulse_report.md still valid |

---

## 6. Deployment Architecture (Railway)

```
┌─────────────────────────────────────────────────────────┐
│ Railway Project                                          │
│                                                          │
│  ┌─────────────────────┐    ┌─────────────────────────┐ │
│  │ discovery-pipeline  │    │ google-workspace-mcp    │ │
│  │ (Python + Node)     │───►│ (Node MCP server)       │ │
│  │                     │    │                         │ │
│  │ Cron: weekly        │    │ stdio / internal net    │ │
│  │ python main.py      │    │                         │ │
│  └─────────────────────┘    └─────────────────────────┘ │
│           │                            │                 │
│           ▼                            ▼                 │
│     Volume: /data              Google Cloud OAuth        │
│     (artifact persistence)     Docs + Gmail APIs         │
└─────────────────────────────────────────────────────────┘
```

**Secrets (Railway environment):**

- `GROQ_API_KEY`
- `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USER_AGENT`
- `GOOGLE_CREDENTIALS_JSON` (base64 or raw JSON string)
- `RECIPIENT_EMAIL`

---

## 7. Security Model

| Concern | Mitigation |
|---------|------------|
| Credential leakage | `.env` gitignored; Railway secrets; never log API keys |
| PII in outputs | Phase 2 strip + Phase 4/5 validation scan before delivery |
| Gmail auto-send | MCP uses `gmail_createDraft` only; `gmail.send` scope not requested |
| Scraping ethics | Public data only; rate-limited requests; no login bypass |
| MCP server exposure | Internal to Railway network or stdio — not public HTTP |

---

## 8. Capstone Integration (Parts 2–4)

| Part 1 Output | Used By | Purpose |
|---------------|---------|---------|
| `classified_reviews.json` | Part 2 | Interview guide themes, hypothesis list |
| `pulse_report.md` + Google Docs archive | Part 2, 3 | Evidence base for problem framing |
| Top 3 action ideas | Part 2, 4 | Features to validate / build |
| `run_log.json` | Part 3 | Trend over weekly runs (if re-run) |
| MCP server | Part 4 | Reuse for MVP notifications / agent tools |

---

## 9. Phase Evaluation Docs

Each pipeline phase has a dedicated evaluation file with tests and exit criteria:

| Phase | Eval Doc |
|-------|----------|
| 1 — Ingestion | [phases/phase-1-ingestion/eval.md](./phases/phase-1-ingestion/eval.md) |
| 2 — Cleaning | [phases/phase-2-cleaning/eval.md](./phases/phase-2-cleaning/eval.md) |
| 3 — Classification | [phases/phase-3-classification/eval.md](./phases/phase-3-classification/eval.md) |
| 4 — Reporting | [phases/phase-4-reporting/eval.md](./phases/phase-4-reporting/eval.md) |
| 5 — Delivery (MCP) | [phases/phase-5-delivery/eval.md](./phases/phase-5-delivery/eval.md) |

---

## 10. Directory Structure

```
spotify-discovery-agent/
├── docs/                          # This documentation set
│   ├── architecture.md
│   ├── implementation.md
│   ├── decision.md
│   └── phases/
│       └── phase-N-*/eval.md
├── ingestion/
├── classification/
├── reporting/
├── delivery/
├── mcp/
├── data/
├── tests/
├── main.py
├── Dockerfile
├── railway.toml
└── requirements.txt
```
