# Orbit Rewards — Loyalty Partner Integration & Campaign QA Hub

**SIMULATED portfolio project.** Orbit Rewards, Northstar Hotels, Cedar Retail, Waypoint Car Rental and all members/transactions are fictional. This is not affiliated with any airline.

A compact FastAPI + SQLite loyalty operations back office demonstrating partner feed ingestion, validation, duplicate-safe points posting, reconciliation, campaign QA, monitoring, tier calculation, audit logging and evidence-grounded AI triage.

## Quick start

Python 3.10+ recommended.

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
python -m app.seed
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/docs for interactive API documentation.

## Demo flow

1. Seed the demo partners, members and 2,000 deterministic transactions:
   `python -m app.seed`
2. In `/docs`, call `POST /partners/hotelco/ingest` and upload `data/sample_hotelco.json` (or the CSV equivalent). Repeat for `shopco` with `data/sample_shopco.json`, and `driveco` with `data/sample_driveco.json`.
3. Repeat the same upload. Previously posted partner transaction IDs are skipped; they are not double-credited.
4. Inspect `/metrics`, `/reconciliation`, `/rejects`, `/audit` and `/members/M0001/tier`.
5. Try `POST /campaigns/validate` with an overlapping campaign or a multiplier above 5.
6. Try `POST /triage` with feed evidence. It uses a template fallback unless LLM configuration is supplied.

The three partner-specific sample files contain 2,000 deterministic transactions in total and seeded fault injections: 6 duplicate rows, 6 missing member IDs, 6 unsupported currencies and 6 negative amounts. Expected first-pass aggregate outcome: 1,976 posted, 18 rejected and 6 duplicates skipped. The API accepts `.json` arrays or `.csv` files. The API validates each row independently and records rejects with reason codes.

## Example API calls

```bash
curl -X POST "http://127.0.0.1:8000/partners/hotelco/ingest" \
  -F "file=@data/sample_transactions.json"

curl http://127.0.0.1:8000/metrics
curl http://127.0.0.1:8000/reconciliation
curl http://127.0.0.1:8000/rejects
```

Example campaign payload:

```json
{
  "id": "WEEKEND-01",
  "partner_id": "hotelco",
  "name": "Weekend Double Points",
  "start_date": "2026-12-01",
  "end_date": "2026-12-31",
  "budget_cap": 25000,
  "earn_multiplier": 2,
  "bonus_weekends": true,
  "active": true
}
```

## LLM triage (optional)

The app works without an LLM. To enable an OpenAI-compatible Chat Completions endpoint, copy `.env.example` to `.env`, set `LLM_API_KEY`, `LLM_BASE_URL` and `LLM_MODEL`, then export those variables in your shell before starting the app. The code uses the API key only on the server side. It sends only the evidence fields supplied to `/triage`; it does not send member names or raw transaction rows. It validates the response shape, retries once, and falls back to a deterministic template with `needs_human_review: true`.

## Metrics and operational controls

- `/health`: process/database health check.
- `/metrics`: received, posted, rejected and duplicate counts; reject rate; time since last feed; net reconciliation discrepancy; threshold alerts.
- `/reconciliation`: per-file totals and discrepancy; duplicate-row amounts are explicitly accounted for so a clean feed reconciles to zero.
- `/rejects`: rejected rows with reason codes.
- `/audit`: append-only event records for posted points and skipped duplicates.

The demo alert threshold is a reject rate above 2%; reconciliation alert triggers when net discrepancy is greater than 0.01 in absolute value. Feed lag is shown as minutes since the latest feed was received (a production implementation would compare against each partner's agreed SLA).

## Earn and tier rules

Partner earn rates are seeded in `app/seed.py`: hotel 2 points/AED, retail 1 point/AED, car rental 1.5 points/AED. Tiers are illustrative cumulative posted-point thresholds: Blue 0, Silver 1,000, Gold 5,000, Platinum 15,000. These are invented demo rules, not any real loyalty programme rules.

## Tests

```bash
pytest -q
```

The test suite covers health, tier thresholds, weekend bonus, successful ingestion, idempotent re-upload, currency and member rejection, campaign date/budget/multiplier/overlap checks, metrics/reconciliation and LLM fallback.

## Project limitations / production hardening

This is a portfolio simulation, not production airline software. A production deployment should add authentication/authorization, partner-specific signing and encryption, file-size and rate controls at the gateway, immutable external audit storage, currency/FX policy, timezone-aware SLA schedules, database migrations, concurrency-safe transactional batch ingestion, secrets management, observability integration and formal security testing. The demo's CSV/JSON upload is intentionally small and SQLite-backed.
