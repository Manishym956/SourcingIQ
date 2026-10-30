"""Phase 2 workflow tables. Runs, mock negotiation, and draft purchase orders."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_workflow"
down_revision: str | None = "0002_procurement"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

RUN_STATUSES = (
    "created",
    "validating",
    "sourcing",
    "comparing",
    "negotiating",
    "draft_ready",
    "awaiting_review",
    "approved_draft",
    "rejected",
    "cancelled",
    "failed",
)
NEGOTIATION_STATUSES = ("open", "accepted", "limit_reached", "cancelled")
PO_STATUSES = ("draft", "awaiting_review", "approved_draft", "rejected", "cancelled")


def upgrade() -> None:
    op.add_column("suppliers", sa.Column("simulation_profile", postgresql.JSONB()))
    op.create_table(
        "sourcing_runs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("rfq_id", sa.Uuid(), sa.ForeignKey("rfqs.id"), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("workflow_version", sa.String(length=64), nullable=False),
        sa.Column("state", postgresql.JSONB(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("error_code", sa.String(length=64)),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.CheckConstraint(
            "status IN (" + ", ".join(f"'{item}'" for item in RUN_STATUSES) + ")",
            name="ck_sourcing_runs_status",
        ),
    )
    op.create_index("ix_sourcing_runs_rfq", "sourcing_runs", ["rfq_id"])
    op.create_index("ix_sourcing_runs_created_by", "sourcing_runs", ["created_by"])
    op.create_table(
        "negotiations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("sourcing_run_id", sa.Uuid(), sa.ForeignKey("sourcing_runs.id"), nullable=False),
        sa.Column("quotation_id", sa.Uuid(), sa.ForeignKey("quotations.id"), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("round_count", sa.Integer(), nullable=False),
        sa.Column("max_rounds", sa.Integer(), nullable=False),
        sa.Column("policy", postgresql.JSONB(), nullable=False),
        sa.Column("transcript", postgresql.JSONB(), nullable=False),
        sa.Column("final_offer_id", sa.Uuid(), sa.ForeignKey("quotations.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("round_count >= 0", name="ck_negotiations_rounds_non_negative"),
        sa.CheckConstraint("round_count <= max_rounds", name="ck_negotiations_rounds_capped"),
        sa.CheckConstraint("max_rounds >= 1 AND max_rounds <= 5", name="ck_negotiations_max_rounds"),
        sa.CheckConstraint(
            "status IN (" + ", ".join(f"'{item}'" for item in NEGOTIATION_STATUSES) + ")",
            name="ck_negotiations_status",
        ),
    )
    op.create_index("ix_negotiations_run", "negotiations", ["sourcing_run_id"])
    op.create_table(
        "purchase_order_drafts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("sourcing_run_id", sa.Uuid(), sa.ForeignKey("sourcing_runs.id"), nullable=False),
        sa.Column("rfq_id", sa.Uuid(), sa.ForeignKey("rfqs.id"), nullable=False),
        sa.Column("quotation_id", sa.Uuid(), sa.ForeignKey("quotations.id"), nullable=False),
        sa.Column("supplier_id", sa.Uuid(), sa.ForeignKey("suppliers.id"), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("items", postgresql.JSONB(), nullable=False),
        sa.Column("subtotal", sa.Numeric(18, 2), nullable=False),
        sa.Column("freight", sa.Numeric(18, 2), nullable=False),
        sa.Column("tax", sa.Numeric(18, 2), nullable=False),
        sa.Column("discount", sa.Numeric(18, 2), nullable=False),
        sa.Column("total", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("terms", postgresql.JSONB(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("version >= 1", name="ck_po_version"),
        sa.CheckConstraint(
            "status IN (" + ", ".join(f"'{item}'" for item in PO_STATUSES) + ")",
            name="ck_po_status",
        ),
    )
    op.create_index("ix_po_run", "purchase_order_drafts", ["sourcing_run_id"])
    op.create_table(
        "approvals",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "purchase_order_id",
            sa.Uuid(),
            sa.ForeignKey("purchase_order_drafts.id"),
            nullable=False,
        ),
        sa.Column("draft_version", sa.Integer(), nullable=False),
        sa.Column("actor_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("action IN ('approve', 'reject')", name="ck_approvals_action"),
    )
    op.create_table(
        "workflow_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workflow_id", sa.Uuid(), sa.ForeignKey("sourcing_runs.id"), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("actor_type", sa.String(length=32), nullable=False),
        sa.Column("actor_id", sa.Uuid()),
        sa.Column("payload_redacted", postgresql.JSONB(), nullable=False),
        sa.Column("correlation_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_workflow_events_workflow", "workflow_events", ["workflow_id"])


def downgrade() -> None:
    op.drop_index("ix_workflow_events_workflow", table_name="workflow_events")
    op.drop_table("workflow_events")
    op.drop_table("approvals")
    op.drop_index("ix_po_run", table_name="purchase_order_drafts")
    op.drop_table("purchase_order_drafts")
    op.drop_index("ix_negotiations_run", table_name="negotiations")
    op.drop_table("negotiations")
    op.drop_index("ix_sourcing_runs_created_by", table_name="sourcing_runs")
    op.drop_index("ix_sourcing_runs_rfq", table_name="sourcing_runs")
    op.drop_table("sourcing_runs")
    op.drop_column("suppliers", "simulation_profile")
