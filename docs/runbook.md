# Operations Runbook — Orbit Rewards (SIMULATED)

## Feed rejection
1. Check `/health`, then `/metrics`.
2. Open `/rejects?partner_id=hotelco` (replace partner ID as needed).
3. Group rows by `reason_code`; do not manually edit posted transactions.
4. Share the reason-code summary and sample row references with the partner through the approved channel.
5. Request a corrected feed with the same stable transaction IDs.
6. Re-upload. Previously posted rows are skipped by the idempotency key; corrected previously rejected rows can be posted.
7. Check `/reconciliation` and `/audit`; record operational sign-off.

## Reconciliation discrepancy
1. Identify the affected feed in `/reconciliation`.
2. Compare declared, posted and rejected totals.
3. Inspect rejected rows and duplicate counts.
4. Submit evidence to `/triage`; review its recommendation. AI output is advisory only.
5. Escalate unresolved discrepancies to the partner owner and finance/loyalty operations.
6. Do not close the incident until totals are explained and a human owner signs off.

## Service disruption
1. Check `/health` and application logs.
2. If database health fails, stop ingestion and preserve the database file.
3. Notify the technical owner; capture timestamp, partner, endpoint and error details.
4. Restore service only after database integrity and API health checks pass.
5. Reconcile all partner files received during the outage; replay safely using stable transaction IDs.
