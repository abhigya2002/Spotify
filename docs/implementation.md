# Implementation Guide — Spotify Discovery Agent with MCP

> **Audience:** Developers and Cursor AI agent implementing Part 1  
> **Prerequisite:** Read [ProblemStatement.md](../ProblemStatement.md) and [architecture.md](./architecture.md)  
> **Decision log:** [decision.md](./decision.md)

---

## 1. Implementation Order

Build phases **sequentially**. Do not start Phase N+1 until Phase N passes its [eval.md](./phases/) exit criteria.

```
Setup → Phase 1 → Phase 2 → Phase 3 → Phase 4 → MCP Setup → Phase 5 → Deploy
```

| Step | Deliverable | Eval Doc |
|------|-------------|----------|
| 0. Project setup | Repo skeleton, `.env.example`, dependencies | — |
| 1. Ingestion | `raw_reviews.json` from ≥2 sources | [phase-1-ingestion/eval.md](./phases/phase-1-ingestion/eval.md) |
| 2. Cleaning | `clean_reviews.json`, zero PII | [phase-2-cleaning/eval.md](./phases/phase-2-cleaning/eval.md) |
| 3. Classification | `classified_reviews.json`, ≤5 themes | [phase-3-classification/eval.md](./phases/phase-3-classification/eval.md) |
| 4. Reporting | `pulse_report.md`, ≤250 words | [phase-4-reporting/eval.md](./phases/phase-4-reporting/eval.md) |
| 5. MCP + Delivery | Google Doc + Gmail draft | [phase-5-delivery/eval.md](./phases/phase-5-delivery/eval.md) |
| 6. Deploy | Railway cron run succeeds | All evals + Part 1 acceptance |

---

## 2. Step 0 — Project Setup

### 2.1 Initialize repository

```bash
mkdir -p spotify-discovery-agent/{ingestion,classification,reporting,delivery,mcp,data,tests,docs}
cd spotify-discovery-agent
python -m venv .venv
# Windows: .venv\Scripts\activate
# Unix: source .venv/bin/activate
pip install -r requirements.txt
npm init -y && npm install app-store-scraper google-play-scraper
```

### 2.2 `requirements.txt` (baseline)

```
python-dotenv>=1.0.0
praw>=7.7.0
requests>=2.31.0
beautifulsoup4>=4.12.0
groq>=0.9.0
pytest>=8.0.0
```

### 2.3 `.env.example`

```env
# Groq
GROQ_API_KEY=

# Reddit
REDDIT_CLIENT_ID=
REDDIT_CLIENT_SECRET=
REDDIT_USER_AGENT=spotify-discovery-agent/1.0

# Google (MCP)
GOOGLE_CREDENTIALS_PATH=
RECIPIENT_EMAIL=

# Pipeline config
REVIEW_WINDOW_WEEKS=10
MIN_REVIEW_COUNT=200
```

### 2.4 Create `main.py` stub

Implement phase functions as stubs first; flesh out as each phase is completed.

---

## 3. Phase 1 — Ingestion

### 3.1 App Store (`ingestion/app_store.js`)

```javascript
const store = require('app-store-scraper');

async function fetchReviews() {
  const reviews = await store.reviews({
    id: 324684580,
    sort: store.sort.RECENT,
    page: 1 // paginate until date window exhausted
  });
  console.log(JSON.stringify(reviews.map(r => ({
    source: 'app_store',
    date: r.updated,
    rating: r.score,
    title: r.title || '',
    text: r.text
  }))));
}

fetchReviews().catch(e => { console.error(e); process.exit(1); });
```

Invoke from Python:

```python
import subprocess, json

def fetch_app_store() -> list[dict]:
    result = subprocess.run(
        ["node", "ingestion/app_store.js"],
        capture_output=True, text=True, check=True
    )
    return json.loads(result.stdout)
```

### 3.2 Play Store (`ingestion/play_store.js`)

Same pattern using `google-play-scraper` with `appId: 'com.spotify.music'`.

### 3.3 Reddit (`ingestion/reddit.py`)

```python
import praw
from datetime import datetime, timedelta, timezone

def fetch_reddit(since: datetime) -> list[dict]:
    reddit = praw.Reddit(
        client_id=os.environ["REDDIT_CLIENT_ID"],
        client_secret=os.environ["REDDIT_CLIENT_SECRET"],
        user_agent=os.environ["REDDIT_USER_AGENT"],
    )
    subreddits = ["spotify", "SpotifyPlaylists", "ifyoulikeblank"]
    records = []
    for sub in subreddits:
        for post in reddit.subreddit(sub).new(limit=500):
            created = datetime.fromtimestamp(post.created_utc, tz=timezone.utc)
            if created < since:
                continue
            records.append({
                "source": "reddit",
                "date": created.isoformat(),
                "rating": None,
                "title": post.title,
                "text": post.selftext or post.title,
            })
    return records
```

### 3.4 Community forum (`ingestion/community_forum.py`)

- Fetch public Ideas/Feature Requests board pages only
- Parse with BeautifulSoup; respect `robots.txt`
- Map to canonical schema

### 3.5 Phase 1 orchestration

```python
def phase_1_ingest() -> list[dict]:
    since = datetime.now(timezone.utc) - timedelta(weeks=int(os.getenv("REVIEW_WINDOW_WEEKS", 10)))
    all_reviews = []
    all_reviews += fetch_app_store()
    all_reviews += fetch_play_store()
    all_reviews += fetch_reddit(since)
    all_reviews += fetch_community_forum(since)
    write_json("data/raw_reviews.json", all_reviews)
    return all_reviews
```

**Exit gate:** Run [phase-1-ingestion/eval.md](./phases/phase-1-ingestion/eval.md) before proceeding.

---

## 4. Phase 2 — Cleaning & Normalization

### 4.1 `ingestion/normalizer.py`

```python
import re, hashlib

PII_PATTERNS = [
    re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),      # email
    re.compile(r"@\w+"),                            # handles
    re.compile(r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b"),  # phone
]

def strip_pii(text: str) -> str:
    for pattern in PII_PATTERNS:
        text = pattern.sub("[REDACTED]", text)
    return text

def normalize_record(raw: dict) -> dict:
    text = strip_pii(f"{raw.get('title', '')} {raw.get('text', '')}".strip())
    record = {
        "source": raw["source"],
        "date": normalize_date(raw["date"]),
        "rating": raw.get("rating"),
        "title": strip_pii(raw.get("title", "")),
        "text": text,
    }
    record["id"] = hashlib.sha256(f"{record['source']}|{record['title']}|{record['text']}".encode()).hexdigest()
    return record

def deduplicate(records: list[dict]) -> list[dict]:
    seen = set()
    unique = []
    for r in records:
        if r["id"] not in seen:
            seen.add(r["id"])
            unique.append(r)
    return unique
```

### 4.2 Phase 2 orchestration

```python
def phase_2_clean(raw: list[dict]) -> list[dict]:
    since = datetime.now(timezone.utc) - timedelta(weeks=int(os.getenv("REVIEW_WINDOW_WEEKS", 10)))
    cleaned = deduplicate([
        normalize_record(r) for r in raw
        if parse_date(r["date"]) >= since
    ])
    write_json("data/clean_reviews.json", cleaned)
    return cleaned
```

**Exit gate:** [phase-2-cleaning/eval.md](./phases/phase-2-cleaning/eval.md)

---

## 5. Phase 3 — LLM Classification

### 5.1 Prompt design (`classification/prompts.py`)

```python
SYSTEM_PROMPT = """You are a product analyst for Spotify music discovery.
Classify each review into exactly ONE theme relevant to music discovery.
Return JSON array with objects: {id, theme, confidence, discovery_relevant, sentiment}.
If not discovery-related, set theme="Other" and discovery_relevant=false.
Use at most these theme families (adapt names to data): Recommendation Quality,
Discovery Friction, Algorithm Transparency, Playlist & Curation, Listening Context.
Sentiment: positive | neutral | negative.
"""

def build_user_prompt(batch: list[dict]) -> str:
    return json.dumps([{"id": r["id"], "text": r["text"][:500]} for r in batch])
```

### 5.2 Classifier (`classification/classifier.py`)

```python
from groq import Groq

client = Groq(api_key=os.environ["GROQ_API_KEY"])

def classify_batch(batch: list[dict]) -> list[dict]:
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        temperature=0.1,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(batch)},
        ],
        response_format={"type": "json_object"},
    )
    return parse_classification_response(response, batch)

def classify_all(reviews: list[dict], batch_size: int = 25) -> list[dict]:
    enriched = []
    for i in range(0, len(reviews), batch_size):
        batch = reviews[i:i + batch_size]
        labels = classify_batch(batch)
        enriched.extend(merge_labels(batch, labels))
    return enriched
```

### 5.3 Theme cap enforcement

After classification, collapse rare themes into top 5 by volume; re-tag remainder as `Other`.

**Exit gate:** [phase-3-classification/eval.md](./phases/phase-3-classification/eval.md)

---

## 6. Phase 4 — Pulse Report Generation

### 6.1 Aggregation (`reporting/aggregator.py`)

- Filter `discovery_relevant == true`
- Count per theme; compute sentiment breakdown
- Select top 3 themes by volume (min confidence threshold 0.6)
- Select 3 quotes: highest confidence, diverse themes/sources

### 6.2 Pulse generator (`reporting/pulse_generator.py`)

```python
def generate_pulse(aggregated: dict, week_range: str) -> str:
    prompt = f"""Write a Spotify Discovery Pulse note for {week_range}.
Max 250 words. Include: header, top 3 themes (1 sentence each + counts),
3 verbatim user quotes (already PII-stripped), 3 prioritized PM action ideas, footer with total reviews.
Data: {json.dumps(aggregated)}
"""
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        temperature=0.2,
        messages=[{"role": "user", "content": prompt}],
    )
    pulse = response.choices[0].message.content
    assert word_count(pulse) <= 250
    return pulse
```

Write to `data/pulse_report.md`.

**Exit gate:** [phase-4-reporting/eval.md](./phases/phase-4-reporting/eval.md)

---

## 7. MCP Setup (Before Phase 5)

### 7.1 Choose MCP server

**Recommended:** Fork/reuse `saksham-mcp-server` from Groww capstone.

**Alternative:** `google-workplace-mcp` or `google-mcp` with equivalent tools.

Required tools:

- `docs_create`
- `docs_writeText` / `docs_append_text`
- `gmail_createDraft`

### 7.2 Cursor configuration

Create `.cursor/mcp.json` at project root:

```json
{
  "mcpServers": {
    "google-workspace": {
      "command": "node",
      "args": ["./mcp/google-workspace-mcp/dist/index.js"],
      "env": {
        "GOOGLE_CREDENTIALS_PATH": "${workspaceFolder}/credentials.json",
        "RECIPIENT_EMAIL": "your-email@example.com"
      }
    }
  }
}
```

Restart Cursor. Verify tools appear in MCP panel.

### 7.3 Google Cloud setup checklist

1. Create GCP project
2. Enable Gmail API, Docs API, Drive API
3. OAuth consent screen → add test users
4. Create Desktop OAuth client → download `credentials.json`
5. First run: complete OAuth flow to generate refresh token (MCP server handles this)
6. Scopes: `documents`, `drive.file`, `gmail.compose` — **not** `gmail.send`

### 7.4 Verify MCP in isolation

Before wiring pipeline code, manually test:

1. `docs_create` → title `MCP Test Doc`
2. `docs_writeText` → append `Hello from MCP`
3. `gmail_createDraft` → subject `MCP Test`, body with Doc link

Record results in [phase-5-delivery/eval.md](./phases/phase-5-delivery/eval.md).

---

## 8. Phase 5 — MCP Delivery

### 8.1 Delivery module structure

```
delivery/
├── mcp_client.py      # Low-level MCP transport (stdio / subprocess)
├── gdocs_client.py    # docs_create, docs_writeText wrappers
├── gmail_client.py    # gmail_createDraft wrapper
└── mcp_delivery.py    # Orchestrates full delivery from pulse_report.md
```

### 8.2 `mcp_delivery.py` flow

```python
def phase_5_deliver(pulse_path: str, week_range: str) -> tuple[str, str]:
    pulse = Path(pulse_path).read_text(encoding="utf-8")

    # 1. Google Doc
    doc_title = f"Spotify Discovery Pulse — {week_range}"
    doc_id = gdocs_client.create_document(doc_title)
    gdocs_client.write_formatted_content(doc_id, pulse)
    doc_url = gdocs_client.get_document_url(doc_id)

    # 2. Gmail draft
    subject = f"Spotify Discovery Pulse — Week of {week_range}"
    body = f"{pulse}\n\nFull report: {doc_url}"
    draft_id = gmail_client.create_draft(
        to=os.environ["RECIPIENT_EMAIL"],
        subject=subject,
        body=body,
    )

    # 3. Run log
    append_run_log(doc_url=doc_url, draft_id=draft_id)
    return doc_url, draft_id
```

### 8.3 MCP client options

**Option A — Subprocess (production):** Spawn MCP server as child process; communicate via stdio JSON-RPC.

**Option B — Cursor agent (development):** Human or Cursor agent invokes MCP tools directly; `mcp_delivery.py` documents the tool sequence for reproducibility.

**Option C — MCP SDK:** Use official MCP Python client if server supports HTTP/SSE transport on Railway.

### 8.4 Document formatting

Parse `pulse_report.md` sections and map to Docs structure:

| Markdown section | Docs formatting |
|------------------|-----------------|
| `# Title` | H1 |
| `## Top Themes` | H2 + bullets |
| `## User Quotes` | H2 + block quotes |
| `## Action Ideas` | H2 + numbered list |
| `## Run Metadata` | H2 + plain text |

### 8.5 Safety guardrails

```python
FORBIDDEN_GMAIL_TOOLS = {"gmail_send", "gmail_sendDraft"}

def invoke_mcp_tool(tool_name: str, **kwargs):
    if tool_name in FORBIDDEN_GMAIL_TOOLS:
        raise RuntimeError("Auto-send is forbidden. Use gmail_createDraft only.")
    ...
```

**Exit gate:** [phase-5-delivery/eval.md](./phases/phase-5-delivery/eval.md)

---

## 9. End-to-End Orchestration (`main.py`)

```python
def main():
    run_log = {"started_at": datetime.now(timezone.utc).isoformat(), "status": "running"}
    try:
        raw = phase_1_ingest()
        clean = phase_2_clean(raw)
        classified = phase_3_classify(clean)
        pulse_path = phase_4_report(classified)
        week_range = compute_week_range()
        doc_url, draft_id = phase_5_deliver(pulse_path, week_range)
        run_log.update({
            "status": "success",
            "review_counts": {"raw": len(raw), "clean": len(clean), "classified": len(classified)},
            "google_doc_url": doc_url,
            "gmail_draft_id": draft_id,
        })
    except Exception as e:
        run_log.update({"status": "failed", "error": str(e)})
        raise
    finally:
        write_json("data/run_log.json", run_log)
```

---

## 10. Testing Strategy

| Level | Location | When |
|-------|----------|------|
| Unit tests | `tests/test_*.py` | Per module during implementation |
| Phase evals | `docs/phases/*/eval.md` | Exit gate before next phase |
| Integration | `tests/test_pipeline.py` | After Phase 4 (mock MCP for Phase 5) |
| E2E | Manual + Railway | After Phase 5 + deploy |

Run all unit tests:

```bash
pytest tests/ -v
```

---

## 11. Deployment (Railway)

### 11.1 `Dockerfile` (multi-stage)

- Stage 1: Node — install scrapers
- Stage 2: Python — copy app, install requirements, entrypoint `python main.py`

### 11.2 `railway.toml`

```toml
[build]
builder = "dockerfile"

[deploy]
startCommand = "python main.py"
cronSchedule = "0 9 * * 1"  # Weekly Monday 9am UTC
```

### 11.3 Post-deploy verification

1. Trigger manual run from Railway dashboard
2. Confirm `data/run_log.json` shows `status: success`
3. Open Google Doc URL from run log
4. Confirm Gmail draft in Drafts folder

---

## 12. Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| < 50 reviews from a source | Narrow date window or API change | Expand `REVIEW_WINDOW_WEEKS`; check scraper output |
| Groq JSON parse errors | Model returned markdown fences | Add response parser strip; retry batch |
| MCP tools not visible in Cursor | Bad `mcp.json` path | Restart Cursor; check server logs |
| Gmail draft missing Doc link | `doc_url` not passed to draft body | Fix `mcp_delivery.py` template |
| OAuth token expired | Refresh token revoked | Re-authenticate MCP server |
| Phase 5 fails but pulse exists | MCP-only failure | `pulse_report.md` still valid; fix MCP and re-run Phase 5 only |

---

## 13. Related Documents

- [architecture.md](./architecture.md) — system design and data flow
- [decision.md](./decision.md) — tech and business decision log
- [ProblemStatement.md](../ProblemStatement.md) — requirements and acceptance criteria
- Phase evals: [docs/phases/](./phases/)
