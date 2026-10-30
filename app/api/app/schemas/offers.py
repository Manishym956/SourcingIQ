from uuid import UUID

from pydantic import BaseModel


class MoneyOut(BaseModel):
    amount: str
    currency: str


class OfferRead(BaseModel):
    supplier_id: UUID
    supplier_name: str
    quotation_id: UUID
    eligible: bool
    exclusion_reasons: list[str]
    landed_cost: MoneyOut | None
    lead_time_days: int | None
    ranking_reasons: list[str]
    cost_breakdown: dict[str, str | bool] | None


class OfferComparison(BaseModel):
    rfq_id: UUID
    data_mode: str
    calculation_version: str
    offers: list[OfferRead]
