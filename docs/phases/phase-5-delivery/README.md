# Phase 5 — MCP Delivery

Phase 5 delivers `pulse_report.md` to Google Docs and Gmail Drafts through an MCP server.

## Inputs

- `../phase-4-reporting/data/pulse_report.md`

## Outputs

- `data/run_log.json`
- `data/phase5_delivery_report.json`

## Setup

1. Copy `.env.example` to `.env`.
2. Fill:
   - `MCP_SERVER_URL`
   - `RECIPIENT_EMAIL`
   - `GOOGLE_DOC_ID` (only needed when server does not support `docs_create`)

## Run

```bash
python main.py
```

Optional:

```bash
python main.py --week-range "24-28 June 2026"
```

## Validate

```bash
pytest tests/test_delivery.py -v
python scripts/validate_phase5.py
```

