import hashlib
import uuid
from datetime import UTC, datetime
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.agent.graph import rank_catalogue
from app.domain.sourcing import (
    CALCULATION_VERSION,
    CatalogueOffer,
    OfferResult,
    RfqSpec,
    money_text,
)
from app.models.procurement import (
    IdempotencyKey,
    OfferEvaluation,
    Quotation,
    Rfq,
    Supplier,
    SupplierCapability,
    User,
)
from app.schemas.offers import MoneyOut, OfferComparison, OfferRead
from app.schemas.rfq import RfqCreate, RfqPage, RfqRead
from app.schemas.supplier import (
    CapabilityRead,
    QuotationRead,
    SupplierPage,
    SupplierRead,
)

DEMO_EMAIL = "buyer@demo.local"


def create_rfq(
    session: Session,
    payload: RfqCreate,
    *,
    raw_body: bytes,
    idempotency_key: str | None,
) -> tuple[int, dict[str, object]]:
    user = _buyer(session)
    if idempotency_key:
        stored = replay_idempotency(session, user, idempotency_key, raw_body)
        if stored is not None:
            return stored
    now = datetime.now(UTC)
    rfq = Rfq(
        id=uuid.uuid4(),
        created_by=user.id,
        material=payload.material,
        specification=payload.specification,
        quantity=payload.quantity,
        unit=payload.unit,
        delivery_location=payload.delivery_location,
        needed_by=payload.needed_by,
        budget_amount=payload.budget.amount if payload.budget else None,
        currency=payload.budget.currency if payload.budget else "INR",
        notes=payload.notes,
        status="validated",
        created_at=now,
    )
    session.add(rfq)
    session.commit()
    body = _rfq_read(rfq).model_dump(mode="json")
    if idempotency_key:
        session.add(
            IdempotencyKey(
                key=idempotency_key,
                user_id=user.id,
                request_hash=request_hash(raw_body),
                status_code=201,
                response_json=body,
                created_at=now,
            )
        )
        session.commit()
    return 201, body


def list_rfqs(session: Session, *, limit: int, offset: int) -> RfqPage:
    user = _buyer(session)
    rows = session.scalars(
        select(Rfq)
        .where(Rfq.created_by == user.id)
        .order_by(Rfq.created_at.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return RfqPage(items=[_rfq_read(row) for row in rows], limit=limit, offset=offset)


def get_rfq(session: Session, rfq_id: uuid.UUID) -> RfqRead:
    user = _buyer(session)
    rfq = session.get(Rfq, rfq_id)
    if rfq is None or rfq.created_by != user.id:
        raise HTTPException(status_code=404, detail="RFQ not found.")
    return _rfq_read(rfq)


def compare_offers(session: Session, rfq_id: uuid.UUID) -> OfferComparison:
    user = _buyer(session)
    rfq = session.get(Rfq, rfq_id)
    if rfq is None or rfq.created_by != user.id:
        raise HTTPException(status_code=404, detail="RFQ not found.")
    offers, _steps = persist_comparison(session, rfq)
    session.commit()
    return OfferComparison(
        rfq_id=rfq.id,
        data_mode="synthetic_demo",
        calculation_version=CALCULATION_VERSION,
        offers=offers,
    )


def persist_comparison(session: Session, rfq: Rfq) -> tuple[list[OfferRead], list[str]]:
    """Replace stored evaluations for this RFQ. Caller commits."""
    spec = RfqSpec(
        material=rfq.material,
        specification=rfq.specification,
        quantity=Decimal(rfq.quantity),
        unit=rfq.unit,
        currency=rfq.currency,
        needed_by=rfq.needed_by,
    )
    as_of = datetime.now(UTC).date()
    ranked, steps = rank_catalogue(spec, _catalogue(session), as_of=as_of)
    now = datetime.now(UTC)
    session.execute(delete(OfferEvaluation).where(OfferEvaluation.rfq_id == rfq.id))
    offers: list[OfferRead] = []
    for item in ranked:
        session.add(
            OfferEvaluation(
                id=uuid.uuid4(),
                rfq_id=rfq.id,
                quotation_id=uuid.UUID(item.quotation_id),
                eligible=item.eligible,
                exclusion_reasons=item.exclusion_reasons,
                normalized_cost=item.landed_cost,
                currency=item.currency,
                calculation_version=CALCULATION_VERSION,
                ranking_reasons=item.ranking_reasons,
                created_at=now,
            )
        )
        offers.append(_offer_read(item))
    return offers, steps


def _offer_read(result: OfferResult) -> OfferRead:
    return OfferRead(
        supplier_id=uuid.UUID(result.supplier_id),
        supplier_name=result.supplier_name,
        quotation_id=uuid.UUID(result.quotation_id),
        eligible=result.eligible,
        exclusion_reasons=result.exclusion_reasons,
        landed_cost=(
            None
            if result.landed_cost is None
            else MoneyOut(amount=money_text(result.landed_cost), currency=result.currency)
        ),
        lead_time_days=result.lead_time_days,
        ranking_reasons=result.ranking_reasons,
        cost_breakdown=result.breakdown,
    )


def list_suppliers(
    session: Session, *, limit: int, offset: int, material: str | None
) -> SupplierPage:
    _buyer(session)
    query = select(Supplier).where(Supplier.status == "active").order_by(Supplier.name)
    if material:
        query = query.where(
            Supplier.id.in_(
                select(SupplierCapability.supplier_id).where(
                    func.lower(SupplierCapability.material) == material.strip().lower()
                )
            )
        )
    rows = session.scalars(query.limit(limit).offset(offset)).all()
    return SupplierPage(
        items=[_supplier_read(session, row) for row in rows],
        limit=limit,
        offset=offset,
    )


def get_supplier(session: Session, supplier_id: uuid.UUID) -> SupplierRead:
    _buyer(session)
    supplier = session.get(Supplier, supplier_id)
    if supplier is None:
        raise HTTPException(status_code=404, detail="Supplier not found.")
    return _supplier_read(session, supplier)


def _buyer(session: Session) -> User:
    user = session.scalar(select(User).where(User.email == DEMO_EMAIL))
    if user is None:
        raise HTTPException(status_code=401, detail="Demo buyer is not seeded.")
    return user


def replay_idempotency(
    session: Session, user: User, key: str, raw_body: bytes
) -> tuple[int, dict[str, object]] | None:
    if len(key) > 200:
        raise HTTPException(status_code=422, detail="Idempotency-Key is too long.")
    existing = session.get(IdempotencyKey, key)
    if existing is None:
        return None
    if existing.user_id != user.id or existing.request_hash != request_hash(raw_body):
        raise HTTPException(
            status_code=409,
            detail="This idempotency key was already used with a different request.",
        )
    return existing.status_code, existing.response_json


def request_hash(raw_body: bytes) -> str:
    return hashlib.sha256(raw_body).hexdigest()


def _catalogue(session: Session) -> list[CatalogueOffer]:
    offers: list[CatalogueOffer] = []
    suppliers = session.scalars(select(Supplier).where(Supplier.status == "active")).all()
    for supplier in suppliers:
        capability = session.scalar(
            select(SupplierCapability).where(SupplierCapability.supplier_id == supplier.id)
        )
        quotation = session.scalar(
            select(Quotation).where(
                Quotation.supplier_id == supplier.id,
                Quotation.rfq_id.is_(None),
            )
        )
        if capability is None or quotation is None:
            continue
        valid_until = quotation.valid_until.date() if quotation.valid_until else None
        offers.append(
            CatalogueOffer(
                supplier_id=str(supplier.id),
                supplier_name=supplier.name,
                quotation_id=str(quotation.id),
                material=capability.material,
                specification=capability.specification,
                available_quantity=Decimal(capability.available_quantity),
                capability_unit=capability.unit,
                lead_time_days=capability.lead_time_days,
                unit_price=Decimal(quotation.unit_price),
                currency=quotation.currency,
                quote_quantity=Decimal(quotation.quantity),
                quote_unit=quotation.unit,
                freight_amount=_optional_decimal(quotation.freight_amount),
                tax_amount=_optional_decimal(quotation.tax_amount),
                discount_amount=_optional_decimal(quotation.discount_amount),
                tax_included=quotation.tax_included,
                valid_until=valid_until,
            )
        )
    return offers


def _optional_decimal(value: Decimal | None) -> Decimal | None:
    if value is None:
        return None
    return Decimal(value)


def _rfq_read(rfq: Rfq) -> RfqRead:
    return RfqRead(
        id=rfq.id,
        material=rfq.material,
        specification=rfq.specification,
        quantity=_plain(rfq.quantity),
        unit=rfq.unit,
        delivery_location=rfq.delivery_location,
        needed_by=rfq.needed_by,
        budget_amount=None if rfq.budget_amount is None else money_text(Decimal(rfq.budget_amount)),
        currency=rfq.currency,
        notes=rfq.notes,
        status=rfq.status,
        created_at=rfq.created_at,
    )


def _supplier_read(session: Session, supplier: Supplier) -> SupplierRead:
    capabilities = session.scalars(
        select(SupplierCapability).where(SupplierCapability.supplier_id == supplier.id)
    ).all()
    quotations = session.scalars(
        select(Quotation).where(Quotation.supplier_id == supplier.id)
    ).all()
    return SupplierRead(
        id=supplier.id,
        name=supplier.name,
        status=supplier.status,
        verification_status=supplier.verification_status,
        service_regions=list(supplier.service_regions),
        data_source=supplier.data_source,
        last_updated_at=supplier.last_updated_at,
        capabilities=[
            CapabilityRead(
                material=item.material,
                specification=item.specification,
                available_quantity=_plain(item.available_quantity),
                unit=item.unit,
                lead_time_days=item.lead_time_days,
            )
            for item in capabilities
        ],
        quotations=[
            QuotationRead(
                id=item.id,
                unit_price=money_text(Decimal(item.unit_price)),
                currency=item.currency,
                quantity=_plain(item.quantity),
                unit=item.unit,
                freight_amount=_money_or_none(item.freight_amount),
                tax_amount=_money_or_none(item.tax_amount),
                discount_amount=_money_or_none(item.discount_amount),
                tax_included=item.tax_included,
                source_type=item.source_type,
                source_reference=item.source_reference,
            )
            for item in quotations
        ],
    )


def _plain(value: Decimal) -> str:
    text = format(Decimal(value), "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def _money_or_none(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return money_text(Decimal(value))
