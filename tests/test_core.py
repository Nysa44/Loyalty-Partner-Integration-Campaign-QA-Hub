import io, json, pytest
from fastapi.testclient import TestClient
from app.main import app
from app.loyalty import tier_for, calculate_points
from app.schemas import CampaignInput
from app.campaigns import validate_campaign
from app.triage import generate_triage

client = TestClient(app)

def test_health():
    assert client.get("/health").json()["status"] == "ok"

def test_tier_thresholds():
    assert tier_for(0) == "Blue"
    assert tier_for(1000) == "Silver"
    assert tier_for(5000) == "Gold"
    assert tier_for(15000) == "Platinum"

def test_points_and_weekend_bonus():
    assert calculate_points(2, 100) == 200
    assert calculate_points(1, 100, weekend_bonus=True, transaction_date="2026-11-21") == 200

def test_ingest_and_idempotent_reupload():
    data = [{"transaction_id":"T1","member_id":"M0001","amount":100,"currency":"AED","transaction_date":"2026-11-20"}]
    payload = json.dumps(data).encode()
    first = client.post("/partners/hotelco/ingest", files={"file":("feed.json",payload,"application/json")})
    second = client.post("/partners/hotelco/ingest", files={"file":("feed.json",payload,"application/json")})
    assert first.status_code == 200 and first.json()["posted"] == 1
    assert second.status_code == 200 and second.json()["duplicates"] == 1
    assert client.get("/members/M0001/tier").json()["points"] == 200

def test_reject_invalid_currency():
    data = [{"transaction_id":"T2","member_id":"M0001","amount":100,"currency":"USD","transaction_date":"2026-11-20"}]
    res = client.post("/partners/hotelco/ingest", files={"file":("feed.json",json.dumps(data).encode(),"application/json")})
    assert res.json()["rejected"] == 1
    assert client.get("/rejects").json()["rejects"][0]["reason_code"] == "UNSUPPORTED_CURRENCY"

def test_unknown_member_rejected():
    data = [{"transaction_id":"T3","member_id":"NOPE","amount":100,"currency":"AED","transaction_date":"2026-11-20"}]
    res = client.post("/partners/hotelco/ingest", files={"file":("feed.json",json.dumps(data).encode(),"application/json")})
    assert res.json()["rejected"] == 1

def test_campaign_end_before_start_fails():
    p = CampaignInput(id="C1",partner_id="hotelco",name="Bad",start_date="2026-12-20",end_date="2026-12-01",budget_cap=1000,earn_multiplier=2)
    assert "END_BEFORE_START" in validate_campaign(p)["errors"]

def test_campaign_missing_budget_fails():
    p = CampaignInput(id="C1",partner_id="hotelco",name="Bad",start_date="2026-12-01",end_date="2026-12-20",budget_cap=None,earn_multiplier=2)
    assert "MISSING_OR_INVALID_BUDGET_CAP" in validate_campaign(p)["errors"]

def test_campaign_multiplier_limit():
    p = CampaignInput(id="C1",partner_id="hotelco",name="Bad",start_date="2026-12-01",end_date="2026-12-20",budget_cap=1000,earn_multiplier=8)
    assert "EARN_MULTIPLIER_OUT_OF_RANGE" in validate_campaign(p)["errors"]

def test_campaign_overlap():
    from app.db import connect
    with connect() as c:
        c.execute("INSERT INTO campaigns VALUES('C0','hotelco','Existing','2026-12-05','2026-12-15',1000,2,0,1)")
    p = CampaignInput(id="C1",partner_id="hotelco",name="Overlap",start_date="2026-12-10",end_date="2026-12-20",budget_cap=1000,earn_multiplier=2)
    assert any(x.startswith("OVERLAPPING_CAMPAIGN") for x in validate_campaign(p)["errors"])

def test_metrics_and_reconciliation():
    data = [{"transaction_id":"T4","member_id":"M0001","amount":100,"currency":"AED","transaction_date":"2026-11-20"}]
    client.post("/partners/hotelco/ingest", files={"file":("feed.json",json.dumps(data).encode(),"application/json")})
    metrics = client.get("/metrics").json()
    assert metrics["posted"] == 1
    assert client.get("/reconciliation").json()["runs"][0]["posted_count"] == 1
    assert abs(client.get("/reconciliation").json()["runs"][0]["discrepancy"]) < 0.01

def test_triage_fallback_without_key(monkeypatch):
    import app.triage
    monkeypatch.setattr(app.triage, "LLM_API_KEY", "")
    result = generate_triage({"partner_id":"hotelco","rejected":2,"duplicates":1,"discrepancy":0})
    assert result["source"] == "template_fallback"
    assert result["needs_human_review"] is True
