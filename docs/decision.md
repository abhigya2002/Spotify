# Decision Log — Spotify Discovery Agent

> **Purpose:** Record significant technical and business decisions so future contributors (and Parts 2–4) understand *why* choices were made, not just *what* was built.  
> **Format:** Lightweight ADR (Architecture Decision Record)

---

## How to Use This File

When making a non-obvious choice:

1. Add a new entry at the **top** of the [Decision Index](#decision-index) (newest first)
2. Copy the [Decision Template](#decision-template) into a new section
3. Fill in context, options considered, decision, and consequences
4. Link related eval results if the decision affects a phase exit gate

**Log a decision when:**

- Choosing between two or more viable technical approaches
- Setting a business/product threshold (e.g., min review count, theme cap)
- Changing scope or constraints from the problem statement
- Reversing a prior decision

---

## Decision Index

| ID | Date | Title | Status | Category |
|----|------|-------|--------|----------|
| DEC-001 | 2026-06-26 | MCP as primary delivery path (not direct Google API) | Accepted | Technical |
| DEC-002 | 2026-06-26 | Groq llama-3.3-70b-versatile for classification + pulse | Accepted | Technical |
| DEC-003 | 2026-06-26 | Node subprocess for App/Play store scrapers | Accepted | Technical |
| DEC-004 | 2026-06-26 | pulse_report.md as delivery intermediate artifact | Accepted | Technical |
| DEC-005 | 2026-06-26 | Gmail draft-only policy (no auto-send) | Accepted | Business |
| DEC-006 | 2026-06-26 | 8–12 week review window, target ≥200 reviews | Accepted | Business |
| DEC-007 | 2026-06-26 | Maximum 5 discovery themes per run | Accepted | Business |
| DEC-008 | 2026-06-26 | Railway for pipeline + MCP server hosting | Accepted | Technical |
| DEC-009 | 2026-06-26 | Reuse saksham-mcp-server pattern from Groww capstone | Accepted | Technical |
| DEC-010 | 2026-06-26 | New Google Doc per weekly run (no overwrite) | Accepted | Business |

---

## Decision Template

```markdown
### DEC-XXX — [Title]

**Date:** YYYY-MM-DD  
**Status:** Proposed | Accepted | Superseded by DEC-YYY | Deprecated  
**Category:** Technical | Business | Process  
**Deciders:** [names or roles]

#### Context
What problem or question triggered this decision?

#### Options Considered
| Option | Pros | Cons |
|--------|------|------|
| A | | |
| B | | |

#### Decision
What we chose and why.

#### Consequences
- Positive: ...
- Negative: ...
- Follow-up: ...
```

---

## Recorded Decisions

### DEC-001 — MCP as primary delivery path (not direct Google API)

**Date:** 2026-06-26  
**Status:** Accepted  
**Category:** Technical  
**Deciders:** Project team (NextLeap capstone)

#### Context
Phase 5 must deliver pulse reports to Google Docs and Gmail. Two approaches: embed Google API client libraries in Python pipeline, or use a Model Context Protocol (MCP) server.

#### Options Considered
| Option | Pros | Cons |
|--------|------|------|
| Direct Google API in Python | Single process; no MCP dependency | OAuth complexity in app code; harder to reuse in Cursor agent workflow |
| MCP server (Google Workspace) | Agent-native; proven in Groww capstone; separates delivery from pipeline | Extra process to host; MCP transport setup |

#### Decision
Use **MCP server as the primary delivery path**. Pipeline Phases 1–4 produce `pulse_report.md`; Phase 5 invokes MCP tools (`docs_create`, `docs_writeText`, `gmail_createDraft`). Direct Google API only as fallback if MCP is unavailable.

#### Consequences
- Positive: Cleaner separation; Cursor can test delivery interactively; reusable for Part 4 MVP
- Negative: Railway must co-host MCP server or use stdio subprocess
- Follow-up: Document MCP setup in [implementation.md](./implementation.md) §7

---

### DEC-002 — Groq llama-3.3-70b-versatile for classification + pulse

**Date:** 2026-06-26  
**Status:** Accepted  
**Category:** Technical

#### Context
Need an LLM for batch review classification (JSON output) and pulse note generation (≤250 words).

#### Options Considered
| Option | Pros | Cons |
|--------|------|------|
| OpenAI GPT-4o | High quality | Cost; not used in prior capstone |
| Groq llama-3.3-70b-versatile | Fast; free tier; proven on Groww (276 reviews) | Groq rate limits |
| Local model (Ollama) | No API cost | Deployment complexity; slower on Railway |

#### Decision
Use **Groq `llama-3.3-70b-versatile`** at temperature 0.1 (classification) and 0.2 (pulse generation). Batch size 20–30 reviews.

#### Consequences
- Positive: Consistent with Groww learnings; low latency
- Negative: Must handle Groq rate limits with retry/backoff
- Follow-up: Log token usage in `run_log.json` for cost tracking

---

### DEC-003 — Node subprocess for App/Play store scrapers

**Date:** 2026-06-26  
**Status:** Accepted  
**Category:** Technical

#### Context
App Store and Play Store ingestion require `app-store-scraper` and `google-play-scraper` — both are npm packages.

#### Options Considered
| Option | Pros | Cons |
|--------|------|------|
| Rewrite scrapers in Python | Single language | Reinventing wheel; maintenance burden |
| Node subprocess from Python | Proven npm libraries; minimal wrapper | Two runtimes in Docker image |
| Separate microservice | Clean isolation | Over-engineered for capstone scope |

#### Decision
**Node subprocess** — Python orchestrator calls `node ingestion/app_store.js` and `play_store.js`; stdout returns JSON.

#### Consequences
- Positive: Reliable scrapers from Groww; thin wrappers
- Negative: Dockerfile needs Node + Python
- Follow-up: Pin npm package versions in `package-lock.json`

---

### DEC-004 — pulse_report.md as delivery intermediate artifact

**Date:** 2026-06-26  
**Status:** Accepted  
**Category:** Technical

#### Context
Need a stable handoff between report generation (Phase 4) and Google delivery (Phase 5).

#### Decision
Always write **`data/pulse_report.md`** before MCP delivery. Phase 5 reads this file exclusively — never regenerate pulse content at delivery time.

#### Consequences
- Positive: Phase 5 can be re-run without re-classifying; easy manual review
- Negative: Extra file on disk
- Follow-up: Include path in `run_log.json`

---

### DEC-005 — Gmail draft-only policy (no auto-send)

**Date:** 2026-06-26  
**Status:** Accepted  
**Category:** Business

#### Context
Weekly pulse is sent to PM reviewer. Auto-send risks spamming stakeholders and bypassing human review.

#### Decision
Use **`gmail_createDraft` only**. Never request `gmail.send` OAuth scope. Block `gmail_send` / `gmail_sendDraft` in delivery code.

#### Consequences
- Positive: Human-in-the-loop before any email goes out; aligns with problem statement
- Negative: Reviewer must manually send if desired
- Follow-up: Enforce in [phase-5-delivery/eval.md](./phases/phase-5-delivery/eval.md)

---

### DEC-006 — 8–12 week review window, target ≥200 reviews

**Date:** 2026-06-26  
**Status:** Accepted  
**Category:** Business

#### Context
Need enough review volume for statistically meaningful themes without stale data.

#### Decision
Default **10-week window** (configurable 8–12 via `REVIEW_WINDOW_WEEKS`). **Minimum 200 clean reviews** before proceeding to classification. If any source returns < 50, expand window and log in decision log.

#### Consequences
- Positive: Balances recency and volume; Groww achieved 276 reviews
- Negative: Sparse sources may require window expansion
- Follow-up: Phase 1 eval tracks per-source counts

---

### DEC-007 — Maximum 5 discovery themes per run

**Date:** 2026-06-26  
**Status:** Accepted  
**Category:** Business

#### Context
Pulse note must be scannable for PM audience. Too many themes dilute signal.

#### Decision
Cap at **5 unique themes**. Reviews classified outside top 5 or irrelevant → `Other`, excluded from pulse.

#### Consequences
- Positive: Forces prioritization; matches pulse structure (top 3 displayed)
- Negative: Some nuance lost in long tail
- Follow-up: Full classified data retained in JSON for Part 2 deep dives

---

### DEC-008 — Railway for pipeline + MCP server hosting

**Date:** 2026-06-26  
**Status:** Accepted  
**Category:** Technical

#### Context
Problem statement requires production deployment. Groww capstone used Railway successfully.

#### Decision
Deploy on **Railway** with weekly cron. Co-host MCP server in same project or as sibling service.

#### Consequences
- Positive: Proven path; simple cron; volume mount for `data/`
- Negative: Railway pricing if run frequency increases
- Follow-up: `railway.toml` + Dockerfile in repo root

---

### DEC-009 — Reuse saksham-mcp-server pattern from Groww capstone

**Date:** 2026-06-26  
**Status:** Accepted  
**Category:** Technical

#### Context
Groww project validated MCP for Google Docs + Gmail. Multiple community MCP servers exist with different tool names.

#### Decision
**Prefer forking/reusing `saksham-mcp-server`** over adopting a new community server, unless tooling gaps block progress.

#### Consequences
- Positive: Known tool names and OAuth flow; faster Phase 5
- Negative: May need to port server into repo
- Follow-up: If blocked, log superseding decision with chosen alternative

---

### DEC-010 — New Google Doc per weekly run (no overwrite)

**Date:** 2026-06-26  
**Status:** Accepted  
**Category:** Business

#### Context
Part 2 interviews and Part 3 problem definition benefit from historical pulse archive.

#### Decision
**Create a new Google Doc each run** titled `Spotify Discovery Pulse — [Week Range]`. Store URL in `run_log.json`.

#### Consequences
- Positive: Weekly trend analysis; audit trail for capstone submission
- Negative: More Docs in Drive over time
- Follow-up: Optional folder organization in Drive (future decision)

---

## Superseded / Open Decisions

_Use this section when reversing or pending decisions._

| ID | Title | Status | Notes |
|----|-------|--------|-------|
| — | — | — | No open decisions |

---

## Related Documents

- [architecture.md](./architecture.md)
- [implementation.md](./implementation.md)
- [ProblemStatement.md](../ProblemStatement.md)
- Phase evals: [docs/phases/](./phases/)
