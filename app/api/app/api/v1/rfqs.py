from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.agent.extraction import PatternExtractor, accept_model_output
from app.api.deps import require_demo_auth
from app.core.db import get_session
from app.domain.sourcing import money_text
from app.schemas.offers import OfferComparison
from app.schemas.rfq import RfqCreate, RfqPage, RfqRead
from app.services.procurement import compare_offers, create_rfq, get_rfq, list_rfqs

router = APIRouter(prefix="/rfqs", tags=["rfqs"], dependencies=[Depends(require_demo_auth)])


class ExtractRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=4000)


class ExtractedFieldRead(BaseModel):
    material: str | None
    specification: str | None
    quantity: str | None
    unit: str | None
    delivery_location: str | None
    needed_by: str | None
    budget_amount: str | None
    currency: str | None


class ExtractionRead(BaseModel):
    status: str
    fields: ExtractedFieldRead
    ignored_fields: list[str]
    missing_fields: list[str]
    reason: str | None
    extractor: str


@router.post("/extract")
def post_extract(payload: ExtractRequest) -> ExtractionRead:
    result = accept_model_output(PatternExtractor().extract(payload.text))
    fields = result.fields
    return ExtractionRead(
        status=result.status,
        fields=ExtractedFieldRead(
            material=fields.material,
            specification=fields.specification,
            quantity=None if fields.quantity is None else format(fields.quantity, "f"),
            unit=fields.unit,
            delivery_location=fields.delivery_location,
            needed_by=None if fields.needed_by is None else fields.needed_by.isoformat(),
            budget_amount=None
            if fields.budget_amount is None
            else money_text(fields.budget_amount),
            currency=fields.currency,
        ),
        ignored_fields=result.ignored_fields,
        missing_fields=result.missing_fields,
        reason=result.reason,
        extractor="local-pattern",
    )


@router.post("")
async def post_rfq(
    payload: RfqCreate,
    request: Request,
    session: Annotated[Session, Depends(get_session)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> JSONResponse:
    raw_body = await request.body()
    status_code, body = create_rfq(
        session,
        payload,
        raw_body=raw_body,
        idempotency_key=idempotency_key,
    )
    return JSONResponse(status_code=status_code, content=body)


@router.get("")
def get_rfqs(
    session: Annotated[Session, Depends(get_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> RfqPage:
    return list_rfqs(session, limit=limit, offset=offset)


@router.get("/{rfq_id}")
def get_one_rfq(rfq_id: UUID, session: Annotated[Session, Depends(get_session)]) -> RfqRead:
    return get_rfq(session, rfq_id)


@router.get("/{rfq_id}/offers")
def get_offers(rfq_id: UUID, session: Annotated[Session, Depends(get_session)]) -> OfferComparison:
    return compare_offers(session, rfq_id)
