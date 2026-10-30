from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class CapabilityRead(BaseModel):
    material: str
    specification: str
    available_quantity: str
    unit: str
    lead_time_days: int


class QuotationRead(BaseModel):
    id: UUID
    unit_price: str
    currency: str
    quantity: str
    unit: str
    freight_amount: str | None
    tax_amount: str | None
    discount_amount: str | None
    tax_included: bool | None
    source_type: str
    source_reference: str | None


class SupplierRead(BaseModel):
    id: UUID
    name: str
    status: str
    verification_status: str
    service_regions: list[str]
    data_source: str
    last_updated_at: datetime
    capabilities: list[CapabilityRead]
    quotations: list[QuotationRead]


class SupplierPage(BaseModel):
    items: list[SupplierRead]
    limit: int
    offset: int
