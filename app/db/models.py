
"""Define business, family, child, and childcare contract database models."""

from datetime import date
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
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
