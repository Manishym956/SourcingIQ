from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_demo_auth
from app.core.db import get_session
from app.models.procurement import PurchaseOrderDraft, Rfq, SourcingRun, Supplier

router = APIRouter(
    prefix="/observability",
    tags=["observability"],
    dependencies=[Depends(require_demo_auth)],
)


@router.get("/metrics")
def get_metrics(session: Annotated[Session, Depends(get_session)]) -> dict[str, Any]:
    """Retrieve operational and pipeline metrics for observability."""
    # Sourcing runs count by status
    run_counts = dict(
        session.execute(
            select(SourcingRun.status, func.count(SourcingRun.id)).group_by(SourcingRun.status)
        ).all()
    )

    # RFQs count
    rfq_count = session.scalar(select(func.count(Rfq.id))) or 0

    # Supplier count
    supplier_count = session.scalar(select(func.count(Supplier.id))) or 0

    # Purchase orders count by status
    po_stmt = select(
        PurchaseOrderDraft.status, func.count(PurchaseOrderDraft.id)
    ).group_by(PurchaseOrderDraft.status)
    po_counts = dict(session.execute(po_stmt).all())

    awaiting = po_counts.get("awaiting_review", 0) + po_counts.get("draft_ready", 0)
    return {
        "service": "sourcingiq-api",
        "data_mode": "synthetic_demo",
        "counts": {
            "rfqs_total": rfq_count,
            "suppliers_total": supplier_count,
            "sourcing_runs": {
                "total": sum(run_counts.values()),
                "by_status": run_counts,
            },
            "purchase_orders": {
                "total": sum(po_counts.values()),
                "approved": po_counts.get("approved_draft", 0),
                "rejected": po_counts.get("rejected", 0),
                "awaiting_review": awaiting,
            },
        },
    }
