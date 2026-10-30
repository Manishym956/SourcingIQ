"""Sourcing runs, simulated negotiation, and draft purchase orders."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.domain.negotiation import (
    NegotiationBounds,
    SupplierSimulation,
    apply_turn,
    price_policy_error,
)
from app.domain.sourcing import (
    CALCULATION_VERSION,
    CatalogueOffer,
    OfferResult,
    RfqSpec,
    evaluate_offer,
    money_text,
)
from app.models.procurement import (
    Approval,
    IdempotencyKey,
    Negotiation,
    PurchaseOrderDraft,
    Quotation,
    Rfq,
    SourcingRun,
    Supplier,
    SupplierCapability,
    User,
    WorkflowEvent,
)
from app.schemas.offers import OfferRead
from app.schemas.workflow import (
    DecisionCreate,
    DraftCreate,
    NegotiationCreate,
    NegotiationRead,
    NegotiationTurn,
    PurchaseOrderRead,
    RunOffersRead,
    SourcingRunCreate,
    SourcingRunPage,
    SourcingRunRead,
    WorkflowEventPage,
    WorkflowEventRead,
)
from app.services.procurement import persist_comparison, replay_idempotency, request_hash

WORKFLOW_VERSION = "sourcing-workflow-v1"
TERMINAL = {"approved_draft", "rejected", "cancelled", "failed"}
OPEN_FOR_DRAFT = {"comparing", "negotiating"}
NOTICE = "Draft — not submitted."


def start_run(
    session: Session,
    payload: SourcingRunCreate,
    *,
    actor_email: str,
    raw_body: bytes,
    idempotency_key: str | None,
    correlation_id: uuid.UUID,
) -> tuple[int, dict[str, object]]:
    user = _user(session, actor_email)
    _require_buyer(user)
    if idempotency_key:
        stored = replay_idempotency(session, user, idempotency_key, raw_body)
        if stored is not None:
            return stored
    rfq = session.get(Rfq, payload.rfq_id)
    if rfq is None or rfq.created_by != user.id:
        raise HTTPException(status_code=404, detail="RFQ not found.")
    if rfq.status != "validated":
        raise HTTPException(status_code=409, detail="RFQ is not ready for sourcing.")
    now = datetime.now(UTC)
    offers, steps = persist_comparison(session, rfq)
    run = SourcingRun(
        id=uuid.uuid4(),
        rfq_id=rfq.id,
        status="comparing",
        workflow_version=WORKFLOW_VERSION,
        state={
            "data_mode": "synthetic_demo",
            "calculation_version": CALCULATION_VERSION,
            "offers": [item.model_dump(mode="json") for item in offers],
            "orchestrator": "langgraph",
            "steps": steps,
        },
        started_at=now,
        finished_at=None,
        error_code=None,
        created_by=user.id,
    )
    session.add(run)
    _event(
        session,
        run.id,
        "sourcing_run.compared",
        user.id,
        {"status": "comparing", "eligible_count": _eligible_count(offers)},
        correlation_id,
        now,
    )
    session.commit()
    body = _run_read(run).model_dump(mode="json")
    _remember(session, user, idempotency_key, raw_body, 201, body, now)
    return 201, body


def get_run(session: Session, run_id: uuid.UUID, *, actor_email: str) -> SourcingRunRead:
    run = _visible_run(session, _user(session, actor_email), run_id)
    return _run_read(run)


def list_runs(session: Session, *, actor_email: str, limit: int, offset: int) -> SourcingRunPage:
    user = _user(session, actor_email)
    query = select(SourcingRun).order_by(SourcingRun.started_at.desc())
    if user.role == "buyer":
        query = query.where(SourcingRun.created_by == user.id)
    rows = session.scalars(query.limit(limit).offset(offset)).all()
    return SourcingRunPage(items=[_run_read(row) for row in rows], limit=limit, offset=offset)


def list_events(
    session: Session,
    run_id: uuid.UUID,
    *,
    actor_email: str,
    limit: int,
    offset: int,
) -> WorkflowEventPage:
    run = _visible_run(session, _user(session, actor_email), run_id)
    rows = session.scalars(
        select(WorkflowEvent)
        .where(WorkflowEvent.workflow_id == run.id)
        .order_by(WorkflowEvent.created_at.asc())
        .limit(limit)
        .offset(offset)
    ).all()
    return WorkflowEventPage(
        items=[
            WorkflowEventRead(
                id=row.id,
                event_type=row.event_type,
                actor_type=row.actor_type,
                payload=row.payload_redacted,
                correlation_id=row.correlation_id,
                created_at=row.created_at.isoformat(),
            )
            for row in rows
        ],
        limit=limit,
        offset=offset,
    )


def run_offers(session: Session, run_id: uuid.UUID, *, actor_email: str) -> RunOffersRead:
    run = _visible_run(session, _user(session, actor_email), run_id)
    state = run.state
    offers = [OfferRead.model_validate(item) for item in state["offers"]]
    return RunOffersRead(
        run_id=run.id,
        rfq_id=run.rfq_id,
        status=run.status,
        data_mode="synthetic_demo",
        calculation_version=str(state["calculation_version"]),
        offers=offers,
    )


def start_negotiation(
    session: Session,
    run_id: uuid.UUID,
    payload: NegotiationCreate,
    *,
    actor_email: str,
    raw_body: bytes,
    idempotency_key: str | None,
    correlation_id: uuid.UUID,
) -> tuple[int, dict[str, object]]:
    if not get_settings().enable_negotiation_simulator:
        raise HTTPException(status_code=403, detail="Negotiation simulation is disabled.")
    user = _user(session, actor_email)
    _require_buyer(user)
    if idempotency_key:
        stored = replay_idempotency(session, user, idempotency_key, raw_body)
        if stored is not None:
            return stored
    run = _visible_run(session, user, run_id)
    _ensure_open(run)
    if run.status not in OPEN_FOR_DRAFT:
        raise HTTPException(status_code=409, detail="This run cannot start a negotiation.")
    existing = session.scalar(select(Negotiation).where(Negotiation.sourcing_run_id == run.id))
    if existing is not None:
        raise HTTPException(status_code=409, detail="This run already has a negotiation.")
    snapshot = _snapshot_offer(run, payload.quotation_id)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="Quotation is not part of this run.")
    if not snapshot.eligible:
        raise HTTPException(status_code=409, detail="Only an eligible quotation can be negotiated.")
    quotation = session.get(Quotation, payload.quotation_id)
    supplier = session.get(Supplier, quotation.supplier_id) if quotation is not None else None
    if quotation is None or supplier is None:
        raise HTTPException(status_code=404, detail="Quotation is not part of this run.")
    _simulation_profile(supplier, Decimal(quotation.unit_price))
    now = datetime.now(UTC)
    negotiation = Negotiation(
        id=uuid.uuid4(),
        sourcing_run_id=run.id,
        quotation_id=quotation.id,
        status="open",
        round_count=0,
        max_rounds=payload.max_rounds,
        policy={
            "max_rounds": payload.max_rounds,
            "floor_unit_price": money_text(payload.floor_unit_price),
            "ceiling_unit_price": money_text(payload.ceiling_unit_price),
            "currency": "INR",
        },
        transcript=[],
        final_offer_id=None,
        created_at=now,
        updated_at=now,
    )
    run.status = "negotiating"
    session.add(negotiation)
    _event(
        session,
        run.id,
        "negotiation.started",
        user.id,
        {
            "negotiation_id": str(negotiation.id),
            "max_rounds": payload.max_rounds,
            "simulation": True,
        },
        correlation_id,
        now,
    )
    session.commit()
    body = _negotiation_read(negotiation).model_dump(mode="json")
    _remember(session, user, idempotency_key, raw_body, 201, body, now)
    return 201, body


def negotiation_turn(
    session: Session,
    negotiation_id: uuid.UUID,
    payload: NegotiationTurn,
    *,
    actor_email: str,
    correlation_id: uuid.UUID,
) -> NegotiationRead:
    if not get_settings().enable_negotiation_simulator:
        raise HTTPException(status_code=403, detail="Negotiation simulation is disabled.")
    user = _user(session, actor_email)
    _require_buyer(user)
    negotiation = _visible_negotiation(session, user, negotiation_id)
    if negotiation.status != "open":
        raise HTTPException(status_code=409, detail="This negotiation is closed.")
    bounds = _bounds(negotiation)
    policy_error = price_policy_error(bounds, payload.proposed_unit_price)
    if policy_error is not None:
        raise HTTPException(status_code=422, detail=policy_error)
    quotation = session.get(Quotation, negotiation.quotation_id)
    supplier = session.get(Supplier, quotation.supplier_id) if quotation is not None else None
    if quotation is None or supplier is None:
        raise HTTPException(status_code=409, detail="The negotiated quotation is missing.")
    profile = _simulation_profile(supplier, Decimal(quotation.unit_price))
    outcome = apply_turn(bounds, profile, negotiation.round_count, payload.proposed_unit_price)
    now = datetime.now(UTC)
    entry: dict[str, object] = {
        "round": outcome.round_count,
        "buyer_unit_price": money_text(outcome.buyer_unit_price),
        "supplier_unit_price": money_text(outcome.supplier_unit_price),
        "untrusted_buyer_text": (payload.message or "").strip(),
        "reason": outcome.reason,
        "simulation": True,
        "status": outcome.status,
    }
    negotiation.round_count = outcome.round_count
    negotiation.transcript = [*negotiation.transcript, entry]
    negotiation.status = outcome.status
    negotiation.updated_at = now
    if outcome.accepted:
        accepted = _accept_price(session, negotiation, quotation, outcome.buyer_unit_price, now)
        if accepted is None:
            raise HTTPException(
                status_code=409,
                detail="Simulated price is not an eligible offer.",
            )
        negotiation.final_offer_id = accepted.id
    run = session.get(SourcingRun, negotiation.sourcing_run_id)
    if run is not None:
        _event(
            session,
            run.id,
            "negotiation.turn",
            user.id,
            {
                "negotiation_id": str(negotiation.id),
                "round": outcome.round_count,
                "status": outcome.status,
                "simulation": True,
            },
            correlation_id,
            now,
        )
    session.commit()
    return _negotiation_read(negotiation)


def get_negotiation(
    session: Session, negotiation_id: uuid.UUID, *, actor_email: str
) -> NegotiationRead:
    negotiation = _visible_negotiation(session, _user(session, actor_email), negotiation_id)
    return _negotiation_read(negotiation)


def get_run_negotiation(
    session: Session, run_id: uuid.UUID, *, actor_email: str
) -> NegotiationRead | None:
    run = _visible_run(session, _user(session, actor_email), run_id)
    negotiation = session.scalar(select(Negotiation).where(Negotiation.sourcing_run_id == run.id))
    if negotiation is None:
        return None
    return _negotiation_read(negotiation)


def get_run_draft(
    session: Session, run_id: uuid.UUID, *, actor_email: str
) -> PurchaseOrderRead | None:
    user = _user(session, actor_email)
    run = _visible_run(session, user, run_id)
    draft = session.scalar(
        select(PurchaseOrderDraft)
        .where(PurchaseOrderDraft.sourcing_run_id == run.id)
        .order_by(PurchaseOrderDraft.created_at.desc())
    )
    if draft is None:
        return None
    supplier = session.get(Supplier, draft.supplier_id)
    return _po_read(draft, supplier.name if supplier is not None else "")


def create_draft(
    session: Session,
    payload: DraftCreate,
    *,
    actor_email: str,
    raw_body: bytes,
    idempotency_key: str | None,
    correlation_id: uuid.UUID,
) -> tuple[int, dict[str, object]]:
    user = _user(session, actor_email)
    _require_buyer(user)
    if idempotency_key:
        stored = replay_idempotency(session, user, idempotency_key, raw_body)
        if stored is not None:
            return stored
    run = _visible_run(session, user, payload.sourcing_run_id)
    _ensure_open(run)
    if run.status not in OPEN_FOR_DRAFT:
        raise HTTPException(status_code=409, detail="This run cannot create a draft.")
    waiting = session.scalar(
        select(PurchaseOrderDraft).where(
            PurchaseOrderDraft.sourcing_run_id == run.id,
            PurchaseOrderDraft.status == "awaiting_review",
        )
    )
    if waiting is not None:
        raise HTTPException(status_code=409, detail="A draft is already awaiting review.")
    quotation = _draft_quotation(session, run, payload.quotation_id)
    rfq = session.get(Rfq, run.rfq_id)
    if rfq is None or quotation is None:
        raise HTTPException(status_code=404, detail="Quotation is not part of this run.")
    result = _evaluate_quotation(session, rfq, quotation)
    if not result.eligible or result.landed_cost is None or result.breakdown is None:
        raise HTTPException(status_code=409, detail="Only an eligible quotation can be drafted.")
    supplier = session.get(Supplier, quotation.supplier_id)
    if supplier is None:
        raise HTTPException(status_code=404, detail="Supplier not found.")
    now = datetime.now(UTC)
    draft = PurchaseOrderDraft(
        id=uuid.uuid4(),
        sourcing_run_id=run.id,
        rfq_id=rfq.id,
        quotation_id=quotation.id,
        supplier_id=supplier.id,
        status="awaiting_review",
        items=[
            {
                "material": rfq.material,
                "specification": rfq.specification,
                "quantity": _plain(rfq.quantity),
                "unit": rfq.unit,
                "unit_price": money_text(Decimal(quotation.unit_price)),
                "line_subtotal": result.breakdown["material_subtotal"],
            }
        ],
        subtotal=Decimal(str(result.breakdown["material_subtotal"])),
        freight=Decimal(str(result.breakdown["freight"])),
        tax=Decimal(str(result.breakdown["tax"])),
        discount=Decimal(str(result.breakdown["discount"])),
        total=result.landed_cost,
        currency=result.currency,
        terms={
            "notice": NOTICE,
            "external_submission": False,
            "data_mode": "synthetic_demo",
            "simulation": quotation.source_type == "simulation",
        },
        version=1,
        created_by=user.id,
        created_at=now,
        updated_at=now,
    )
    run.status = "awaiting_review"
    session.add(draft)
    _event(
        session,
        run.id,
        "purchase_order.drafted",
        user.id,
        {
            "purchase_order_id": str(draft.id),
            "version": 1,
            "external_submission": False,
        },
        correlation_id,
        now,
    )
    session.commit()
    body = _po_read(draft, supplier.name).model_dump(mode="json")
    _remember(session, user, idempotency_key, raw_body, 201, body, now)
    return 201, body


def get_draft(session: Session, po_id: uuid.UUID, *, actor_email: str) -> PurchaseOrderRead:
    user = _user(session, actor_email)
    draft = _visible_draft(session, user, po_id)
    supplier = session.get(Supplier, draft.supplier_id)
    name = supplier.name if supplier is not None else ""
    return _po_read(draft, name)


def decide_draft(
    session: Session,
    po_id: uuid.UUID,
    payload: DecisionCreate,
    *,
    action: str,
    actor_email: str,
    correlation_id: uuid.UUID,
) -> PurchaseOrderRead:
    user = _user(session, actor_email)
    _require_approver(user)
    if action == "reject" and not (payload.reason and payload.reason.strip()):
        raise HTTPException(status_code=422, detail="A rejection reason is required.")
    draft = _visible_draft(session, user, po_id)
    if payload.draft_version != draft.version:
        raise HTTPException(status_code=409, detail="Draft version does not match.")
    if draft.status != "awaiting_review":
        raise HTTPException(status_code=409, detail="This draft is already decided.")
    rfq = session.get(Rfq, draft.rfq_id)
    if action == "approve" and rfq is not None and rfq.budget_amount is not None:
        if draft.total > Decimal(rfq.budget_amount):
            raise HTTPException(status_code=409, detail="Landed cost exceeds the RFQ budget.")
    now = datetime.now(UTC)
    draft.status = "approved_draft" if action == "approve" else "rejected"
    draft.updated_at = now
    session.add(
        Approval(
            id=uuid.uuid4(),
            purchase_order_id=draft.id,
            draft_version=draft.version,
            actor_id=user.id,
            action=action,
            reason=None if payload.reason is None else payload.reason.strip(),
            created_at=now,
        )
    )
    run = session.get(SourcingRun, draft.sourcing_run_id)
    if run is not None:
        run.status = draft.status
        run.finished_at = now
        _event(
            session,
            run.id,
            f"purchase_order.{action}d" if action == "approve" else "purchase_order.rejected",
            user.id,
            {
                "purchase_order_id": str(draft.id),
                "draft_version": draft.version,
                "external_submission": False,
            },
            correlation_id,
            now,
        )
    session.commit()
    supplier = session.get(Supplier, draft.supplier_id)
    return _po_read(draft, supplier.name if supplier is not None else "")


def _accept_price(
    session: Session,
    negotiation: Negotiation,
    source: Quotation,
    unit_price: Decimal,
    now: datetime,
) -> Quotation | None:
    run = session.get(SourcingRun, negotiation.sourcing_run_id)
    if run is None:
        return None
    rfq = session.get(Rfq, run.rfq_id)
    if rfq is None:
        return None
    accepted = Quotation(
        id=uuid.uuid4(),
        supplier_id=source.supplier_id,
        rfq_id=rfq.id,
        unit_price=unit_price,
        currency=source.currency,
        quantity=Decimal(rfq.quantity),
        unit=source.unit,
        freight_amount=source.freight_amount,
        tax_amount=source.tax_amount,
        discount_amount=source.discount_amount,
        tax_included=source.tax_included,
        valid_until=source.valid_until,
        quoted_at=now,
        source_type="simulation",
        source_reference=str(negotiation.id),
    )
    result = _evaluate_quotation(session, rfq, accepted)
    if not result.eligible or result.landed_cost is None:
        return None
    session.add(accepted)
    session.flush()
    return accepted


def _evaluate_quotation(session: Session, rfq: Rfq, quotation: Quotation) -> OfferResult:
    supplier = session.get(Supplier, quotation.supplier_id)
    capability = session.scalar(
        select(SupplierCapability).where(SupplierCapability.supplier_id == quotation.supplier_id)
    )
    if supplier is None or capability is None:
        raise HTTPException(status_code=409, detail="Supplier capability is missing.")
    valid_until = quotation.valid_until.date() if quotation.valid_until else None
    offer = CatalogueOffer(
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
        freight_amount=_optional(quotation.freight_amount),
        tax_amount=_optional(quotation.tax_amount),
        discount_amount=_optional(quotation.discount_amount),
        tax_included=quotation.tax_included,
        valid_until=valid_until,
    )
    spec = RfqSpec(
        material=rfq.material,
        specification=rfq.specification,
        quantity=Decimal(rfq.quantity),
        unit=rfq.unit,
        currency=rfq.currency,
        needed_by=rfq.needed_by,
    )
    return evaluate_offer(spec, offer, as_of=datetime.now(UTC).date())


def _draft_quotation(
    session: Session, run: SourcingRun, quotation_id: uuid.UUID
) -> Quotation | None:
    snapshot = _snapshot_offer(run, quotation_id)
    if snapshot is not None:
        if not snapshot.eligible:
            raise HTTPException(
                status_code=409, detail="Only an eligible quotation can be drafted."
            )
        return session.get(Quotation, quotation_id)
    negotiation = session.scalar(select(Negotiation).where(Negotiation.sourcing_run_id == run.id))
    if (
        negotiation is not None
        and negotiation.status == "accepted"
        and negotiation.final_offer_id == quotation_id
    ):
        return session.get(Quotation, quotation_id)
    raise HTTPException(status_code=404, detail="Quotation is not part of this run.")


def _snapshot_offer(run: SourcingRun, quotation_id: uuid.UUID) -> OfferRead | None:
    for item in run.state["offers"]:
        offer = OfferRead.model_validate(item)
        if offer.quotation_id == quotation_id:
            return offer
    return None


def _simulation_profile(supplier: Supplier, list_price: Decimal) -> SupplierSimulation:
    raw = supplier.simulation_profile or {}
    try:
        profile = SupplierSimulation(
            list_unit_price=list_price,
            minimum_unit_price=Decimal(str(raw["minimum_unit_price"])),
            concession_per_round=Decimal(str(raw["concession_per_round"])),
        )
    except (KeyError, ArithmeticError, ValueError) as exc:
        raise HTTPException(
            status_code=409,
            detail="This supplier has no simulation profile.",
        ) from exc
    if profile.minimum_unit_price <= 0 or profile.concession_per_round < 0:
        raise HTTPException(status_code=409, detail="This supplier has no simulation profile.")
    if profile.minimum_unit_price > profile.list_unit_price:
        raise HTTPException(status_code=409, detail="This supplier has no simulation profile.")
    return profile


def _bounds(negotiation: Negotiation) -> NegotiationBounds:
    policy = negotiation.policy
    return NegotiationBounds(
        max_rounds=int(policy["max_rounds"]),
        floor_unit_price=Decimal(str(policy["floor_unit_price"])),
        ceiling_unit_price=Decimal(str(policy["ceiling_unit_price"])),
    )


def _ensure_open(run: SourcingRun) -> None:
    if run.status in TERMINAL:
        raise HTTPException(status_code=409, detail="This run is closed.")


def _user(session: Session, email: str) -> User:
    user = session.scalar(select(User).where(User.email == email))
    if user is None:
        raise HTTPException(status_code=401, detail="Demo user is not seeded.")
    return user


def _require_buyer(user: User) -> None:
    if user.role != "buyer":
        raise HTTPException(status_code=403, detail="This action requires the buyer role.")


def _require_approver(user: User) -> None:
    if user.role not in {"approver", "admin_demo"}:
        raise HTTPException(status_code=403, detail="This action requires the approver role.")


def _visible_run(session: Session, user: User, run_id: uuid.UUID) -> SourcingRun:
    run = session.get(SourcingRun, run_id)
    if run is None or (user.role == "buyer" and run.created_by != user.id):
        raise HTTPException(status_code=404, detail="Sourcing run not found.")
    if user.role not in {"buyer", "approver", "admin_demo"}:
        raise HTTPException(status_code=403, detail="This action is not allowed.")
    return run


def _visible_negotiation(session: Session, user: User, negotiation_id: uuid.UUID) -> Negotiation:
    negotiation = session.get(Negotiation, negotiation_id)
    if negotiation is None:
        raise HTTPException(status_code=404, detail="Negotiation not found.")
    _visible_run(session, user, negotiation.sourcing_run_id)
    return negotiation


def _visible_draft(session: Session, user: User, po_id: uuid.UUID) -> PurchaseOrderDraft:
    draft = session.get(PurchaseOrderDraft, po_id)
    if draft is None or (user.role == "buyer" and draft.created_by != user.id):
        raise HTTPException(status_code=404, detail="Purchase order draft not found.")
    if user.role not in {"buyer", "approver", "admin_demo"}:
        raise HTTPException(status_code=403, detail="This action is not allowed.")
    return draft


def _event(
    session: Session,
    workflow_id: uuid.UUID,
    event_type: str,
    actor_id: uuid.UUID,
    payload: dict[str, object],
    correlation_id: uuid.UUID,
    now: datetime,
) -> None:
    session.add(
        WorkflowEvent(
            id=uuid.uuid4(),
            workflow_id=workflow_id,
            event_type=event_type,
            actor_type="user",
            actor_id=actor_id,
            payload_redacted=payload,
            correlation_id=correlation_id,
            created_at=now,
        )
    )


def _remember(
    session: Session,
    user: User,
    key: str | None,
    raw_body: bytes,
    status_code: int,
    body: dict[str, object],
    now: datetime,
) -> None:
    if not key:
        return
    session.add(
        IdempotencyKey(
            key=key,
            user_id=user.id,
            request_hash=request_hash(raw_body),
            status_code=status_code,
            response_json=body,
            created_at=now,
        )
    )
    session.commit()


def _run_read(run: SourcingRun) -> SourcingRunRead:
    offers = [OfferRead.model_validate(item) for item in run.state["offers"]]
    return SourcingRunRead(
        id=run.id,
        rfq_id=run.rfq_id,
        status=run.status,
        workflow_version=run.workflow_version,
        started_at=run.started_at.isoformat(),
        finished_at=None if run.finished_at is None else run.finished_at.isoformat(),
        error_code=run.error_code,
        eligible_count=_eligible_count(offers),
        data_mode="synthetic_demo",
        orchestrator=str(run.state.get("orchestrator", "langgraph")),
        steps=list(run.state.get("steps", [])),
    )


def _negotiation_read(negotiation: Negotiation) -> NegotiationRead:
    return NegotiationRead(
        id=negotiation.id,
        sourcing_run_id=negotiation.sourcing_run_id,
        quotation_id=negotiation.quotation_id,
        status=negotiation.status,
        round_count=negotiation.round_count,
        max_rounds=negotiation.max_rounds,
        policy=negotiation.policy,  # type: ignore[arg-type]
        transcript=list(negotiation.transcript),
        final_offer_id=negotiation.final_offer_id,
        simulation=True,
        data_mode="synthetic_demo",
    )


def _po_read(draft: PurchaseOrderDraft, supplier_name: str) -> PurchaseOrderRead:
    return PurchaseOrderRead(
        id=draft.id,
        sourcing_run_id=draft.sourcing_run_id,
        rfq_id=draft.rfq_id,
        quotation_id=draft.quotation_id,
        supplier_id=draft.supplier_id,
        supplier_name=supplier_name,
        status=draft.status,
        items=list(draft.items),
        subtotal=money_text(Decimal(draft.subtotal)),
        freight=money_text(Decimal(draft.freight)),
        tax=money_text(Decimal(draft.tax)),
        discount=money_text(Decimal(draft.discount)),
        total=money_text(Decimal(draft.total)),
        currency=draft.currency,
        terms=draft.terms,
        version=draft.version,
        notice=NOTICE,
        created_at=draft.created_at.isoformat(),
    )


def _eligible_count(offers: list[OfferRead]) -> int:
    return sum(1 for item in offers if item.eligible)


def _optional(value: Decimal | None) -> Decimal | None:
    if value is None:
        return None
    return Decimal(value)


def _plain(value: Decimal) -> str:
    text = format(Decimal(value), "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"
