from datetime import date, datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

SUPPORTED_CURRENCY = "INR"
SUPPORTED_UNIT = "tonne"


class MoneyIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    amount: Decimal
    currency: str

    @field_validator("amount")
    @classmethod
    def positive_amount(cls, value: Decimal) -> Decimal:
        if value <= 0:
            raise ValueError("Must be greater than zero.")
        return value

    @field_validator("currency")
    @classmethod
    def supported_currency(cls, value: str) -> str:
        if value != SUPPORTED_CURRENCY:
            raise ValueError("Only INR is supported.")
        return value


class RfqCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    material: Annotated[str, Field(min_length=1, max_length=200)]
    specification: Annotated[str, Field(min_length=1, max_length=200)]
    quantity: Decimal
    unit: str
    delivery_location: Annotated[str, Field(min_length=1, max_length=300)]
    needed_by: date
    budget: MoneyIn | None = None
    notes: Annotated[str | None, Field(max_length=2000)] = None

    @field_validator("material", "specification", "delivery_location")
    @classmethod
    def strip_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Must not be empty.")
        return stripped

    @field_validator("quantity")
    @classmethod
    def positive_quantity(cls, value: Decimal) -> Decimal:
        if value <= 0:
            raise ValueError("Must be greater than zero.")
        return value

    @field_validator("unit")
    @classmethod
    def supported_unit(cls, value: str) -> str:
        if value != SUPPORTED_UNIT:
            raise ValueError("Supported unit is tonne.")
        return value

    @field_validator("needed_by")
    @classmethod
    def deadline_not_past(cls, value: date) -> date:
        if value < datetime.now().astimezone().date():
            raise ValueError("Needed-by date cannot be in the past.")
        return value


class RfqRead(BaseModel):
    id: UUID
    material: str
    specification: str
    quantity: str
    unit: str
    delivery_location: str
    needed_by: date
    budget_amount: str | None
    currency: str
    notes: str | None
    status: str
    created_at: datetime


class RfqPage(BaseModel):
    items: list[RfqRead]
    limit: int
    offset: int
