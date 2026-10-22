"""Test database model relationships and tenant isolation."""

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.db.models import (
    Business,
    Child,
    Contract,
    Family,
    Invoice,
    InvoiceLine,
)


def test_business_can_own_family_child_and_contract(session):
    """Persist related records belonging to the same business."""
    business = Business(name="Example Childminding")
    family = Family(name="Example Family", business=business)
    child = Child(name="Example Child", business=business, family=family)
    contract = Contract(
        business=business,
        family=family,
        child=child,
        effective_from=date(2026, 9, 1),
        effective_to=None,
        rate_amount=Decimal("7.50"),
        rate_unit="hour",
    )

    session.add(contract)
    session.commit()

    assert family.business_id == business.id
    assert child.family_id == family.id
    assert contract.rate_amount == Decimal("7.50")


def test_child_cannot_reference_family_from_another_business(session):
    """Reject a child whose family belongs to another business."""
    first_business = Business(name="First Business")
    second_business = Business(name="Second Business")
    first_family = Family(name="First Family", business=first_business)

    session.add_all([first_family, second_business])
    session.commit()

    child = Child(
        name="Example Child",
        business=second_business,
        family=first_family,
    )
    session.add(child)

    with pytest.raises(IntegrityError):
        session.commit()

    session.rollback()


def test_contract_cannot_reference_child_from_another_business(session):
    """Reject a contract whose child belongs to another business."""
    first_business = Business(name="First Business")
    second_business = Business(name="Second Business")
    first_family = Family(name="First Family", business=first_business)
    first_child = Child(
        name="First Child",
        business=first_business,
        family=first_family,
    )
    second_family = Family(name="Second Family", business=second_business)

    session.add_all([first_child, second_family])
    session.commit()

    contract = Contract(
        business=second_business,
        family=second_family,
        child=first_child,
        effective_from=date(2026, 9, 1),
        rate_amount=Decimal("7.50"),
        rate_unit="hour",
    )
    session.add(contract)

    with pytest.raises(IntegrityError):
        session.commit()

    session.rollback()


def test_contract_rejects_end_date_before_start_date(session):
    """Reject a contract with an invalid effective date range."""
    business = Business(name="Example Business")
    family = Family(name="Example Family", business=business)
    child = Child(name="Example Child", business=business, family=family)
    contract = Contract(
        business=business,
        family=family,
        child=child,
        effective_from=date(2026, 10, 1),
        effective_to=date(2026, 9, 30),
        rate_amount=Decimal("7.50"),
        rate_unit="hour",
    )

    session.add(contract)

    with pytest.raises(IntegrityError):
        session.commit()

    session.rollback()


def test_draft_invoice_can_reference_family_in_same_business(session):
    """Allow a draft invoice for a family in the same business."""
    business = Business(name="Example Business")
    family = Family(name="Example Family", business=business)
    session.add(family)
    session.flush()

    invoice = Invoice(
        business_id=business.id,
        family_id=family.id,
        period_start=date(2026, 9, 1),
        period_end=date(2026, 9, 30),
        status="draft",
        idempotency_key="draft-september",
        total_pence=0,
    )
    session.add(invoice)
    session.commit()

    assert invoice.id is not None
    assert invoice.family_id == family.id


def test_invoice_cannot_reference_family_from_another_business(session):
    """Reject an invoice referencing another business's family."""
    first_business = Business(name="First Business")
    second_business = Business(name="Second Business")
    first_family = Family(name="First Family", business=first_business)
    session.add_all([first_family, second_business])
    session.flush()

    invoice = Invoice(
        business_id=second_business.id,
        family_id=first_family.id,
        period_start=date(2026, 9, 1),
        period_end=date(2026, 9, 30),
        status="draft",
        idempotency_key="cross-business-invoice",
        total_pence=0,
    )
    session.add(invoice)

    with pytest.raises(IntegrityError):
        session.commit()

    session.rollback()


def test_invoice_line_cannot_reference_child_from_another_business(session):
    """Reject an invoice line referencing another business's child."""
    first_business = Business(name="First Business")
    second_business = Business(name="Second Business")
    first_family = Family(name="First Family", business=first_business)
    first_child = Child(
        name="First Child",
        business=first_business,
        family=first_family,
    )
    second_family = Family(name="Second Family", business=second_business)
    session.add_all([first_child, second_family])
    session.flush()

    invoice = Invoice(
        business_id=second_business.id,
        family_id=second_family.id,
        period_start=date(2026, 9, 1),
        period_end=date(2026, 9, 30),
        status="draft",
        idempotency_key="second-business-invoice",
        total_pence=0,
    )
    session.add(invoice)
    session.flush()

    line = InvoiceLine(
        business_id=second_business.id,
        invoice_id=invoice.id,
        child_id=first_child.id,
        description="Contracted childcare",
        line_type="contracted_hours",
        quantity=Decimal("10"),
        unit="hour",
        unit_rate=Decimal("7.50"),
        amount_pence=7500,
    )
    session.add(line)

    with pytest.raises(IntegrityError):
        session.commit()

    session.rollback()


def test_invoice_number_must_be_unique_within_business(session):
    """Reject duplicate invoice numbers within one business."""
    business = Business(name="Example Business")
    family = Family(name="Example Family", business=business)
    session.add(family)
    session.flush()

    invoice_fields = {
        "business_id": business.id,
        "family_id": family.id,
        "period_start": date(2026, 9, 1),
        "period_end": date(2026, 9, 30),
        "status": "issued",
        "invoice_number": "INV-2026-0001",
        "total_pence": 7500,
        "issued_at": datetime.now(timezone.utc),
    }

    session.add(Invoice(idempotency_key="request-one", **invoice_fields))
    session.commit()

    session.add(Invoice(idempotency_key="request-two", **invoice_fields))

    with pytest.raises(IntegrityError):
        session.commit()

    session.rollback()


def test_different_businesses_can_use_same_invoice_number(session):
    """Allow different businesses to reuse an invoice number."""
    first_business = Business(name="First Business")
    second_business = Business(name="Second Business")
    first_family = Family(name="First Family", business=first_business)
    second_family = Family(name="Second Family", business=second_business)
    session.add_all([first_family, second_family])
    session.flush()

    invoice_fields = {
        "period_start": date(2026, 9, 1),
        "period_end": date(2026, 9, 30),
        "status": "issued",
        "invoice_number": "INV-2026-0001",
        "total_pence": 7500,
        "issued_at": datetime.now(timezone.utc),
    }

    session.add_all(
        [
            Invoice(
                business_id=first_business.id,
                family_id=first_family.id,
                idempotency_key="first-business-request",
                **invoice_fields,
            ),
            Invoice(
                business_id=second_business.id,
                family_id=second_family.id,
                idempotency_key="second-business-request",
                **invoice_fields,
            ),
        ]
    )
    session.commit()

    assert session.query(Invoice).count() == 2
