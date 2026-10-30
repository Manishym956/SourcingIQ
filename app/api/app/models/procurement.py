import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Rfq(Base):
    __tablename__ = "rfqs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    created_by: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"), nullable=False)
    material: Mapped[str] = mapped_column(String(200), nullable=False)
    specification: Mapped[str] = mapped_column(String(200), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    delivery_location: Mapped[str] = mapped_column(String(300), nullable=False)
    needed_by: Mapped[date] = mapped_column(Date, nullable=False)
    budget_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Supplier(Base):
    __tablename__ = "suppliers"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    verification_status: Mapped[str] = mapped_column(String(64), nullable=False)
    service_regions: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    data_source: Mapped[str] = mapped_column(String(64), nullable=False)
    simulation_profile: Mapped[dict[str, str] | None] = mapped_column(JSONB)
    last_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SupplierCapability(Base):
    __tablename__ = "supplier_capabilities"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    supplier_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("suppliers.id"), nullable=False)
    material: Mapped[str] = mapped_column(String(200), nullable=False)
    specification: Mapped[str] = mapped_column(String(200), nullable=False)
    available_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    lead_time_days: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Quotation(Base):
    __tablename__ = "quotations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    supplier_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("suppliers.id"), nullable=False)
    rfq_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("rfqs.id"))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    freight_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    tax_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    discount_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    tax_included: Mapped[bool | None] = mapped_column(Boolean)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    quoted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_reference: Mapped[str | None] = mapped_column(String(200))


class OfferEvaluation(Base):
    __tablename__ = "offer_evaluations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    rfq_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("rfqs.id"), nullable=False)
    quotation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("quotations.id"), nullable=False
    )
    eligible: Mapped[bool] = mapped_column(Boolean, nullable=False)
    exclusion_reasons: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    normalized_cost: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    calculation_version: Mapped[str] = mapped_column(String(64), nullable=False)
    ranking_reasons: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"

    key: Mapped[str] = mapped_column(String(200), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    response_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SourcingRun(Base):
    __tablename__ = "sourcing_runs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    rfq_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("rfqs.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    workflow_version: Mapped[str] = mapped_column(String(64), nullable=False)
    state: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_code: Mapped[str | None] = mapped_column(String(64))
    created_by: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"), nullable=False)


class Negotiation(Base):
    __tablename__ = "negotiations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    sourcing_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("sourcing_runs.id"), nullable=False
    )
    quotation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("quotations.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    round_count: Mapped[int] = mapped_column(Integer, nullable=False)
    max_rounds: Mapped[int] = mapped_column(Integer, nullable=False)
    policy: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    transcript: Mapped[list[dict[str, object]]] = mapped_column(JSONB, nullable=False)
    final_offer_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("quotations.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PurchaseOrderDraft(Base):
    __tablename__ = "purchase_order_drafts"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    sourcing_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("sourcing_runs.id"), nullable=False
    )
    rfq_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("rfqs.id"), nullable=False)
    quotation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("quotations.id"), nullable=False
    )
    supplier_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("suppliers.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    items: Mapped[list[dict[str, object]]] = mapped_column(JSONB, nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    freight: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    tax: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    discount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    terms: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Approval(Base):
    __tablename__ = "approvals"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    purchase_order_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("purchase_order_drafts.id"), nullable=False
    )
    draft_version: Mapped[int] = mapped_column(Integer, nullable=False)
    actor_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"), nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class WorkflowEvent(Base):
    __tablename__ = "workflow_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("sourcing_runs.id"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_type: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    payload_redacted: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    correlation_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    source_label: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("knowledge_documents.id"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
