from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import require_demo_auth
from app.core.db import get_session
from app.schemas.supplier import SupplierPage, SupplierRead
from app.services.procurement import get_supplier, list_suppliers

router = APIRouter(
    prefix="/suppliers", tags=["suppliers"], dependencies=[Depends(require_demo_auth)]
)


@router.get("")
def get_suppliers(
    session: Annotated[Session, Depends(get_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    material: str | None = None,
) -> SupplierPage:
    return list_suppliers(session, limit=limit, offset=offset, material=material)


@router.get("/{supplier_id}")
def get_one_supplier(
    supplier_id: UUID, session: Annotated[Session, Depends(get_session)]
) -> SupplierRead:
    return get_supplier(session, supplier_id)
