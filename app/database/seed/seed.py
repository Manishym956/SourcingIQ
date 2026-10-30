"""Seed the local database with a synthetic-demo marker and catalogue."""

import sys
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from sqlalchemy.orm import Session

API_ROOT = Path(__file__).resolve().parents[2] / "api"
sys.path.insert(0, str(API_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from catalog import (  # noqa: E402
    CATALOGUE,
    DEMO_APPROVER_EMAIL,
    DEMO_APPROVER_ID,
    DEMO_USER_EMAIL,
    DEMO_USER_ID,
)
from knowledge import DOCUMENTS, document_checksum  # noqa: E402

from app.core.db import get_engine  # noqa: E402
from app.models.metadata import AppMetadata  # noqa: E402
from app.models.procurement import (  # noqa: E402
    KnowledgeChunk,
    KnowledgeDocument,
    Quotation,
    Supplier,
    SupplierCapability,
    User,
)

DATA_MODE_KEY = "data_mode"
DATA_MODE_VALUE = "synthetic_demo"


def seed() -> None:
    now = datetime.now(UTC)
    with Session(get_engine()) as session:
        row = session.get(AppMetadata, DATA_MODE_KEY)
        if row is None:
            session.add(AppMetadata(key=DATA_MODE_KEY, value=DATA_MODE_VALUE, updated_at=now))
        else:
            row.value = DATA_MODE_VALUE
            row.updated_at = now
        user = session.get(User, DEMO_USER_ID)
        if user is None:
            session.add(
                User(
                    id=DEMO_USER_ID,
                    email=DEMO_USER_EMAIL,
                    display_name="Demo Buyer",
                    role="buyer",
                    created_at=now,
                    updated_at=now,
                )
            )
        approver = session.get(User, DEMO_APPROVER_ID)
        if approver is None:
            session.add(
                User(
                    id=DEMO_APPROVER_ID,
                    email=DEMO_APPROVER_EMAIL,
                    display_name="Demo Approver",
                    role="approver",
                    created_at=now,
                    updated_at=now,
                )
            )
        for item in CATALOGUE:
            _upsert_supplier(session, item, now)
        for document in DOCUMENTS:
            _upsert_document(session, document, now)
        session.commit()


def _upsert_supplier(session: Session, item: dict, now: datetime) -> None:
    supplier = session.get(Supplier, item["supplier_id"])
    if supplier is None:
        session.add(
            Supplier(
                id=item["supplier_id"],
                name=item["name"],
                status="active",
                verification_status="demo_unverified",
                service_regions=["Bengaluru, Karnataka"],
                data_source="synthetic",
                simulation_profile=item["simulation_profile"],
                last_updated_at=now,
                created_at=now,
            )
        )
    else:
        supplier.simulation_profile = item["simulation_profile"]
    if session.get(SupplierCapability, item["capability_id"]) is None:
        session.add(
            SupplierCapability(
                id=item["capability_id"],
                supplier_id=item["supplier_id"],
                material=item["material"],
                specification=item["specification"],
                available_quantity=Decimal(item["available_quantity"]),
                unit="tonne",
                lead_time_days=item["lead_time_days"],
                updated_at=now,
            )
        )
    if session.get(Quotation, item["quotation_id"]) is None:
        session.add(
            Quotation(
                id=item["quotation_id"],
                supplier_id=item["supplier_id"],
                rfq_id=None,
                unit_price=Decimal(item["unit_price"]),
                currency="INR",
                quantity=Decimal(item["available_quantity"]),
                unit="tonne",
                freight_amount=_decimal(item["freight_amount"]),
                tax_amount=_decimal(item["tax_amount"]),
                discount_amount=_decimal(item["discount_amount"]),
                tax_included=item["tax_included"],
                valid_until=None,
                quoted_at=now,
                source_type="synthetic_seed",
                source_reference=item["name"],
            )
        )


def _upsert_document(session: Session, document: dict, now: datetime) -> None:
    checksum = document_checksum(document["chunks"])
    row = session.get(KnowledgeDocument, document["id"])
    if row is None:
        session.add(
            KnowledgeDocument(
                id=document["id"],
                title=document["title"],
                version=1,
                checksum=checksum,
                source_label="approved_demo",
                created_at=now,
            )
        )
    else:
        row.checksum = checksum
        row.title = document["title"]
    for position, (chunk_id, text) in enumerate(document["chunks"]):
        chunk = session.get(KnowledgeChunk, chunk_id)
        if chunk is None:
            session.add(
                KnowledgeChunk(
                    id=chunk_id,
                    document_id=document["id"],
                    position=position,
                    text=text,
                    created_at=now,
                )
            )
        else:
            chunk.text = text
            chunk.position = position


def _decimal(value: str | None) -> Decimal | None:
    if value is None:
        return None
    return Decimal(value)


if __name__ == "__main__":
    seed()
    print("seeded data_mode=synthetic_demo and synthetic catalogue")
