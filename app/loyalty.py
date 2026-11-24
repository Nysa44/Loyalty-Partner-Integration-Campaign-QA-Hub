from datetime import date
import json
from .db import connect

TIERS = [(0, "Blue"), (1000, "Silver"), (5000, "Gold"), (15000, "Platinum")]

def tier_for(points: int) -> str:
    tier = "Blue"
    for threshold, name in TIERS:
        if points >= threshold:
            tier = name
    return tier

def calculate_points(partner_rate, amount, multiplier=1.0, weekend_bonus=False, transaction_date=None):
    points = int(round(float(amount) * float(partner_rate) * float(multiplier)))
    if weekend_bonus and transaction_date:
        try:
            if date.fromisoformat(transaction_date).weekday() >= 5:
                points *= 2
        except ValueError:
            pass
    return max(points, 0)

def member_summary(member_id):
    with connect() as c:
        row = c.execute("SELECT COALESCE(SUM(points),0) AS points FROM transactions WHERE member_id=?", (member_id,)).fetchone()
    points = int(row["points"])
    return {"member_id": member_id, "points": points, "tier": tier_for(points)}
