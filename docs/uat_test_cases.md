# UAT Test Cases — Orbit Rewards (SIMULATED)

| ID | Scenario | Expected result |
|---|---|---|
| UAT-01 | Valid AED transaction | Points posted and audit event written |
| UAT-02 | Re-upload same partner transaction ID | Duplicate skipped; no second credit |
| UAT-03 | Missing transaction ID | Row rejected with validation reason |
| UAT-04 | Missing member ID | Row rejected |
| UAT-05 | Unknown member | Row rejected as UNKNOWN_MEMBER |
| UAT-06 | Unsupported currency | Row rejected as UNSUPPORTED_CURRENCY |
| UAT-07 | Negative amount | Row rejected; no points posted |
| UAT-08 | Invalid date format | Row rejected |
| UAT-09 | Weekend campaign bonus | Eligible weekend transaction earns bonus points |
| UAT-10 | Campaign end date before start | Campaign validation fails |
| UAT-11 | Same-partner overlapping campaign | Campaign validation fails |
| UAT-12 | Missing budget or multiplier above 5 | Campaign validation fails |
| UAT-13 | Feed contains rejects | Rejects and feed-run reconciliation are queryable |
| UAT-14 | LLM unavailable or key absent | Template triage returned with human-review flag |
