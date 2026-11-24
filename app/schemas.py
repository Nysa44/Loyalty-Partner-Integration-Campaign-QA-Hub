from pydantic import BaseModel, Field, ConfigDict
from typing import Optional

class TransactionRow(BaseModel):
    model_config = ConfigDict(extra="ignore")
    transaction_id: str = Field(min_length=1, max_length=100)
    member_id: str = Field(min_length=1, max_length=100)
    amount: float = Field(gt=0)
    currency: str = Field(min_length=3, max_length=3)
    transaction_date: str = Field(min_length=10, max_length=10)
    campaign_id: Optional[str] = None

class CampaignInput(BaseModel):
    id: str
    partner_id: str
    name: str
    start_date: str
    end_date: str
    budget_cap: Optional[float] = None
    earn_multiplier: float
    bonus_weekends: bool = False
    active: bool = True

class IngestResult(BaseModel):
    source_file: str
    rows: int
    posted: int
    rejected: int
    duplicates: int
    posted_points: int
    discrepancy: float
