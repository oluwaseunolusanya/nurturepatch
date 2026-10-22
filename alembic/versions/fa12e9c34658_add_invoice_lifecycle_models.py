"""Add invoice lifecycle models.

Revision ID: fa12e9c34658
Revises: 87e41fb77478
Create Date: 2026-10-22
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "fa12e9c34658"
down_revision: str | None = "87e41fb77478"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create invoice, invoice-line, and invoice-correction tables."""
    op.create_table(
        "invoices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("business_id", sa.Integer(), nullable=False),
        sa.Column("family_id", sa.Integer(), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("invoice_number", sa.String(length=50), nullable=True),
        sa.Column("idempotency_key", sa.String(length=200), nullable=False),
        sa.Column("total_pence", sa.BigInteger(), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "period_end >= period_start",
            name=op.f("ck_invoices_valid_billing_period"),
        ),
        sa.CheckConstraint(
            "total_pence >= 0",
            name=op.f("ck_invoices_non_negative_invoice_total"),
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'issued', 'corrected')",
            name=op.f("ck_invoices_valid_invoice_status"),
        ),
        sa.CheckConstraint(
            "(status = 'draft' AND invoice_number IS NULL "
            "AND issued_at IS NULL) OR "
            "(status IN ('issued', 'corrected') "
            "AND invoice_number IS NOT NULL AND issued_at IS NOT NULL)",
            name=op.f("ck_invoices_invoice_issue_state_consistency"),
        ),
        sa.ForeignKeyConstraint(
            ["business_id"],
            ["businesses.id"],
            name=op.f("fk_invoices_business_id_businesses"),
        ),
        sa.ForeignKeyConstraint(
            ["business_id", "family_id"],
            ["families.business_id", "families.id"],
            name=op.f("fk_invoices_business_id_families"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_invoices")),
        sa.UniqueConstraint(
            "business_id",
            "id",
            name="uq_invoices_business_id_id",
        ),
        sa.UniqueConstraint(
            "business_id",
            "invoice_number",
            name="uq_invoices_business_invoice_number",
        ),
        sa.UniqueConstraint(
            "business_id",
            "idempotency_key",
            name="uq_invoices_business_idempotency_key",
        ),
    )

    op.create_table(
        "invoice_corrections",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("business_id", sa.Integer(), nullable=False),
        sa.Column("original_invoice_id", sa.Integer(), nullable=False),
        sa.Column("correction_type", sa.String(length=20), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column("amount_pence", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "amount_pence > 0",
            name=op.f("ck_invoice_corrections_positive_correction_amount"),
        ),
        sa.CheckConstraint(
            "correction_type IN ('credit', 'correction')",
            name=op.f("ck_invoice_corrections_valid_correction_type"),
        ),
        sa.ForeignKeyConstraint(
            ["business_id"],
            ["businesses.id"],
            name=op.f("fk_invoice_corrections_business_id_businesses"),
        ),
        sa.ForeignKeyConstraint(
            ["business_id", "original_invoice_id"],
            ["invoices.business_id", "invoices.id"],
            name=op.f("fk_invoice_corrections_business_id_invoices"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_invoice_corrections")),
        sa.UniqueConstraint("business_id", "id"),
    )

    op.create_table(
        "invoice_lines",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("business_id", sa.Integer(), nullable=False),
        sa.Column("invoice_id", sa.Integer(), nullable=False),
        sa.Column("child_id", sa.Integer(), nullable=True),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("line_type", sa.String(length=30), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column("unit", sa.String(length=30), nullable=False),
        sa.Column("unit_rate", sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column("amount_pence", sa.BigInteger(), nullable=False),
        sa.Column("adjustment_reason", sa.String(length=500), nullable=True),
        sa.Column("deduction_evidence", sa.String(length=1000), nullable=True),
        sa.CheckConstraint(
            "quantity > 0",
            name=op.f("ck_invoice_lines_positive_line_quantity"),
        ),
        sa.CheckConstraint(
            "(line_type = 'adjustment' AND unit_rate <= 0 "
            "AND amount_pence <= 0) OR "
            "(line_type <> 'adjustment' AND unit_rate >= 0 "
            "AND amount_pence >= 0)",
            name=op.f("ck_invoice_lines_line_amount_sign_matches_type"),
        ),
        sa.CheckConstraint(
            "line_type IN "
            "('contracted_hours', 'additional_hours', 'service', 'adjustment')",
            name=op.f("ck_invoice_lines_valid_invoice_line_type"),
        ),
        sa.ForeignKeyConstraint(
            ["business_id", "invoice_id"],
            ["invoices.business_id", "invoices.id"],
            name=op.f("fk_invoice_lines_business_id_invoices"),
        ),
        sa.ForeignKeyConstraint(
            ["business_id", "child_id"],
            ["children.business_id", "children.id"],
            name=op.f("fk_invoice_lines_business_id_children"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_invoice_lines")),
    )


def downgrade() -> None:
    """Remove invoice lifecycle tables in dependency order."""
    op.drop_table("invoice_lines")
    op.drop_table("invoice_corrections")
    op.drop_table("invoices")
