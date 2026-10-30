import uuid
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.deps import require_actor
from app.core.db import get_session
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
)
from app.services.workflow import (
    create_draft,
    decide_draft,
    get_draft,
    get_negotiation,
    get_run,
    get_run_draft,
    get_run_negotiation,
    list_events,
    list_runs,
    negotiation_turn,
    run_offers,
    start_negotiation,
    start_run,
)

router = APIRouter(tags=["workflow"])


def _correlation(request: Request) -> UUID:
    raw = getattr(request.state, "request_id", "")
    try:
        return UUID(str(raw))
    except ValueError:
        return uuid.uuid4()


@router.post("/sourcing-runs")
async def post_run(
    payload: SourcingRunCreate,
    request: Request,
    session: Annotated[Session, Depends(get_session)],
    actor: Annotated[str, Depends(require_actor)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> JSONResponse:
    status_code, body = start_run(
        session,
        payload,
        actor_email=actor,
        raw_body=await request.body(),
        idempotency_key=idempotency_key,
        correlation_id=_correlation(request),
    )
    return JSONResponse(status_code=status_code, content=body)


@router.get("/sourcing-runs")
def get_runs(
    session: Annotated[Session, Depends(get_session)],
    actor: Annotated[str, Depends(require_actor)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> SourcingRunPage:
    return list_runs(session, actor_email=actor, limit=limit, offset=offset)


@router.get("/sourcing-runs/{run_id}")
def get_one_run(
    run_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    actor: Annotated[str, Depends(require_actor)],
) -> SourcingRunRead:
    return get_run(session, run_id, actor_email=actor)


@router.get("/sourcing-runs/{run_id}/events")
def get_events(
    run_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    actor: Annotated[str, Depends(require_actor)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> WorkflowEventPage:
    return list_events(session, run_id, actor_email=actor, limit=limit, offset=offset)


@router.get("/sourcing-runs/{run_id}/negotiations")
def get_run_negotiations(
    run_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    actor: Annotated[str, Depends(require_actor)],
) -> NegotiationRead:
    negotiation = get_run_negotiation(session, run_id, actor_email=actor)
    if negotiation is None:
        raise HTTPException(status_code=404, detail="Negotiation not found.")
    return negotiation


@router.get("/sourcing-runs/{run_id}/purchase-orders")
def get_run_purchase_order(
    run_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    actor: Annotated[str, Depends(require_actor)],
) -> PurchaseOrderRead:
    draft = get_run_draft(session, run_id, actor_email=actor)
    if draft is None:
        raise HTTPException(status_code=404, detail="Purchase order draft not found.")
    return draft


@router.get("/sourcing-runs/{run_id}/offers")
def get_run_offers(
    run_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    actor: Annotated[str, Depends(require_actor)],
) -> RunOffersRead:
    return run_offers(session, run_id, actor_email=actor)


@router.post("/sourcing-runs/{run_id}/negotiations")
async def post_negotiation(
    run_id: UUID,
    payload: NegotiationCreate,
    request: Request,
    session: Annotated[Session, Depends(get_session)],
    actor: Annotated[str, Depends(require_actor)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> JSONResponse:
    status_code, body = start_negotiation(
        session,
        run_id,
        payload,
        actor_email=actor,
        raw_body=await request.body(),
        idempotency_key=idempotency_key,
        correlation_id=_correlation(request),
    )
    return JSONResponse(status_code=status_code, content=body)


@router.post("/negotiations/{negotiation_id}/turns")
def post_turn(
    negotiation_id: UUID,
    payload: NegotiationTurn,
    request: Request,
    session: Annotated[Session, Depends(get_session)],
    actor: Annotated[str, Depends(require_actor)],
) -> NegotiationRead:
    return negotiation_turn(
        session,
        negotiation_id,
        payload,
        actor_email=actor,
        correlation_id=_correlation(request),
    )


@router.get("/negotiations/{negotiation_id}")
def get_one_negotiation(
    negotiation_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    actor: Annotated[str, Depends(require_actor)],
) -> NegotiationRead:
    return get_negotiation(session, negotiation_id, actor_email=actor)


@router.post("/purchase-orders/drafts")
async def post_draft(
    payload: DraftCreate,
    request: Request,
    session: Annotated[Session, Depends(get_session)],
    actor: Annotated[str, Depends(require_actor)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> JSONResponse:
    status_code, body = create_draft(
        session,
        payload,
        actor_email=actor,
        raw_body=await request.body(),
        idempotency_key=idempotency_key,
        correlation_id=_correlation(request),
    )
    return JSONResponse(status_code=status_code, content=body)


@router.get("/purchase-orders/{po_id}")
def get_one_draft(
    po_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    actor: Annotated[str, Depends(require_actor)],
) -> PurchaseOrderRead:
    return get_draft(session, po_id, actor_email=actor)


@router.post("/purchase-orders/{po_id}/approve")
def post_approve(
    po_id: UUID,
    payload: DecisionCreate,
    request: Request,
    session: Annotated[Session, Depends(get_session)],
    actor: Annotated[str, Depends(require_actor)],
) -> PurchaseOrderRead:
    return decide_draft(
        session,
        po_id,
        payload,
        action="approve",
        actor_email=actor,
        correlation_id=_correlation(request),
    )


@router.post("/purchase-orders/{po_id}/reject")
def post_reject(
    po_id: UUID,
    payload: DecisionCreate,
    request: Request,
    session: Annotated[Session, Depends(get_session)],
    actor: Annotated[str, Depends(require_actor)],
) -> PurchaseOrderRead:
    return decide_draft(
        session,
        po_id,
        payload,
        action="reject",
        actor_email=actor,
        correlation_id=_correlation(request),
    )
