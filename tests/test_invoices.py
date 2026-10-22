"""Test invoice lifecycle operations against PostgreSQL."""

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.db.models import (
    Business,
    Child,
    Contract,
    Family,
    Invoice,
    InvoiceCorrection,
)
from app.services.billing import BillingLineInput, LineType
from app.services.invoices import (
    IdempotencyConflict,
    InvoiceServiceError,
    create_draft,
    issue_invoice,
    recalculate_draft,
    record_correction,
)


@pytest.fixture
def invoice_context(session):
    """Create a business, family, child, and contract for invoice tests."""
    business = Business(name="Test Childcare Business")
    family = Family(name="Test Family", business=business)
    child = Child(name="Test Child", business=business, family=family)
    contract = Contract(
        business=business,
        family=family,
        child=child,
        effective_from=date(2025, 1, 1),
        effective_to=None,
        rate_amount=Decimal("7.50"),
        rate_unit="hour",
    )

    session.add(contract)
    session.flush()

    return {
        "business_id": business.id,
        "family_id": family.id,
        "child_id": child.id,
    }


def billing_line(child_id: int, quantity: str = "10") -> BillingLineInput:
    """Build a standard contracted-hours billing line."""
    return BillingLineInput(
        description="Childcare hours",
        line_type=LineType.CONTRACTED_HOURS,
        quantity=Decimal(quantity),
        unit_rate=Decimal("7.50"),
        unit="hour",
        child_id=str(child_id),
    )


def make_draft(session, context, *, key="request-001", quantity="10"):
    """Create a draft invoice using standard test inputs."""
    return create_draft(
        session,
        business_id=context["business_id"],
        family_id=context["family_id"],
        period_start=date(2025, 1, 1),
        period_end=date(2025, 1, 31),
        idempotency_key=key,
        lines=[billing_line(context["child_id"], quantity)],
    )


def test_create_draft_persists_calculated_snapshot(session, invoice_context):
    """Draft creation stores the calculated lines and invoice total."""
    invoice = make_draft(session, invoice_context)

    assert invoice.status == "draft"
    assert invoice.invoice_number is None
    assert invoice.issued_at is None
    assert invoice.total_pence == 7500
    assert len(invoice.lines) == 1
    assert invoice.lines[0].amount_pence == 7500

    invoice_id = invoice.id
    session.flush()
    session.expire_all()

    persisted = session.get(Invoice, invoice_id)
    assert persisted is not None
    assert persisted.total_pence == 7500


def test_duplicate_request_returns_existing_draft(session, invoice_context):
    """Repeating the same request returns the existing invoice."""
    first = make_draft(session, invoice_context)
    second = make_draft(session, invoice_context)

    assert second.id == first.id

    invoices = session.scalars(
        select(Invoice).where(
            Invoice.business_id == invoice_context["business_id"],
            Invoice.idempotency_key == "request-001",
        )
    ).all()
    assert len(invoices) == 1


def test_reused_idempotency_key_with_different_content_conflicts(
    session, invoice_context
):
    """An idempotency key cannot be reused for different invoice content."""
    make_draft(session, invoice_context)

    with pytest.raises(IdempotencyConflict):
        make_draft(session, invoice_context, quantity="12")


def test_recalculate_draft_replaces_lines_and_total(session, invoice_context):
    """Recalculation replaces draft lines and updates the total."""
    invoice = make_draft(session, invoice_context)

    updated = recalculate_draft(
        session,
        business_id=invoice_context["business_id"],
        invoice_id=invoice.id,
        lines=[billing_line(invoice_context["child_id"], "12")],
    )

    assert updated.total_pence == 9000
    assert len(updated.lines) == 1
    assert updated.lines[0].quantity == Decimal("12")
    assert updated.lines[0].amount_pence == 9000


def test_issued_invoice_cannot_be_recalculated(session, invoice_context):
    """An issued invoice cannot be recalculated as a draft."""
    invoice = make_draft(session, invoice_context)

    issue_invoice(
        session,
        business_id=invoice_context["business_id"],
        invoice_id=invoice.id,
        issued_at=datetime(2025, 2, 1, tzinfo=timezone.utc),
    )

    with pytest.raises(InvoiceServiceError, match="Only draft"):
        recalculate_draft(
            session,
            business_id=invoice_context["business_id"],
            invoice_id=invoice.id,
            lines=[billing_line(invoice_context["child_id"], "12")],
        )


def test_issue_invoice_assigns_number_and_timestamp(session, invoice_context):
    """Issuance assigns an invoice number and timestamp."""
    invoice = make_draft(session, invoice_context)
    issued_at = datetime(2025, 2, 1, tzinfo=timezone.utc)

    issued = issue_invoice(
        session,
        business_id=invoice_context["business_id"],
        invoice_id=invoice.id,
        issued_at=issued_at,
    )

    assert issued.status == "issued"
    assert issued.invoice_number == "INV-2025-000001"
    assert issued.issued_at == issued_at
    assert issued.total_pence == 7500

    with pytest.raises(InvoiceServiceError, match="Only draft"):
        issue_invoice(
            session,
            business_id=invoice_context["business_id"],
            invoice_id=invoice.id,
        )


def test_issued_invoice_snapshot_survives_contract_rate_change(
    session, invoice_context
):
    """Changing a contract rate does not rewrite an issued invoice."""
    invoice = make_draft(session, invoice_context)

    issue_invoice(
        session,
        business_id=invoice_context["business_id"],
        invoice_id=invoice.id,
        issued_at=datetime(2025, 2, 1, tzinfo=timezone.utc),
    )

    original_amount = invoice.lines[0].amount_pence
    original_rate = invoice.lines[0].unit_rate

    contract = session.scalar(
        select(Contract).where(
            Contract.business_id == invoice_context["business_id"],
            Contract.family_id == invoice_context["family_id"],
        )
    )
    assert contract is not None

    contract.rate_amount = Decimal("9.00")
    session.flush()
    session.expire(invoice, ["lines"])

    assert invoice.lines[0].amount_pence == original_amount
    assert invoice.lines[0].unit_rate == original_rate
    assert invoice.total_pence == 7500


def test_correction_preserves_original_invoice(session, invoice_context):
    """A correction is separate from the original issued invoice."""
    invoice = make_draft(session, invoice_context)

    issue_invoice(
        session,
        business_id=invoice_context["business_id"],
        invoice_id=invoice.id,
        issued_at=datetime(2025, 2, 1, tzinfo=timezone.utc),
    )
    original_total = invoice.total_pence

    correction = record_correction(
        session,
        business_id=invoice_context["business_id"],
        invoice_id=invoice.id,
        correction_type="credit",
        reason="Documented childcare adjustment",
        amount_pence=500,
    )

    assert correction.original_invoice_id == invoice.id
    assert correction.amount_pence == 500
    assert invoice.total_pence == original_total
    assert invoice.status == "issued"

    persisted = session.get(InvoiceCorrection, correction.id)
    assert persisted is not None
    assert persisted.reason == "Documented childcare adjustment"


def test_correction_rejects_draft_invoice(session, invoice_context):
    """A correction cannot be recorded against a draft invoice."""
    invoice = make_draft(session, invoice_context)

    with pytest.raises(InvoiceServiceError, match="issued invoices"):
        record_correction(
            session,
            business_id=invoice_context["business_id"],
            invoice_id=invoice.id,
            correction_type="credit",
            reason="Test correction",
            amount_pence=500,
        )


def test_draft_rejects_child_from_another_family(session, invoice_context):
    """Invoice lines cannot reference children outside the invoice family."""
    business = session.get(Business, invoice_context["business_id"])
    assert business is not None

    other_family = Family(name="Another Family", business=business)
    other_child = Child(
        name="Other Child",
        business=business,
        family=other_family,
    )
    session.add(other_child)
    session.flush()

    with pytest.raises(InvoiceServiceError, match="invoice family"):
        create_draft(
            session,
            business_id=invoice_context["business_id"],
            family_id=invoice_context["family_id"],
            period_start=date(2025, 1, 1),
            period_end=date(2025, 1, 31),
            idempotency_key="wrong-child",
            lines=[billing_line(other_child.id)],
        )