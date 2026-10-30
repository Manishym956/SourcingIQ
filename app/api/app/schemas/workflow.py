from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.domain.negotiation import MAX_NEGOTIATION_ROUNDS
from app.domain.sourcing import quantize_money
from app.schemas.offers import OfferRead


class SourcingRunCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rfq_id: UUID


class SourcingRunRead(BaseModel):
    id: UUID
    rfq_id: UUID
    status: str
    workflow_version: str
    started_at: str
    finished_at: str | None
    error_code: str | None
    eligible_count: int
    data_mode: str
    orchestrator: str
    steps: list[str]


class SourcingRunPage(BaseModel):
    items: list[SourcingRunRead]
    limit: int
    offset: int


class RunOffersRead(BaseModel):
    run_id: UUID
    rfq_id: UUID
    status: str
    data_mode: str
    calculation_version: str
    offers: list[OfferRead]


class WorkflowEventRead(BaseModel):
    id: UUID
    event_type: str
    actor_type: str
    payload: dict[str, object]
    correlation_id: UUID
    created_at: str


class WorkflowEventPage(BaseModel):
    items: list[WorkflowEventRead]
    limit: int
    offset: int


class NegotiationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    quotation_id: UUID
    max_rounds: int
    floor_unit_price: Decimal
    ceiling_unit_price: Decimal

    @field_validator("max_rounds")
    @classmethod
    def capped_rounds(cls, value: int) -> int:
        if value < 1 or value > MAX_NEGOTIATION_ROUNDS:
            raise ValueError(f"Maximum rounds must be from 1 to {MAX_NEGOTIATION_ROUNDS}.")
        return value

    @field_validator("floor_unit_price", "ceiling_unit_price")
    @classmethod
    def positive_price(cls, value: Decimal) -> Decimal:
        if value <= 0:
            raise ValueError("Must be greater than zero.")
        return quantize_money(value)

    @model_validator(mode="after")
    def floor_not_above_ceiling(self) -> "NegotiationCreate":
        if self.floor_unit_price > self.ceiling_unit_price:
            raise ValueError("Floor unit price cannot exceed the ceiling.")
        return self


class NegotiationTurn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    proposed_unit_price: Decimal
    message: str | None = Field(default=None, max_length=500)

    @field_validator("proposed_unit_price")
    @classmethod
    def positive_offer(cls, value: Decimal) -> Decimal:
        if value <= 0:
            raise ValueError("Must be greater than zero.")
        return quantize_money(value)


class NegotiationRead(BaseModel):
    id: UUID
    sourcing_run_id: UUID
    quotation_id: UUID
    status: str
    round_count: int
    max_rounds: int
    policy: dict[str, str | int]
    transcript: list[dict[str, object]]
    final_offer_id: UUID | None
    simulation: bool
    data_mode: str


class DraftCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sourcing_run_id: UUID
    quotation_id: UUID


class DecisionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    draft_version: int
    reason: str | None = Field(default=None, max_length=1000)

    @field_validator("draft_version")
    @classmethod
    def positive_version(cls, value: int) -> int:
        if value < 1:
            raise ValueError("Draft version must be at least 1.")
        return value


class PurchaseOrderRead(BaseModel):
    id: UUID
    sourcing_run_id: UUID
    rfq_id: UUID
    quotation_id: UUID
    supplier_id: UUID
    supplier_name: str
    status: str
    items: list[dict[str, object]]
    subtotal: str
    freight: str
    tax: str
    discount: str
    total: str
    currency: str
    terms: dict[str, object]
    version: int
    notice: str
    created_at: str
