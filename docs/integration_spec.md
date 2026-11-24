# Partner Integration Specification — Orbit Rewards (SIMULATED)

## Purpose and scope
Accept fictional partner transaction feeds, validate schema and business rules, post eligible loyalty points once, preserve rejects for operations review, and reconcile the partner feed with posting outcomes.

## Interface
- Transport: HTTPS REST in a real deployment; local demo uses HTTP.
- Endpoint: `POST /partners/{partner_id}/ingest`
- Formats: JSON array or CSV.
- Required fields: `transaction_id`, `member_id`, `amount`, `currency`, `transaction_date`.
- Optional: `campaign_id`.
- Currency rule: AED only in this simulation.
- Idempotency key: `(partner_id, transaction_id)`.
- Response: row, posted, rejected, duplicate and points counts plus monetary reconciliation totals.

## Processing
1. Authenticate partner (not implemented in demo).
2. Parse file and validate each row.
3. Check member exists and currency is supported.
4. Check idempotency key.
5. Apply partner earn rate and eligible campaign multiplier.
6. Post transaction and audit event in one database operation.
7. Store invalid rows in rejects with reason code.
8. Create feed-run reconciliation summary.

## Operational reason codes
`INVALID_TRANSACTION`, `MISSING_MEMBER_ID`, `UNKNOWN_MEMBER`, `INVALID_AMOUNT`, `INVALID_CURRENCY`, `UNSUPPORTED_CURRENCY`, `INVALID_DATE`, `VALIDATION_ERROR`.

## Non-functional expectations
Use encrypted transport, authenticated partner identities, replay protection, agreed partner SLAs, structured logs, least-privilege access, retention policy and monitored error budgets in production.
