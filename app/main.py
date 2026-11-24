import csv, io, json
from datetime import datetime
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from .db import init_db, connect
from .schemas import TransactionRow, CampaignInput
from .loyalty import calculate_points, member_summary
from .campaigns import validate_campaign, save_campaign
from .triage import generate_triage

app = FastAPI(title="Orbit Rewards Loyalty Operations Hub", version="1.0.0",
              description="SIMULATED airline-style loyalty partner operations platform. No real airline data.")
@app.on_event("startup")
def startup():
    init_db()

@app.get("/")
def root():
    return {"program":"Orbit Rewards (SIMULATED)", "message":"Loyalty partner integration and campaign QA API",
            "docs":"/docs", "warning":"All partners and data are fictional."}

@app.get("/health")
def health():
    with connect() as c:
        c.execute("SELECT 1").fetchone()
    return {"status":"ok","database":"ok","timestamp":datetime.utcnow().isoformat()+"Z"}

def _parse_upload(content, filename):
    try:
        if filename.lower().endswith(".json"):
            data = json.loads(content.decode("utf-8"))
            if not isinstance(data, list): raise ValueError("JSON must be an array of transaction objects")
            return data
        if filename.lower().endswith(".csv"):
            return list(csv.DictReader(io.StringIO(content.decode("utf-8-sig"))))
    except Exception as exc:
        raise HTTPException(400, f"Could not parse file: {exc}")
    raise HTTPException(400, "Upload a .csv or .json file")

@app.post("/partners/{partner_id}/ingest")
async def ingest(partner_id: str, file: UploadFile = File(...)):
    init_db()
    raw = await file.read()
    if len(raw) > 5_000_000:
        raise HTTPException(413, "File exceeds 5 MB limit")
    rows = _parse_upload(raw, file.filename or "upload.csv")
    with connect() as c:
        partner = c.execute("SELECT * FROM partners WHERE id=?", (partner_id,)).fetchone()
    if not partner:
        raise HTTPException(404, "Unknown partner. Seed demo partners first.")
    posted = rejected = duplicates = posted_points = 0
    posted_total = rejected_total = duplicate_total = declared_total = 0.0
    for index, item in enumerate(rows, start=1):
        declared_total += float(item.get("amount") or 0) if str(item.get("amount") or "").replace(".","",1).replace("-","",1).isdigit() else 0
        try:
            row = TransactionRow.model_validate(item)
            if row.currency != "AED":
                raise ValueError("UNSUPPORTED_CURRENCY")
            with connect() as c:
                member = c.execute("SELECT 1 FROM members WHERE id=?", (row.member_id,)).fetchone()
                if not member:
                    raise ValueError("UNKNOWN_MEMBER")
                exists = c.execute("SELECT 1 FROM transactions WHERE partner_id=? AND transaction_id=?",
                                   (partner_id,row.transaction_id)).fetchone()
                if exists:
                    duplicates += 1
                    duplicate_total += row.amount
                    c.execute("INSERT INTO audit_log(event_type,entity_key,details) VALUES(?,?,?)",
                              ("DUPLICATE_SKIPPED", row.transaction_id, json.dumps({"partner":partner_id,"file":file.filename})))
                    continue
                campaign_multiplier = 1.0
                weekend = False
                if row.campaign_id:
                    camp = c.execute("SELECT * FROM campaigns WHERE id=? AND partner_id=? AND active=1",
                                     (row.campaign_id,partner_id)).fetchone()
                    if camp and camp["start_date"] <= row.transaction_date <= camp["end_date"]:
                        campaign_multiplier = camp["earn_multiplier"]
                        weekend = bool(camp["bonus_weekends"])
                points = calculate_points(partner["earn_rate"], row.amount, campaign_multiplier, weekend, row.transaction_date)
                c.execute("""INSERT INTO transactions(partner_id,transaction_id,member_id,amount,currency,points,campaign_id,source_file)
                             VALUES(?,?,?,?,?,?,?,?)""",
                          (partner_id,row.transaction_id,row.member_id,row.amount,row.currency,points,row.campaign_id,file.filename or "upload"))
                c.execute("INSERT INTO audit_log(event_type,entity_key,details) VALUES(?,?,?)",
                          ("POINTS_POSTED",row.transaction_id,json.dumps({"partner":partner_id,"member":row.member_id,"points":points})))
                posted += 1; posted_points += points; posted_total += row.amount
        except Exception as exc:
            rejected += 1
            reason = str(exc)
            if "UNSUPPORTED_CURRENCY" in reason: code = "UNSUPPORTED_CURRENCY"
            elif "UNKNOWN_MEMBER" in reason: code = "UNKNOWN_MEMBER"
            elif "transaction_id" in reason: code = "INVALID_TRANSACTION"
            elif "member_id" in reason: code = "MISSING_MEMBER_ID"
            elif "amount" in reason: code = "INVALID_AMOUNT"
            elif "currency" in reason: code = "INVALID_CURRENCY"
            elif "transaction_date" in reason: code = "INVALID_DATE"
            else: code = "VALIDATION_ERROR"
            try: rejected_total += float(item.get("amount") or 0)
            except Exception: pass
            with connect() as c:
                c.execute("""INSERT INTO rejects(partner_id,transaction_id,source_file,reason_code,details,row_json)
                             VALUES(?,?,?,?,?,?)""",
                          (partner_id,str(item.get("transaction_id") or ""),file.filename or "upload",code,reason,json.dumps(item)))
    discrepancy = round(declared_total - posted_total - rejected_total - duplicate_total, 2)
    with connect() as c:
        c.execute("""INSERT INTO feed_runs(partner_id,source_file,row_count,posted_count,rejected_count,duplicate_count,
                      declared_total,posted_total,rejected_total,duplicate_total,discrepancy) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                  (partner_id,file.filename or "upload",len(rows),posted,rejected,duplicates,declared_total,
                   posted_total,rejected_total,duplicate_total,discrepancy))
    return {"partner_id":partner_id,"source_file":file.filename,"rows":len(rows),"posted":posted,
            "rejected":rejected,"duplicates":duplicates,"posted_points":posted_points,
            "declared_total":round(declared_total,2),"posted_total":round(posted_total,2),
            "rejected_total":round(rejected_total,2),"duplicate_total":round(duplicate_total,2),"discrepancy":discrepancy}

@app.get("/metrics")
def metrics():
    with connect() as c:
        totals = c.execute("""SELECT COALESCE(SUM(row_count),0) rows, COALESCE(SUM(posted_count),0) posted,
          COALESCE(SUM(rejected_count),0) rejected, COALESCE(SUM(duplicate_count),0) duplicates,
          COALESCE(SUM(discrepancy),0) discrepancy FROM feed_runs""").fetchone()
        last = c.execute("SELECT received_at FROM feed_runs ORDER BY id DESC LIMIT 1").fetchone()
    rows = int(totals["rows"]); rejected = int(totals["rejected"])
    reject_rate = round(rejected / rows, 4) if rows else 0.0
    lag_minutes = 0
    if last:
        try: lag_minutes = max(0, int((datetime.utcnow()-datetime.fromisoformat(last["received_at"])).total_seconds()/60))
        except Exception: pass
    alerts = []
    if reject_rate > 0.02: alerts.append("REJECT_RATE_ABOVE_2_PERCENT")
    if abs(float(totals["discrepancy"])) > 0.01: alerts.append("RECONCILIATION_DISCREPANCY")
    return {"rows_received":rows,"posted":int(totals["posted"]),"rejected":rejected,
            "duplicates_skipped":int(totals["duplicates"]),"reject_rate":reject_rate,
            "feed_lag_minutes_since_last_feed":lag_minutes,"net_discrepancy":round(float(totals["discrepancy"]),2),
            "alerts":alerts}

@app.get("/reconciliation")
def reconciliation():
    with connect() as c:
        rows = c.execute("SELECT * FROM feed_runs ORDER BY id DESC").fetchall()
    return {"runs":[dict(r) for r in rows]}

@app.get("/rejects")
def get_rejects(partner_id: str | None = None, limit: int = 100):
    with connect() as c:
        if partner_id:
            rows = c.execute("SELECT * FROM rejects WHERE partner_id=? ORDER BY id DESC LIMIT ?",(partner_id,min(limit,500))).fetchall()
        else:
            rows = c.execute("SELECT * FROM rejects ORDER BY id DESC LIMIT ?",(min(limit,500),)).fetchall()
    return {"rejects":[dict(r) for r in rows]}

@app.get("/members/{member_id}/tier")
def get_tier(member_id: str):
    result = member_summary(member_id)
    if result["points"] == 0:
        with connect() as c:
            exists = c.execute("SELECT 1 FROM members WHERE id=?",(member_id,)).fetchone()
        if not exists: raise HTTPException(404,"Unknown member")
    return result

@app.post("/campaigns/validate")
def campaign_validate(payload: CampaignInput):
    return validate_campaign(payload)

@app.post("/campaigns")
def campaign_create(payload: CampaignInput):
    result = save_campaign(payload)
    if result["status"] == "FAIL": raise HTTPException(422,result)
    return {"saved":True,**result}

@app.post("/triage")
def triage(payload: dict):
    allowed = {"partner_id","source_file","rows","posted","rejected","duplicates","discrepancy","reason_codes","feed_lag_minutes"}
    evidence = {k:v for k,v in payload.items() if k in allowed}
    if not evidence: raise HTTPException(400,"Provide operational evidence fields")
    return generate_triage(evidence)

@app.get("/audit")
def audit(limit: int = 100):
    with connect() as c:
        rows = c.execute("SELECT * FROM audit_log ORDER BY id DESC LIMIT ?",(min(limit,500),)).fetchall()
    return {"events":[dict(r) for r in rows]}
