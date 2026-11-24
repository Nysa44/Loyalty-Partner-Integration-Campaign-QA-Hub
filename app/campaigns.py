from datetime import date
from .db import connect

def validate_campaign(payload):
    errors = []
    try:
        start = date.fromisoformat(payload.start_date)
        end = date.fromisoformat(payload.end_date)
        if end < start:
            errors.append("END_BEFORE_START")
    except ValueError:
        errors.append("INVALID_DATE")
        start = end = None
    if payload.budget_cap is None or payload.budget_cap <= 0:
        errors.append("MISSING_OR_INVALID_BUDGET_CAP")
    if payload.earn_multiplier <= 0 or payload.earn_multiplier > 5:
        errors.append("EARN_MULTIPLIER_OUT_OF_RANGE")
    if start and end and end >= start:
        with connect() as c:
            overlaps = c.execute("""
              SELECT id FROM campaigns
              WHERE partner_id=? AND active=1 AND id<>?
              AND NOT (end_date < ? OR start_date > ?)
            """, (payload.partner_id, payload.id, payload.start_date, payload.end_date)).fetchall()
        if overlaps:
            errors.append("OVERLAPPING_CAMPAIGN:" + ",".join(x["id"] for x in overlaps))
    with connect() as c:
        exists = c.execute("SELECT 1 FROM partners WHERE id=?", (payload.partner_id,)).fetchone()
    if not exists:
        errors.append("UNKNOWN_PARTNER")
    return {"status": "PASS" if not errors else "FAIL", "errors": errors}

def save_campaign(payload):
    result = validate_campaign(payload)
    if result["status"] == "FAIL":
        return result
    with connect() as c:
        c.execute("""
          INSERT INTO campaigns(id,partner_id,name,start_date,end_date,budget_cap,earn_multiplier,bonus_weekends,active)
          VALUES(?,?,?,?,?,?,?,?,?)
          ON CONFLICT(id) DO UPDATE SET partner_id=excluded.partner_id,name=excluded.name,
          start_date=excluded.start_date,end_date=excluded.end_date,budget_cap=excluded.budget_cap,
          earn_multiplier=excluded.earn_multiplier,bonus_weekends=excluded.bonus_weekends,active=excluded.active
        """, (payload.id,payload.partner_id,payload.name,payload.start_date,payload.end_date,
              payload.budget_cap,payload.earn_multiplier,int(payload.bonus_weekends),int(payload.active)))
    return result
