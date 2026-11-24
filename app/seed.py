import csv, json, random
from .db import init_db, connect
from .config import BASE_DIR

PARTNERS = [
    ("hotelco", "Northstar Hotels (SIMULATED)", 2.0),
    ("shopco", "Cedar Retail (SIMULATED)", 1.0),
    ("driveco", "Waypoint Car Rental (SIMULATED)", 1.5),
]
def _write(rows, stem, out):
    with (out / f"{stem}.json").open("w") as f:
        json.dump(rows, f, indent=2)
    with (out / f"{stem}.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

def seed():
    init_db()
    with connect() as c:
        for p in PARTNERS:
            c.execute("INSERT OR IGNORE INTO partners(id,name,earn_rate) VALUES(?,?,?)", p)
        for i in range(1, 101):
            c.execute("INSERT OR IGNORE INTO members(id,name) VALUES(?,?)", (f"M{i:04d}", f"Demo Member {i:03d}"))
    out = BASE_DIR / "data"
    out.mkdir(exist_ok=True)
    rng = random.Random(44)
    rows = []
    for i in range(1, 2001):
        partner = PARTNERS[(i-1) % 3][0]
        rows.append({
            "partner_id": partner,
            "transaction_id": f"TX{i:05d}", "member_id": f"M{rng.randint(1,100):04d}",
            "amount": round(rng.uniform(10, 500), 2), "currency": "AED",
            "transaction_date": f"2026-11-{rng.randint(1,24):02d}", "campaign_id": None
        })
    grouped = {p[0]: [r.copy() for r in rows if r["partner_id"] == p[0]] for p in PARTNERS}
    # Per partner, inject 2 duplicate IDs, 2 missing member IDs, 2 unsupported currencies,
    # and 2 negative amounts. Across 3 feeds: 6 duplicate rows + 18 rejected rows.
    for partner_id, group in grouped.items():
        for idx in range(2):
            group[100 + idx]["transaction_id"] = group[idx]["transaction_id"]
            group[200 + idx]["member_id"] = ""
            group[300 + idx]["currency"] = "USD"
            group[400 + idx]["amount"] = -abs(group[400 + idx]["amount"])
        _write(group, f"sample_{partner_id}", out)
    _write(rows, "sample_transactions", out)
    (out / "late_feed_example.json").write_text(json.dumps({
      "partner_id":"hotelco","source_file":"late_partner_feed.json",
      "received_at":"2026-11-24T23:59:00","expected_by":"2026-11-24T18:00:00",
      "note":"SIMULATED late feed marker for monitoring demonstration"
    }, indent=2))
    print("Seeded 2,000 deterministic transactions across 3 fictional partners.")
    print("Known injected faults: 6 duplicate rows, 6 missing member IDs, 6 unsupported currencies, 6 negative amounts.")
    print("Expected first-pass totals across the 3 partner feeds: 1,976 posted, 18 rejected, 6 duplicates skipped.")
if __name__ == "__main__":
    seed()
