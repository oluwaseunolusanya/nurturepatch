
"""Manage invoice drafts, issuance, idempotency, and corrections.

This service coordinates database persistence with the pure billing engine.
Callers own transaction commit and rollback so invoice operations can be
combined atomically with surrounding application work.
"""

from collections.abc import Sequence
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    Business,
    Child,
    Family,
    Invoice,
    InvoiceCorrection,
    InvoiceLine,
)
from app.services.billing import (
    BillingError,
    BillingLineInput,
    InvoiceCalculation,
    calculate_invoice,
)


class InvoiceServiceError(ValueError):
    """Represent an invalid invoice lifecycle operation."""


class IdempotencyConflict(InvoiceServiceError):
    """Represent reuse of an idempotency key for different content."""


def _normalise_child_id(child_id: str | None) -> int | None:
    """Convert a billing input child identifier to its database integer ID.

    Args:
        child_id: Optional child identifier from a billing line.

    Returns:
        The integer child ID, or None when the line has no child.

    Raises:
        InvoiceServiceError: If the identifier is not a positive integer
            represented as a string.
    """
    if child_id is None:
        return None

    try:
        result = int(child_id)
    except (TypeError, ValueError) as exc:
        raise InvoiceServiceError(
            "child_id must be a valid integer ID."
        ) from exc

    if result <= 0 or str(result) != child_id:
        raise InvoiceServiceError("child_id must be a positive integer ID.")

    return result


def _validate_scope(
    session: Session,
    business_id: int,
    family_id: int,
    lines: Sequence[BillingLineInput],
) -> None:
    """Validate that the family and referenced children belong to the business.

    Args:
        session: Active SQLAlchemy session.
        business_id: Tenant business ID.
        family_id: Invoice family ID.
        lines: Billing lines being persisted.

    Raises:
        InvoiceServiceError: If the family or a child is outside the
            requested business or family.
    """
    family = session.scalar(
        select(Family).where(
            Family.id == family_id,
            Family.business_id == business_id,
        )
    )
    if family is None:
        raise InvoiceServiceError("Family does not belong to this business.")

    for line in lines:
        child_id = _normalise_child_id(line.child_id)
        if child_id is None:
            continue

        child = session.scalar(
            select(Child).where(
                Child.id == child_id,
                Child.business_id == business_id,
                Child.family_id == family_id,
            )
        )
        if child is None:
            raise InvoiceServiceError(
                "Every invoice child must belong to the invoice family "
                "and business."
            )


def _build_line_rows(
    business_id: int,
    calculation: InvoiceCalculation,
) -> list[InvoiceLine]:
    """Create persistent invoice line snapshots from a billing calculation.

    Args:
        business_id: Tenant business ID.
        calculation: Result returned by the billing engine.

    Returns:
        Invoice line ORM objects ready to attach to an invoice.
    """
    rows: list[InvoiceLine] = []

    for calculated in calculation.lines:
        inputs = calculated.inputs
        rows.append(
            InvoiceLine(
                business_id=business_id,
                child_id=_normalise_child_id(inputs.child_id),
                description=inputs.description,
                line_type=inputs.line_type.value,
                quantity=inputs.quantity,
                unit=inputs.unit,
                unit_rate=inputs.unit_rate,
                amount_pence=calculated.displayed_amount_pence,
                adjustment_reason=inputs.adjustment_reason,
                deduction_evidence=inputs.deduction_evidence,
            )
        )

    return rows


def _line_matches_input(
    stored: InvoiceLine,
    supplied: BillingLineInput,
) -> bool:
    """Compare persisted line fields with a repeated billing request."""
    return (
        stored.child_id == _normalise_child_id(supplied.child_id)
        and stored.description == supplied.description
        and stored.line_type == supplied.line_type.value
        and stored.quantity == supplied.quantity
        and stored.unit == supplied.unit
        and stored.unit_rate == supplied.unit_rate
        and stored.adjustment_reason == supplied.adjustment_reason
        and stored.deduction_evidence == supplied.deduction_evidence
    )


def _matches_request(
    session: Session,
    invoice: Invoice,
    family_id: int,
    period_start: date,
    period_end: date,
    lines: Sequence[BillingLineInput],
) -> bool:
    """Determine whether an existing invoice matches a repeated request."""
    if (
        invoice.family_id != family_id
        or invoice.period_start != period_start
        or invoice.period_end != period_end
    ):
        return False

    stored_lines = list(
        session.scalars(
            select(InvoiceLine)
            .where(
                InvoiceLine.business_id == invoice.business_id,
                InvoiceLine.invoice_id == invoice.id,
            )
            .order_by(InvoiceLine.id)
        )
    )

    return len(stored_lines) == len(lines) and all(
        _line_matches_input(stored, supplied)
        for stored, supplied in zip(stored_lines, lines, strict=True)
    )


def _calculate(lines: Sequence[BillingLineInput]) -> InvoiceCalculation:
    """Calculate invoice totals and translate billing validation errors.

    Args:
        lines: Billing inputs to calculate.

    Returns:
        The calculated invoice amounts and line snapshots.

    Raises:
        InvoiceServiceError: If a billing input is invalid.
    """
    try:
        return calculate_invoice(lines)
    except BillingError as exc:
        raise InvoiceServiceError(str(exc)) from exc


def create_draft(
    session: Session,
    *,
    business_id: int,
    family_id: int,
    period_start: date,
    period_end: date,
    idempotency_key: str,
    lines: Sequence[BillingLineInput],
) -> Invoice:
    """Create a draft or return the equivalent invoice from a repeated request.

    A business-level row lock serialises draft creation for that business.
    The caller owns the transaction and must commit or roll it back.

    Args:
        session: Active SQLAlchemy session.
        business_id: Tenant business ID.
        family_id: Invoice family ID.
        period_start: First date covered by the invoice.
        period_end: Last date covered by the invoice.
        idempotency_key: Client-generated key unique within the business.
        lines: Billing inputs to calculate and snapshot.

    Returns:
        The newly created draft or the equivalent existing invoice.

    Raises:
        InvoiceServiceError: If the business or request is invalid.
        IdempotencyConflict: If the key belongs to a different request.
    """
    if period_end < period_start:
        raise InvoiceServiceError(
            "period_end must not precede period_start."
        )

    if not idempotency_key or not idempotency_key.strip():
        raise InvoiceServiceError("idempotency_key must not be empty.")

    if len(idempotency_key) > 200:
        raise InvoiceServiceError(
            "idempotency_key exceeds 200 characters."
        )

    # Acquire the same tenant-level lock used by invoice issuance.
    # PostgreSQL holds this lock until the transaction ends.
    business = session.scalar(
        select(Business)
        .where(Business.id == business_id)
        .with_for_update()
    )
    if business is None:
        raise InvoiceServiceError("Business not found.")

    calculation = _calculate(lines)

    existing = session.scalar(
        select(Invoice).where(
            Invoice.business_id == business_id,
            Invoice.idempotency_key == idempotency_key,
        )
    )

    if existing is not None:
        if _matches_request(
            session,
            existing,
            family_id,
            period_start,
            period_end,
            lines,
        ):
            return existing

        raise IdempotencyConflict(
            "This idempotency key was already used for a different request."
        )

    _validate_scope(session, business_id, family_id, lines)

    invoice = Invoice(
        business_id=business_id,
        family_id=family_id,
        period_start=period_start,
        period_end=period_end,
        status="draft",
        invoice_number=None,
        idempotency_key=idempotency_key,
        total_pence=calculation.total_pence,
        lines=_build_line_rows(business_id, calculation),
    )

    session.add(invoice)
    session.flush()

    return invoice


def recalculate_draft(
    session: Session,
    *,
    business_id: int,
    invoice_id: int,
    lines: Sequence[BillingLineInput],
) -> Invoice:
    """Replace draft line snapshots and recalculate the invoice total.

    Args:
        session: Active SQLAlchemy session.
        business_id: Tenant business ID.
        invoice_id: Invoice to recalculate.
        lines: Replacement billing inputs.

    Returns:
        The updated draft invoice.

    Raises:
        InvoiceServiceError: If the invoice is missing, not a draft, or
            contains invalid billing inputs.
    """
    invoice = session.scalar(
        select(Invoice)
        .where(
            Invoice.id == invoice_id,
            Invoice.business_id == business_id,
        )
        .with_for_update()
    )

    if invoice is None:
        raise InvoiceServiceError("Invoice not found in this business.")

    if invoice.status != "draft":
        raise InvoiceServiceError("Only draft invoices can be recalculated.")

    _validate_scope(session, business_id, invoice.family_id, lines)
    calculation = _calculate(lines)

    invoice.lines.clear()
    invoice.lines.extend(_build_line_rows(business_id, calculation))
    invoice.total_pence = calculation.total_pence

    session.flush()

    return invoice


def issue_invoice(
    session: Session,
    *,
    business_id: int,
    invoice_id: int,
    issued_at: datetime | None = None,
) -> Invoice:
    """Assign an invoice number and issue a draft within the current transaction.

    Args:
        session: Active SQLAlchemy session.
        business_id: Tenant business ID.
        invoice_id: Draft invoice to issue.
        issued_at: Optional timezone-aware issue timestamp.

    Returns:
        The issued invoice with its number and timestamp.

    Raises:
        InvoiceServiceError: If the business or invoice is missing, the
            invoice has already been issued, it has no lines, or its
            timestamp is invalid.
    """
    business = session.scalar(
        select(Business)
        .where(Business.id == business_id)
        .with_for_update()
    )

    if business is None:
        raise InvoiceServiceError("Business not found.")

    invoice = session.scalar(
        select(Invoice)
        .where(
            Invoice.id == invoice_id,
            Invoice.business_id == business_id,
        )
        .with_for_update()
    )

    if invoice is None:
        raise InvoiceServiceError("Invoice not found in this business.")

    if invoice.status != "draft":
        raise InvoiceServiceError("Only draft invoices can be issued.")

    if not invoice.lines:
        raise InvoiceServiceError("Cannot issue an invoice without lines.")

    timestamp = issued_at or datetime.now(timezone.utc)

    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise InvoiceServiceError("issued_at must be timezone-aware.")

    prefix = f"INV-{timestamp.year}-"

    existing_numbers = session.scalars(
        select(Invoice.invoice_number).where(
            Invoice.business_id == business_id,
            Invoice.invoice_number.like(f"{prefix}%"),
        )
    ).all()

    sequences: list[int] = []

    for number in existing_numbers:
        if number is None:
            continue

        suffix = number.removeprefix(prefix)
        if suffix.isdigit():
            sequences.append(int(suffix))

    next_sequence = max(sequences, default=0) + 1

    invoice.invoice_number = f"{prefix}{next_sequence:06d}"
    invoice.issued_at = timestamp
    invoice.status = "issued"

    session.flush()

    return invoice


def record_correction(
    session: Session,
    *,
    business_id: int,
    invoice_id: int,
    correction_type: str,
    reason: str,
    amount_pence: int,
    created_at: datetime | None = None,
) -> InvoiceCorrection:
    """Record a correction without modifying the original invoice snapshot.

    Args:
        session: Active SQLAlchemy session.
        business_id: Tenant business ID.
        invoice_id: Original issued invoice ID.
        correction_type: Either ``credit`` or ``correction``.
        reason: Explanation retained with the correction record.
        amount_pence: Positive amount represented by the correction.
        created_at: Optional timezone-aware creation timestamp.

    Returns:
        The newly recorded correction.

    Raises:
        InvoiceServiceError: If the invoice is not issued or any correction
            field is invalid.
    """
    if correction_type not in {"credit", "correction"}:
        raise InvoiceServiceError(
            "correction_type must be 'credit' or 'correction'."
        )

    if not reason or not reason.strip():
        raise InvoiceServiceError("A correction reason is required.")

    if len(reason) > 500:
        raise InvoiceServiceError(
            "Correction reason exceeds 500 characters."
        )

    if isinstance(amount_pence, bool) or not isinstance(amount_pence, int):
        raise InvoiceServiceError("amount_pence must be an integer.")

    if amount_pence <= 0:
        raise InvoiceServiceError(
            "amount_pence must be greater than zero."
        )

    invoice = session.scalar(
        select(Invoice)
        .where(
            Invoice.id == invoice_id,
            Invoice.business_id == business_id,
        )
        .with_for_update()
    )

    if invoice is None:
        raise InvoiceServiceError("Invoice not found in this business.")

    if invoice.status != "issued":
        raise InvoiceServiceError(
            "Corrections can only be recorded against issued invoices."
        )

    timestamp = created_at or datetime.now(timezone.utc)

    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise InvoiceServiceError(
            "created_at must be timezone-aware."
        )

    correction = InvoiceCorrection(
        business_id=business_id,
        original_invoice_id=invoice.id,
        correction_type=correction_type,
        reason=reason.strip(),
        amount_pence=amount_pence,
        created_at=timestamp,
    )

    session.add(correction)
    session.flush()

    return correction
