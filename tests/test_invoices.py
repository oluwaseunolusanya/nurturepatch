
"""Test invoice lifecycle operations against PostgreSQL."""

from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from decimal import Decimal
from threading import Barrier

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

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
    """Recording a correction does not alter the original invoice."""
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
        amount_pence=1500,
        reason="Adjustment agreed with the family",
    )

    assert isinstance(correction, InvoiceCorrection)
    assert correction.amount_pence == 1500
    assert correction.correction_type == "credit"
    assert invoice.total_pence == original_total
    assert invoice.status == "issued"


def test_correction_rejects_draft_invoice(session, invoice_context):
    """A correction cannot be recorded against a draft invoice."""
    invoice = make_draft(session, invoice_context)

    with pytest.raises(InvoiceServiceError):
        record_correction(
            session,
            business_id=invoice_context["business_id"],
            invoice_id=invoice.id,
            correction_type="credit",
            amount_pence=1500,
            reason="Correction against a draft",
        )


def test_draft_rejects_child_from_another_family(session, invoice_context):
    """A draft cannot include a child belonging to another family."""
    other_family = Family(
        name="Another Family",
        business_id=invoice_context["business_id"],
    )
    other_child = Child(
        name="Another Child",
        business_id=invoice_context["business_id"],
        family=other_family,
    )
    session.add(other_child)
    session.flush()

    with pytest.raises(InvoiceServiceError):
        create_draft(
            session,
            business_id=invoice_context["business_id"],
            family_id=invoice_context["family_id"],
            period_start=date(2025, 1, 1),
            period_end=date(2025, 1, 31),
            idempotency_key="wrong-family-child",
            lines=[billing_line(other_child.id)],
        )


def test_concurrent_duplicate_requests_create_one_invoice(
    session, invoice_context
):
    """Concurrent requests with the same key return one invoice."""
    context = invoice_context
    engine = session.get_bind()
    barrier = Barrier(2)

    # Commit setup data so independent worker sessions can see it.
    session.commit()

    def create_concurrently():
        with Session(engine) as worker_session:
            barrier.wait(timeout=10)
            invoice = make_draft(worker_session, context)
            invoice_id = invoice.id
            worker_session.commit()
            return invoice_id

    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(create_concurrently)
        second = executor.submit(create_concurrently)
        first_id = first.result(timeout=30)
        second_id = second.result(timeout=30)

    assert first_id == second_id

    with Session(engine) as verification_session:
        invoices = verification_session.scalars(
            select(Invoice).where(
                Invoice.business_id == context["business_id"],
                Invoice.idempotency_key == "request-001",
            )
        ).all()

        assert len(invoices) == 1


def test_concurrent_issuance_assigns_unique_invoice_numbers(
    session, invoice_context
):
    """Concurrent issuance assigns distinct invoice numbers."""
    context = invoice_context
    engine = session.get_bind()
    barrier = Barrier(2)

    first_draft = make_draft(session, context, key="concurrent-001")
    second_draft = make_draft(session, context, key="concurrent-002")
    invoice_ids = [first_draft.id, second_draft.id]

    # Make both drafts visible to independent worker sessions.
    session.commit()

    def issue_concurrently(invoice_id):
        with Session(engine) as worker_session:
            barrier.wait(timeout=10)
            invoice = issue_invoice(
                worker_session,
                business_id=context["business_id"],
                invoice_id=invoice_id,
                issued_at=datetime(2025, 2, 1, tzinfo=timezone.utc),
            )
            invoice_number = invoice.invoice_number
            worker_session.commit()
            return invoice_number

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = [
            executor.submit(issue_concurrently, invoice_id)
            for invoice_id in invoice_ids
        ]
        invoice_numbers = [
            result.result(timeout=30) for result in results
        ]

    assert len(set(invoice_numbers)) == 2
    assert set(invoice_numbers) == {
        "INV-2025-000001",
        "INV-2025-000002",
    }
