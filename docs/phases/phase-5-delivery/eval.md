# Phase 5 Evaluation — MCP Delivery (Google Docs + Gmail)

> **Phase:** 5 — Delivery via MCP  
> **Input:** `data/pulse_report.md`  
> **Output:** Google Doc URL + Gmail draft ID (logged in `data/run_log.json`)  
> **Implementation:** [implementation.md §7–8](../../implementation.md)  
> **Architecture:** [architecture.md §3.6](../../architecture.md)  
> **Decision:** [DEC-001, DEC-005, DEC-009, DEC-010](../../decision.md)

---

## 1. Phase Objective

Deliver the weekly pulse note to Google Docs (formatted, new doc per run) and create a Gmail draft (never auto-send) using the Google Workspace MCP server.

---

## 2. Exit Criteria (Gate to Deployment / Part 1 Complete)

| # | Criterion | Target | Blocking |
|---|-----------|--------|----------|
| E5.1 | MCP server connected | Tools `docs_create`, `docs_writeText`/`docs_append_text`, `gmail_createDraft` available | Yes |
| E5.2 | Google Doc created | New doc per run — not overwritten | Yes |
| E5.3 | Doc title correct | `Spotify Discovery Pulse — [Week Range]` | Yes |
| E5.4 | Doc formatting | H1 title + H2 sections (`Top Themes`, `User Quotes`, `Action Ideas`, `Run Metadata`) | Yes |
| E5.5 | Doc content complete | Full pulse text present; matches `pulse_report.md` | Yes |
| E5.6 | Doc URL logged | `google_doc_url` in `data/run_log.json` | Yes |
| E5.7 | Gmail draft created | Draft visible in Drafts folder | Yes |
| E5.8 | Draft subject | `Spotify Discovery Pulse — Week of [Date]` | Yes |
| E5.9 | Draft body | Pulse content + clickable Google Doc link | Yes |
| E5.10 | Draft recipient | Matches `RECIPIENT_EMAIL` env var | Yes |
| E5.11 | No auto-send | `gmail_send` / `gmail_sendDraft` never invoked | Yes |
| E5.12 | MCP path used | Delivery logs show MCP tool calls (not direct API bypass) | Yes |
| E5.13 | OAuth scopes | `gmail.compose` only — not `gmail.send` | Yes |
| E5.14 | PII in delivered artifacts | 0 PII in Doc and draft | Yes |

---

## 3. Test Plan

### 3.1 MCP Connectivity Test (Pre-Phase 5)

Run before wiring pipeline delivery.

| Step | MCP Tool | Expected Result | Pass? |
|------|----------|-----------------|-------|
| 1 | List available tools | `docs_create`, `gmail_createDraft` present | |
| 2 | `docs_create` | Returns document ID | |
| 3 | `docs_writeText` / `docs_append_text` | Text appears in doc | |
| 4 | `docs_getText` (optional) | Content readable | |
| 5 | `gmail_createDraft` | Draft ID returned | |
| 6 | Manual check Gmail | Draft in Drafts folder | |

### 3.2 Unit Tests (Mocked MCP)

| Test ID | Module | Description | Assertion |
|---------|--------|-------------|-----------|
| T5.1 | `gdocs_client.py` | `create_document` calls MCP | Mock receives `docs_create` |
| T5.2 | `gdocs_client.py` | Section formatting map | H1/H2 structure applied |
| T5.3 | `gmail_client.py` | `create_draft` calls MCP | Mock receives `gmail_createDraft` |
| T5.4 | `mcp_delivery.py` | Forbidden tools blocked | `gmail_send` raises error |
| T5.5 | `mcp_delivery.py` | Doc link in email body | URL pattern in body |
| T5.6 | `mcp_delivery.py` | Run log updated | `google_doc_url` set |

**Run:**

```bash
pytest tests/test_delivery.py -v
```

### 3.3 Integration Test (Live MCP)

```bash
python -c "
from main import phase_5_deliver
doc_url, draft_id = phase_5_deliver('data/pulse_report.md', '9–15 June 2026')
assert doc_url.startswith('https://docs.google.com')
assert draft_id
import json
log = json.load(open('data/run_log.json'))
assert log.get('google_doc_url') == doc_url
print('PASS:', doc_url, draft_id)
"
```

### 3.4 Manual Verification Checklist

**Google Doc:**

- [ ] Open `google_doc_url` from `run_log.json`
- [ ] Title matches week range
- [ ] H1/H2 formatting visible (not flat plaintext)
- [ ] All 3 themes, 3 quotes, 3 action ideas present
- [ ] Footer metadata present
- [ ] Prior week's doc still exists (not overwritten) — [DEC-010](../../decision.md)

**Gmail Draft:**

- [ ] Open Gmail → Drafts
- [ ] Subject line correct
- [ ] Body contains pulse summary
- [ ] Google Doc link works
- [ ] Email was NOT sent automatically

**Security:**

- [ ] Confirm no email in Sent folder from this run
- [ ] Delivery code grep: no `gmail_send` calls

```bash
# Static check — no forbidden send calls
rg "gmail_send|gmail_sendDraft" delivery/ --glob "*.py" && echo "FAIL: send found" || echo "PASS: no send calls"
```

---

## 4. Evaluation Metrics

### Run: _[YYYY-MM-DD / run_id]_

| Metric | Value | Pass? |
|--------|-------|-------|
| MCP server name / version | | |
| `docs_create` latency (ms) | | |
| `docs_writeText` calls count | | |
| `gmail_createDraft` latency (ms) | | |
| Google Doc URL | | |
| Gmail draft ID | | |
| Pulse chars written to Doc | | |
| Doc content matches pulse (diff bytes) | | |
| Delivery duration (seconds) | | |
| MCP errors / retries | | |
| Auto-send guard triggered | | |

---

## 5. End-to-End Part 1 Acceptance

Phase 5 eval is the final gate. Cross-reference [ProblemStatement.md §8](../../../ProblemStatement.md):

| Acceptance # | Criterion | Verified in |
|--------------|-----------|-------------|
| 5 | Google Doc via MCP | E5.2–E5.6 |
| 6 | Gmail draft via MCP | E5.7–E5.10 |
| 7 | `main.py` cold start E2E | Full pipeline run |
| 8 | Railway deployment | Post-deploy cron run |
| 9 | MCP integration | E5.12 |

### E2E Cold Start Test

```bash
# Fresh clone simulation
rm -rf data/*.json data/pulse_report.md
python main.py
# Verify all data artifacts + run_log status: success
```

---

## 6. Failure Handling

| Failure | Action |
|---------|--------|
| MCP server not starting | Check `.cursor/mcp.json` / Railway service; verify credentials |
| OAuth token expired | Re-authenticate; update refresh token in secrets |
| Doc created but empty | Fix `gdocs_client` write sequence; delete orphan doc |
| Draft missing Doc link | Fix `mcp_delivery.py` body template; re-run Phase 5 only |
| Formatting lost | Use `docs_formatText` or structured write; update client |
| `gmail.send` scope requested | Remove scope from OAuth config — [DEC-005](../../decision.md) |
| Phase 5 fails, pulse OK | Safe to retry Phase 5 without re-running 1–4 |

---

## 7. Deployment Eval (Railway)

| # | Criterion | How to Verify | Pass? |
|---|-----------|---------------|-------|
| D1 | Pipeline service deploys | Railway build green | |
| D2 | MCP server reachable from pipeline | Delivery succeeds on Railway | |
| D3 | Secrets configured | All env vars set in Railway dashboard | |
| D4 | Cron triggers weekly | Manual + scheduled run | |
| D5 | `run_log.json` persists or logs to stdout | Check volume / Railway logs | |
| D6 | Google Doc + draft from production run | Same manual checks as §3.4 | |

---

## 8. Sign-off

| Role | Name | Date | Result |
|------|------|------|--------|
| Implementer | | | Pass / Fail |
| Reviewer | | | Pass / Fail |

**Notes:**

---

## 9. Artifacts Produced

- [ ] Google Doc created (URL in `run_log.json`)
- [ ] Gmail draft created (ID in `run_log.json`)
- [ ] `tests/test_delivery.py` (green)
- [ ] MCP connectivity test PASS (§3.1)
- [ ] No auto-send verified (§3.4)
- [ ] E2E cold start PASS (§5)
- [ ] Railway deployment PASS (§7) — if deploying
- [ ] Metrics table (§4) filled

**Part 1 status:** ☐ Complete / ☐ Incomplete
