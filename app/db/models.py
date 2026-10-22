"""Define tenant-aware business, childcare, contract, and invoice models."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKeyConstraint,
    Numeric,
    String,
    UniqueConstraint,
    and_,
)
from sqlalchemy.orm import Mapped, foreign, mapped_column, relationship

from app.db.base import Base


class Business(Base):
    """Represent a childminding business that owns its data."""

    __tablename__ = "businesses"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)

    families: Mapped[list["Family"]] = relationship(
        back_populates="business",
        foreign_keys=lambda: [Family.business_id],
    )
    children: Mapped[list["Child"]] = relationship(
        back_populates="business",
        foreign_keys=lambda: [Child.business_id],
    )
    contracts: Mapped[list["Contract"]] = relationship(
        back_populates="business",
        foreign_keys=lambda: [Contract.business_id],
    )
    invoices: Mapped[list["Invoice"]] = relationship(
        back_populates="business",
        foreign_keys=lambda: [Invoice.business_id],
    )


class Family(Base):
    """Represent a family within one business."""

    __tablename__ = "families"
    __table_args__ = (
        UniqueConstraint("business_id", "id"),
        ForeignKeyConstraint(["business_id"], ["businesses.id"]),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)

    business: Mapped["Business"] = relationship(
        back_populates="families",
        foreign_keys=[business_id],
    )
    children: Mapped[list["Child"]] = relationship(
        back_populates="family",
        primaryjoin=lambda: and_(
            Family.id == foreign(Child.family_id),
            Family.business_id == Child.business_id,
        ),
    )
    contracts: Mapped[list["Contract"]] = relationship(
        back_populates="family",
        primaryjoin=lambda: and_(
            Family.id == foreign(Contract.family_id),
            Family.business_id == Contract.business_id,
        ),
    )
    invoices: Mapped[list["Invoice"]] = relationship(
        back_populates="family",
        primaryjoin=lambda: and_(
            Family.id == foreign(Invoice.family_id),
            Family.business_id == Invoice.business_id,
        ),
    )


class Child(Base):
    """Represent a child belonging to a family within one business."""

    __tablename__ = "children"
    __table_args__ = (
        UniqueConstraint("business_id", "id"),
        ForeignKeyConstraint(["business_id"], ["businesses.id"]),
        ForeignKeyConstraint(
            ["business_id", "family_id"],
            ["families.business_id", "families.id"],
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(nullable=False)
    family_id: Mapped[int] = mapped_column(nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)

    business: Mapped["Business"] = relationship(
        back_populates="children",
        foreign_keys=[business_id],
    )
    family: Mapped["Family"] = relationship(
        back_populates="children",
        primaryjoin=lambda: and_(
            Family.id == foreign(Child.family_id),
            Family.business_id == Child.business_id,
        ),
    )
    contracts: Mapped[list["Contract"]] = relationship(
        back_populates="child",
        primaryjoin=lambda: and_(
            Child.id == foreign(Contract.child_id),
            Child.business_id == Contract.business_id,
        ),
    )


class Contract(Base):
    """Represent a child's contracted rate for a defined date range."""

    __tablename__ = "contracts"
    __table_args__ = (
        UniqueConstraint("business_id", "id"),
        ForeignKeyConstraint(["business_id"], ["businesses.id"]),
        ForeignKeyConstraint(
            ["business_id", "family_id"],
            ["families.business_id", "families.id"],
        ),
        ForeignKeyConstraint(
            ["business_id", "child_id"],
            ["children.business_id", "children.id"],
        ),
        CheckConstraint(
            "effective_to IS NULL OR effective_to >= effective_from",
            name="valid_effective_date_range",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(nullable=False)
    family_id: Mapped[int] = mapped_column(nullable=False)
    child_id: Mapped[int] = mapped_column(nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    rate_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    rate_unit: Mapped[str] = mapped_column(String(30), nullable=False)

    business: Mapped["Business"] = relationship(
        back_populates="contracts",
        foreign_keys=[business_id],
    )
    family: Mapped["Family"] = relationship(
        back_populates="contracts",
        primaryjoin=lambda: and_(
            Family.id == foreign(Contract.family_id),
            Family.business_id == Contract.business_id,
        ),
    )
    child: Mapped["Child"] = relationship(
        back_populates="contracts",
        primaryjoin=lambda: and_(
            Child.id == foreign(Contract.child_id),
            Child.business_id == Contract.business_id,
        ),
    )


class Invoice(Base):
    """Represent a draft or issued invoice for one family."""

    __tablename__ = "invoices"
    __table_args__ = (
        UniqueConstraint(
            "business_id",
            "id",
            name="uq_invoices_business_id_id",
        ),
        UniqueConstraint(
            "business_id",
            "invoice_number",
            name="uq_invoices_business_invoice_number",
        ),
        UniqueConstraint(
            "business_id",
            "idempotency_key",
            name="uq_invoices_business_idempotency_key",
        ),
        ForeignKeyConstraint(["business_id"], ["businesses.id"]),
        ForeignKeyConstraint(
            ["business_id", "family_id"],
            ["families.business_id", "families.id"],
        ),
        CheckConstraint(
            "period_end >= period_start",
            name="valid_billing_period",
        ),
        CheckConstraint(
            "total_pence >= 0",
            name="non_negative_invoice_total",
        ),
        CheckConstraint(
            "status IN ('draft', 'issued', 'corrected')",
            name="valid_invoice_status",
        ),
        CheckConstraint(
            "(status = 'draft' AND invoice_number IS NULL "
            "AND issued_at IS NULL) OR "
            "(status IN ('issued', 'corrected') "
            "AND invoice_number IS NOT NULL AND issued_at IS NOT NULL)",
            name="invoice_issue_state_consistency",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(nullable=False)
    family_id: Mapped[int] = mapped_column(nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="draft",
    )
    invoice_number: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)
    total_pence: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
    )
    issued_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    business: Mapped["Business"] = relationship(
        back_populates="invoices",
        foreign_keys=[business_id],
    )
    family: Mapped["Family"] = relationship(
        back_populates="invoices",
        primaryjoin=lambda: and_(
            Family.id == foreign(Invoice.family_id),
            Family.business_id == Invoice.business_id,
        ),
    )
    lines: Mapped[list["InvoiceLine"]] = relationship(
        back_populates="invoice",
        primaryjoin=lambda: and_(
            Invoice.id == foreign(InvoiceLine.invoice_id),
            Invoice.business_id == InvoiceLine.business_id,
        ),
        cascade="all, delete-orphan",
    )
    corrections: Mapped[list["InvoiceCorrection"]] = relationship(
        back_populates="original_invoice",
        primaryjoin=lambda: and_(
            Invoice.id == foreign(InvoiceCorrection.original_invoice_id),
            Invoice.business_id == InvoiceCorrection.business_id,
        ),
    )


class InvoiceLine(Base):
    """Preserve billing inputs and monetary amounts for an invoice line."""

    __tablename__ = "invoice_lines"
    __table_args__ = (
        ForeignKeyConstraint(
            ["business_id", "invoice_id"],
            ["invoices.business_id", "invoices.id"],
        ),
        ForeignKeyConstraint(
            ["business_id", "child_id"],
            ["children.business_id", "children.id"],
        ),
        CheckConstraint(
            "quantity > 0",
            name="positive_line_quantity",
        ),
        CheckConstraint(
            "(line_type = 'adjustment' AND unit_rate <= 0 "
            "AND amount_pence <= 0) OR "
            "(line_type <> 'adjustment' AND unit_rate >= 0 "
            "AND amount_pence >= 0)",
            name="line_amount_sign_matches_type",
        ),
        CheckConstraint(
            "line_type IN "
            "('contracted_hours', 'additional_hours', 'service', 'adjustment')",
            name="valid_invoice_line_type",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(nullable=False)
    invoice_id: Mapped[int] = mapped_column(nullable=False)
    child_id: Mapped[int | None] = mapped_column(nullable=True)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    line_type: Mapped[str] = mapped_column(String(30), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    unit: Mapped[str] = mapped_column(String(30), nullable=False)
    unit_rate: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    amount_pence: Mapped[int] = mapped_column(BigInteger, nullable=False)
    adjustment_reason: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    deduction_evidence: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    invoice: Mapped["Invoice"] = relationship(
        back_populates="lines",
        primaryjoin=lambda: and_(
            Invoice.id == foreign(InvoiceLine.invoice_id),
            Invoice.business_id == InvoiceLine.business_id,
        ),
    )


class InvoiceCorrection(Base):
    """Record a credit or correction linked to an issued invoice."""

    __tablename__ = "invoice_corrections"
    __table_args__ = (
        UniqueConstraint("business_id", "id"),
        ForeignKeyConstraint(["business_id"], ["businesses.id"]),
        ForeignKeyConstraint(
            ["business_id", "original_invoice_id"],
            ["invoices.business_id", "invoices.id"],
        ),
        CheckConstraint(
            "amount_pence > 0",
            name="positive_correction_amount",
        ),
        CheckConstraint(
            "correction_type IN ('credit', 'correction')",
            name="valid_correction_type",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(nullable=False)
    original_invoice_id: Mapped[int] = mapped_column(nullable=False)
    correction_type: Mapped[str] = mapped_column(String(20), nullable=False)
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    amount_pence: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    original_invoice: Mapped["Invoice"] = relationship(
        back_populates="corrections",
        primaryjoin=lambda: and_(
            Invoice.id == foreign(InvoiceCorrection.original_invoice_id),
            Invoice.business_id == InvoiceCorrection.business_id,
        ),
    )
