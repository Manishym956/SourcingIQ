"""Phase 1 procurement tables. Deterministic catalogue only."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_procurement"
down_revision: str | None = "0001_app_metadata"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("email"),
        sa.CheckConstraint("role IN ('buyer', 'approver', 'admin_demo')", name="ck_users_role"),
    )
    op.create_table(
        "rfqs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("material", sa.String(length=200), nullable=False),
        sa.Column("specification", sa.String(length=200), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 4), nullable=False),
        sa.Column("unit", sa.String(length=32), nullable=False),
        sa.Column("delivery_location", sa.String(length=300), nullable=False),
        sa.Column("needed_by", sa.Date(), nullable=False),
        sa.Column("budget_amount", sa.Numeric(18, 2)),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("quantity > 0", name="ck_rfqs_quantity_positive"),
    )
    op.create_index("ix_rfqs_created_by", "rfqs", ["created_by"])
    op.create_table(
        "suppliers",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("verification_status", sa.String(length=64), nullable=False),
        sa.Column("service_regions", postgresql.JSONB(), nullable=False),
        sa.Column("data_source", sa.String(length=64), nullable=False),
        sa.Column("last_updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "supplier_capabilities",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("supplier_id", sa.Uuid(), sa.ForeignKey("suppliers.id"), nullable=False),
        sa.Column("material", sa.String(length=200), nullable=False),
        sa.Column("specification", sa.String(length=200), nullable=False),
        sa.Column("available_quantity", sa.Numeric(18, 4), nullable=False),
        sa.Column("unit", sa.String(length=32), nullable=False),
        sa.Column("lead_time_days", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_capabilities_supplier", "supplier_capabilities", ["supplier_id"])
    op.create_table(
        "quotations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("supplier_id", sa.Uuid(), sa.ForeignKey("suppliers.id"), nullable=False),
        sa.Column("rfq_id", sa.Uuid(), sa.ForeignKey("rfqs.id")),
        sa.Column("unit_price", sa.Numeric(18, 4), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 4), nullable=False),
        sa.Column("unit", sa.String(length=32), nullable=False),
        sa.Column("freight_amount", sa.Numeric(18, 2)),
        sa.Column("tax_amount", sa.Numeric(18, 2)),
        sa.Column("discount_amount", sa.Numeric(18, 2)),
        sa.Column("tax_included", sa.Boolean()),
        sa.Column("valid_until", sa.DateTime(timezone=True)),
        sa.Column("quoted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("source_reference", sa.String(length=200)),
    )
    op.create_index("ix_quotations_supplier", "quotations", ["supplier_id"])
    op.create_table(
        "offer_evaluations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("rfq_id", sa.Uuid(), sa.ForeignKey("rfqs.id"), nullable=False),
        sa.Column("quotation_id", sa.Uuid(), sa.ForeignKey("quotations.id"), nullable=False),
        sa.Column("eligible", sa.Boolean(), nullable=False),
        sa.Column("exclusion_reasons", postgresql.JSONB(), nullable=False),
        sa.Column("normalized_cost", sa.Numeric(18, 2)),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("calculation_version", sa.String(length=64), nullable=False),
        sa.Column("ranking_reasons", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_offer_evaluations_rfq", "offer_evaluations", ["rfq_id"])
    op.create_table(
        "idempotency_keys",
        sa.Column("key", sa.String(length=200), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("response_json", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("idempotency_keys")
    op.drop_table("offer_evaluations")
    op.drop_table("quotations")
    op.drop_table("supplier_capabilities")
    op.drop_table("suppliers")
    op.drop_table("rfqs")
    op.drop_table("users")
