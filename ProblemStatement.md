PROJECT PROBLEM STATEMENT
AI-Powered Music Discovery Engine — Spotify
NextLeap PM Graduation Project  |  June 2026

0. Quick Reference
Product	Spotify
Course	NextLeap Product Management
Project Arc	4 parts — Discovery Agent → User Research → Problem Definition → AI-Native MVP
Current Phase	Part 1 — Review Discovery Agent (build now)
Final Deliverable (overall)	End-to-end PM workflow: automated signal → validated insight → scoped problem → shipped AI feature
Submission Deadline	10 days from project start (Part 1)
Primary Language	Python 3.11+
Deployment Target	Production (Railway or equivalent)
Key External APIs	Apple App Store (app-store-scraper), Google Play (google-play-scraper), Reddit (PRAW), Groq LLaMA-3.3-70b-versatile
Delivery Channels (Part 1)	Google Docs (structured report) + Gmail (weekly email digest) via MCP server
MCP Integration	Google Workspace MCP server — Docs creation/formatting + Gmail draft creation

1. Full Project Context (Parts 1–4)
This document is the master problem statement for the Spotify Music Discovery graduation capstone. It describes the **entire PM journey** and scopes **Part 1** in implementation detail. Parts 2–4 are defined here so every build decision in Part 1 serves the downstream deliverables.

1.1 Why This Project Exists
Spotify is the world's leading music streaming platform (600M+ MAU) with best-in-class algorithmic recommendations (Discover Weekly, Daily Mixes, Radio). Despite this, a substantial share of listening time is dominated by repeat playlists, familiar artists, and previously discovered tracks.

**The strategic gap:** Spotify has a discovery problem. Users are not meaningfully finding and engaging with new music — even though the product ostensibly exists to solve exactly this.

This capstone mirrors a real PM workflow: start from unstructured user feedback in the wild, synthesize it into actionable insight, validate with humans, define the problem rigorously, and ship a production-grade AI-native solution.

1.2 The Four-Part Journey
| Part | Name | Goal | Primary Output | Depends On |
|------|------|------|----------------|------------|
| **1** | AI-Powered Review Discovery Engine | Automate multi-source review ingestion, theme classification, and weekly pulse reporting | Discovery Agent (pipeline + Google Doc + Gmail draft) | — |
| **2** | User Research & Hypothesis Validation | Validate themes from Part 1 with 5–6 user interviews | Interview synthesis doc, validated/invalidated hypotheses | Part 1 themes & action ideas |
| **3** | Problem Definition | Root cause analysis, target segment, opportunity sizing, business case | Problem statement deck, opportunity matrix | Parts 1 + 2 |
| **4** | AI-Native MVP | Design and deploy a user-facing AI feature or agent that addresses the defined problem | Live MVP on Railway (or equivalent) | Parts 1–3 |

1.3 How Part 1 Feeds the Full Problem
Part 1 is not a standalone scraper — it is the **intelligence layer** that seeds every downstream part:

- **For Part 2 (Interviews):** Top themes, user quotes, and action ideas become interview guides and hypothesis checklists. The agent answers: *What should we ask users, and what do we already suspect?*
- **For Part 3 (Problem Definition):** Aggregated sentiment, segment signals (power users vs. casual listeners), and cross-platform patterns inform root-cause framing and opportunity sizing. The agent answers: *What is the real problem, for whom, and why does it matter commercially?*
- **For Part 4 (MVP):** Prioritized action ideas and unmet needs directly inform feature scope. The agent answers: *What should we build first?*

**Design implication:** Every artifact Part 1 produces (classified reviews, pulse note, Google Doc, Gmail draft) must be structured, quotable, and PM-ready — not raw data dumps.

1.4 Commercial Stakes (Across All Parts)
- **Discovery → Retention:** Users who discover new music they love show measurably higher retention and session length.
- **Discovery → Subscription Upgrades:** Premium features are easier to justify when users actively find value.
- **Discovery → Artist Ecosystem Health:** Spotify's long-term defensibility requires new artists to be discovered.
- **Signal Quality:** App reviews and community discussions are lagging but honest signals — unfiltered user voice that internal NPS surveys cannot capture.

---

2. Part 1 Scope — Review Discovery Agent
This section scopes the current build. Parts 2–4 will be executed after Part 1 is complete and reviewed, using Part 1 outputs as inputs.

2.1 Research Questions the Agent Must Answer
The Discovery Agent must surface answers to:
- Why do users struggle to discover new music despite algorithmic recommendations?
- What are the most common frustrations with current recommendation mechanics?
- What listening behaviors and goals are users trying to achieve but failing at?
- What triggers repetitive listening behavior — comfort, laziness, algorithm failure, or something else?
- Which user segments experience discovery challenges differently (power users vs. casual listeners, genre-specific users, mood-based listeners)?
- What unmet needs consistently emerge across platforms (App Store, Play Store, Reddit, forums)?

2.2 What You Are Building — Core Definition
The Discovery Agent is an end-to-end data pipeline that:
1. Ingests multi-source user feedback (App Store, Play Store, Reddit, community forums)
2. Classifies reviews into discovery-relevant themes using an LLM
3. Generates a structured, ≤250-word one-page weekly pulse note
4. Extracts top user quotes (verbatim, PII-stripped)
5. Proposes three prioritized action ideas
6. **Delivers the pulse note via Google Docs and Gmail using a Google Workspace MCP server**

2.3 System Constraints (Non-Negotiable)
| Constraint | Requirement |
|------------|-------------|
| Data Source | Public review exports only — NO scraping behind authentication walls |
| Review Window | Last 8–12 weeks of reviews |
| Theme Limit | Maximum 5 themes per run |
| Output Length | Weekly pulse note ≤ 250 words, scannable format |
| PII Policy | Zero PII in any artifact — strip usernames, emails, IDs before output |
| Delivery | Google Docs report + Gmail draft email via **MCP server** (not manual copy-paste) |
| Deployment | Production deployment required (Railway or equivalent) |
| LLM | Groq API with `llama-3.3-70b-versatile` model |

---

3. Data Sources & Ingestion Specification
3.1 Source Priority
Ingest from all sources below. Prioritize App Store + Play Store as primary signal; Reddit and forums as qualitative depth layer.

3.2 Source Details
| Source | Tool / Library | Spotify App ID / Endpoint | Fields to Capture |
|--------|----------------|---------------------------|-------------------|
| Apple App Store | app-store-scraper (npm) | id=324684580 | rating, title, text, date |
| Google Play Store | google-play-scraper (npm) | com.spotify.music | score, title, text, date |
| Reddit | PRAW (Python) | r/spotify, r/SpotifyPlaylists, r/ifyoulikeblank | title, selftext, score, created_utc |
| Community Forums | requests + BeautifulSoup (public pages only) | community.spotify.com (Ideas/Feature Requests) | post title, body, upvote count, date |

3.3 Ingestion Rules
- Filter to reviews/posts from the last 8–12 weeks based on date field
- Normalize schema across sources: `{ source, date, rating (null if not applicable), title, text }`
- Strip any PII from text field before storage: remove @mentions, email patterns, phone numbers, full names where detectable
- Minimum review count target: 200+ records for statistical theme validity
- Store raw + cleaned versions separately in the pipeline

---

4. Theme Classification Specification
4.1 Classification Goal
Group all ingested reviews into a maximum of 5 themes relevant to music discovery. The LLM classifier must not force reviews into irrelevant categories — unclassifiable reviews should be tagged as `Other` and excluded from the pulse.

4.2 Suggested Starting Themes (LLM may adapt)
The LLM should discover themes organically from the data. These are hypothesis seeds for the system prompt:
- **Recommendation Quality** — complaints or praise about Discover Weekly, Daily Mix, Radio, or autoplay accuracy
- **Discovery Friction** — difficulty finding new artists, genres, or moods; recommendation loops
- **Algorithm Transparency** — users not understanding why they see certain suggestions; lack of control
- **Playlist & Curation** — frustrations or wishes around editorial playlists, collaborative playlists, AI DJ
- **Listening Context** — mood-based, activity-based, or social discovery needs not being met

4.3 LLM Classification Prompt Design Requirements
- System prompt must instruct the model to: (a) classify each review into exactly one theme, (b) return structured JSON, (c) include a confidence score 0–1, (d) flag if the review is discovery-irrelevant
- Per-review output schema: `{ theme: string, confidence: float, discovery_relevant: bool, sentiment: 'positive' | 'neutral' | 'negative' }`
- Batch reviews in groups of 20–30 to stay within token limits
- Model: `groq/llama-3.3-70b-versatile`
- Temperature: 0.1 (low, for consistency)

---

5. Output Specification
5.1 Weekly Pulse Note — Content Structure
The pulse note must be ≤ 250 words, scannable, and contain exactly:
- **Header:** Product name + week range (e.g., `Spotify Discovery Pulse — 9–15 June 2026`)
- **Top 3 Themes:** Theme name + 1-sentence summary + review volume + sentiment breakdown
- **3 User Quotes:** Verbatim (PII-stripped), each labeled with source and rating if available
- **3 Action Ideas:** Short, prioritized, PM-style recommendations derived from themes
- **Footer:** Total reviews analyzed, date generated

5.2 Intermediate Artifact
Before delivery, the pipeline writes `data/pulse_report.md`. This file is the single source of truth passed to the MCP delivery layer. Retain this pattern — it decouples report generation from Google Workspace delivery and makes debugging easier.

---

6. MCP Server Integration — Google Docs & Gmail (Required)
Delivery in Part 1 **must** use a **Model Context Protocol (MCP) server** for Google Workspace integration. This is the same pattern used in the prior Groww capstone (`saksham-mcp-server`). Do not implement raw Google API calls in the pipeline unless the MCP server is unavailable — MCP is the primary delivery path.

6.1 Why MCP for Delivery
| Benefit | Description |
|---------|-------------|
| Agent-native | Cursor (and the deployed orchestrator) invoke Docs/Gmail as tools — no bespoke OAuth flow in application code |
| Separation of concerns | Pipeline phases 1–4 produce `pulse_report.md`; Phase 5 is a thin MCP delivery layer |
| Reusable | Same MCP server serves Part 1 weekly runs and can support Part 4 MVP notifications |
| Auditable | Draft-only Gmail policy is enforced at the tool level (`gmail_createDraft`, not `gmail_send`) |

6.2 MCP Server Setup
**Option A — Prior project pattern (recommended):** Reuse or fork the `saksham-mcp-server` used in the Groww build. Host on Railway alongside the pipeline.

**Option B — Community MCP server:** Use a Google Workspace MCP server (e.g., `google-workplace-mcp`, `google-mcp`) with equivalent Docs + Gmail tools.

**Cursor configuration** — add to `.cursor/mcp.json` (project-level) or `~/.cursor/mcp.json` (global):

```json
{
  "mcpServers": {
    "google-workspace": {
      "command": "node",
      "args": ["/path/to/mcp-server/dist/index.js"],
      "env": {
        "GOOGLE_CREDENTIALS_PATH": "/path/to/credentials.json",
        "RECIPIENT_EMAIL": "your-alias@example.com"
      }
    }
  }
}
```

6.3 Google Cloud Prerequisites
1. Create a Google Cloud project (or reuse an existing one)
2. Enable APIs: **Gmail API**, **Google Docs API**, **Google Drive API** (Docs are stored in Drive)
3. Configure OAuth consent screen (External or Internal, depending on workspace)
4. Create OAuth 2.0 credentials (Desktop app) or a service account with domain-wide delegation
5. Required OAuth scopes:
   - `https://www.googleapis.com/auth/documents`
   - `https://www.googleapis.com/auth/drive.file`
   - `https://www.googleapis.com/auth/gmail.compose` (draft creation only — do not request `gmail.send`)
6. Store credentials in `.env` / secure secret store — never commit to git

6.4 MCP Tools Used in Phase 5 (Delivery)
| Service | MCP Tool | Purpose |
|---------|----------|---------|
| Google Docs | `docs_create` | Create new document titled `Spotify Discovery Pulse — [Week Range]` |
| Google Docs | `docs_writeText` / `docs_append_text` / `docs_formatText` | Write pulse content with H1/H2 heading structure |
| Google Docs | `docs_getText` (optional) | Verify document content after write |
| Gmail | `gmail_createDraft` | Create draft email — **never auto-send** |
| Gmail | `gmail_listLabels` (optional) | Confirm draft landed in Drafts folder |

6.5 Google Docs Delivery Specification
- Create a **new document per run** (do not overwrite prior weeks — Part 2 needs a historical archive)
- Document title: `Spotify Discovery Pulse — [Week Range]`
- Apply structured formatting:
  - H1: Document title
  - H2: `Top Themes`, `User Quotes`, `Action Ideas`, `Run Metadata`
  - Body: Scannable bullet lists under each section
- Persist the document URL in the run log (`data/run_log.json` or equivalent)
- Share document with project owner (view access) if using service account

6.6 Gmail Delivery Specification
- Use `gmail_createDraft` only — **do NOT auto-send**
- **To:** configured `RECIPIENT_EMAIL` (your own alias or PM reviewer)
- **Subject:** `Spotify Discovery Pulse — Week of [Date]`
- **Body:** Pulse note content (plain text or minimal HTML) + clickable Google Doc link
- Verify draft exists in Gmail Drafts folder before marking run complete

6.7 Delivery Flow (Phase 5)
```
pulse_report.md
       │
       ▼
┌──────────────────────────────────────┐
│  delivery/mcp_delivery.py            │
│  (or Cursor agent invoking MCP tools)│
└──────────────────────────────────────┘
       │
       ├──► MCP: docs_create + docs_writeText  →  Google Doc URL
       │
       └──► MCP: gmail_createDraft (with Doc link)  →  Gmail Draft
```

6.8 Environment Variables (MCP + Google)
| Variable | Purpose |
|----------|---------|
| `GOOGLE_CREDENTIALS_PATH` or `GOOGLE_CREDENTIALS_JSON` | OAuth client secret or service account JSON |
| `GOOGLE_CLIENT_ID` | OAuth client ID (if not using JSON path) |
| `GOOGLE_CLIENT_SECRET` | OAuth client secret |
| `RECIPIENT_EMAIL` | Gmail draft recipient |
| `MCP_SERVER_COMMAND` | Optional — command to spawn MCP server in production |

---

7. System Architecture
7.1 Pipeline Phases
| Phase | Name | Responsibility | Output |
|-------|------|----------------|--------|
| 1 | Ingestion | Fetch reviews from App Store, Play Store, Reddit, Community Forums | `raw_reviews.json` |
| 2 | Cleaning & Normalization | Strip PII, deduplicate, normalize schema, filter by date window | `clean_reviews.json` |
| 3 | LLM Classification | Batch classify reviews into ≤5 themes via Groq API; sentiment tagging | `classified_reviews.json` |
| 4 | Pulse Report Generation | Aggregate themes, select quotes, generate action ideas via LLM | `pulse_report.md` |
| 5 | Delivery (MCP) | Post pulse to Google Docs and draft Gmail via MCP server | Google Doc URL + Gmail Draft |

7.2 Recommended Project Structure
```
spotify-discovery-agent/
├── ingestion/
│   ├── app_store.js          # app-store-scraper wrapper
│   ├── play_store.js         # google-play-scraper wrapper
│   ├── reddit.py             # PRAW-based Reddit fetcher
│   ├── community_forum.py    # BeautifulSoup community.spotify.com
│   └── normalizer.py         # Schema normalization + PII stripping
├── classification/
│   ├── classifier.py         # Groq API batching + classification logic
│   └── prompts.py            # System + user prompt templates
├── reporting/
│   ├── aggregator.py         # Theme aggregation + quote selection
│   └── pulse_generator.py    # LLM-generated pulse note
├── delivery/
│   ├── mcp_delivery.py       # Orchestrates Docs + Gmail via MCP tools
│   ├── gdocs_client.py       # MCP wrapper for Google Docs operations
│   └── gmail_client.py       # MCP wrapper for Gmail draft creation
├── mcp/                        # MCP server config (if self-hosted)
│   └── mcp.json                # Cursor / Railway MCP server definition
├── data/
│   ├── raw_reviews.json
│   ├── clean_reviews.json
│   ├── classified_reviews.json
│   ├── pulse_report.md
│   └── run_log.json            # Doc URLs, run timestamps, review counts
├── tests/
├── .env                        # GROQ_API_KEY, REDDIT_*, GOOGLE_*, RECIPIENT_EMAIL
├── main.py                     # Orchestrator — runs full pipeline end-to-end
├── Dockerfile
├── railway.toml
├── requirements.txt
└── README.md
```

7.3 Environment Variables (Full List)
- `GROQ_API_KEY` — from console.groq.com
- `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USER_AGENT` — from apps.reddit.com
- `GOOGLE_CREDENTIALS_PATH` or `GOOGLE_CREDENTIALS_JSON` — Google OAuth / service account
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` — if using env-based OAuth
- `RECIPIENT_EMAIL` — Gmail draft recipient

---

8. Acceptance Criteria (Definition of Done — Part 1)
The agent is considered complete when **all** of the following pass:

| # | Criterion | How to Verify |
|---|-----------|---------------|
| 1 | Ingestion: ≥ 200 reviews from at least 2 sources within the 8–12 week window | `print(len(reviews))` and assert date range |
| 2 | Cleaning: 0 PII strings (email/phone/@handle patterns) in `clean_reviews.json` | PII regex scan on cleaned file |
| 3 | Classification: All reviews assigned a theme; ≤ 5 unique themes in output | `assert len(set(themes)) <= 5` |
| 4 | Pulse Note: Word count ≤ 250; contains 3 themes, 3 quotes, 3 action ideas | Word count check + structural parse |
| 5 | Google Doc (via MCP): New Doc created with correct title, H1/H2 formatting, and full pulse content | Open Doc link from `run_log.json` |
| 6 | Gmail Draft (via MCP): Draft exists with correct subject, body, and Doc link | Check Gmail Drafts folder |
| 7 | Pipeline: `main.py` runs end-to-end from cold start with only `.env` configured | Clone repo, set `.env`, run `python main.py` |
| 8 | Deployment: Agent runs successfully on Railway (or equivalent) | Trigger from Railway dashboard or cron/webhook |
| 9 | MCP integration: Delivery phase invokes MCP tools (not hardcoded API bypass) | Inspect `delivery/` logs or MCP server request log |

---

9. Downstream Parts — Preview (Out of Build Scope for Now)
These are **not** Part 1 deliverables but provide context for why Part 1 artifacts must be PM-ready.

**Part 2 — User Research (5–6 interviews)**
- Use Part 1 themes as interview guide structure
- Validate or invalidate the 3 action ideas from the pulse note
- Output: interview synthesis with evidence-backed hypothesis status

**Part 3 — Problem Definition**
- Root cause analysis grounded in Part 1 quantitative themes + Part 2 qualitative depth
- Target segment definition, opportunity sizing, business case
- Output: problem statement deck with clear "who, what, why now"

**Part 4 — AI-Native MVP**
- Build and deploy a user-facing AI feature addressing the Part 3 problem
- May reuse MCP server for notifications, user feedback loops, or agent tooling
- Output: live MVP on Railway with README and demo script

---

10. Explicit Out of Scope (Part 1)
- User interviews or primary research (Part 2)
- Problem definition framework or opportunity sizing (Part 3)
- MVP feature design or user-facing product (Part 4)
- Any authenticated scraping (behind login walls)
- Real-time streaming ingestion — batch weekly runs are sufficient
- Social media platforms (Twitter/X, TikTok) — Reddit and forums cover social signal
- Multi-language review processing — English only for this build
- **Auto-sending emails** — Gmail drafts only via MCP

---

11. Reference: Prior Project (Groww)
A similar pipeline was built for Groww (India's leading investment platform). Key learnings that apply directly to Spotify:

| Learning | Application to Spotify |
|----------|------------------------|
| `google-play-scraper` and `app-store-scraper` (npm) are reliable for public review ingestion | Use the same tooling for App Store + Play Store |
| Groq `llama-3.3-70b-versatile` performed well for theme classification at batch sizes of 20–30 | Same model and batch size |
| Railway is the preferred deployment target for MCP server hosting | Host pipeline + MCP server on Railway |
| **MCP server pattern (`saksham-mcp-server`) enabled clean Google Docs + Gmail wiring in Phase 4** | **Replicate this pattern — MCP is required for Part 1 delivery** |
| `pulse_report.md` as intermediate artifact before Docs/Gmail delivery | Retain this decoupling pattern |
| 276 reviews processed through Phases 1–3 successfully | Spotify should target similar or higher volume |

---

12. Instructions for Cursor (AI Implementation Agent)
When Cursor reads this document, it should:

1. **Understand the full arc** — Part 1 outputs feed Parts 2–4; structure all artifacts accordingly
2. **Create the directory structure** as specified in Section 7.2, including `delivery/` and `mcp/` folders
3. **Implement phases sequentially** (1 → 2 → 3 → 4 → 5) with tests after each
4. **Configure the Google Workspace MCP server** before implementing Phase 5 — verify `docs_create` and `gmail_createDraft` tools are available in Cursor
5. Use Python for the core pipeline; Node.js only for app store scrapers if needed
6. All secrets via `.env` + `python-dotenv` — never hardcode credentials
7. Include `Dockerfile` + `railway.toml` for deployment (pipeline and MCP server if self-hosted)
8. Write `README.md` with: setup instructions, env var list, MCP server setup steps, and how to run end-to-end
9. Validate all acceptance criteria in Section 8 before marking Part 1 complete
10. Ask for clarification if any data source returns < 50 reviews (may require date window expansion)
