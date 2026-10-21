"""Pure billing calculation models.

This module contains the data structures used by the billing engine.
It must remain independent of HTTP, database, and cloud infrastructure.

Financial policy:
- Use Decimal for intermediate monetary calculations, never float.
- Keep authoritative payable totals in integer pence.
- Sum exact line amounts before rounding the invoice total.
- Reconcile displayed line amounts to the authoritative total when needed.

The canonical rationale and rounding examples are documented in
docs/decisions/0001-billing-money-and-rounding.md.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum


class BillingError(ValueError):
    """Raised when billing input violates a calculation rule."""


class LineType(str, Enum):
    """Identify the business purpose of an invoice line."""

    CONTRACTED_HOURS = "contracted_hours"
    ADDITIONAL_HOURS = "additional_hours"
    SERVICE = "service"
    ADJUSTMENT = "adjustment"


class ServiceUnit(str, Enum):
    """Define the supported units for additional services."""

    TRIP = "trip"
    DAY = "day"
    MEAL = "meal"
    FIXED_FEE = "fixed_fee"


@dataclass(frozen=True)
class BillingLineInput:
    """Capture the inputs needed to calculate one invoice line.

    Decimal values are used to avoid introducing binary floating-point
    errors. Validation of quantities, rates, units, and adjustments is
    performed by the billing service before calculating an amount.
    """

    description: str
    line_type: LineType
    quantity: Decimal
    unit_rate: Decimal
    unit: str
    child_id: str | None = None
    adjustment_reason: str | None = None
    contract_permits_deduction: bool = False
    deduction_evidence: str | None = None


@dataclass(frozen=True)
class CalculatedLine:
    """Preserve a line's inputs and calculated monetary representations.

    exact_amount retains the intermediate amount before monetary rounding.
    displayed_amount_pence represents the line amount shown to the user,
    rounded to two decimal places and represented in integer pence.
    """

    inputs: BillingLineInput
    exact_amount: Decimal
    displayed_amount_pence: int


@dataclass(frozen=True)
class InvoiceCalculation:
    """Represent the invoice calculation and its display reconciliation.

    total_pence is the authoritative payable total. The rounding adjustment
    reconciles displayed line amounts with that total; it must not change
    the underlying exact line calculations.
    """

    lines: tuple[CalculatedLine, ...]
    exact_subtotal: Decimal
    total_pence: int
    rounding_adjustment_pence: int


def _require_decimal(value: Decimal, field_name: str) -> Decimal:
    """Validate that a numeric input is a finite Decimal.

    Args:
        value: The value to validate.
        field_name: The input field name used in error messages.

    Returns:
        The validated Decimal value, unchanged.

    Raises:
        BillingError: If value is not a Decimal or is not finite.
    """
    if not isinstance(value, Decimal):
        raise BillingError(f"{field_name} must be a Decimal.")

    if not value.is_finite():
        raise BillingError(f"{field_name} must be finite.")

    return value


def validate_billing_line(line: BillingLineInput) -> None:
    """Validate a billing line before calculating its monetary amount.

    Ordinary charges require a positive quantity and non-negative rate.
    Adjustments may be positive or negative, but must have a reason.
    Negative adjustments additionally require contract permission and
    supporting evidence.

    Args:
        line: The billing line input to validate.

    Returns:
        None if the input satisfies all validation rules.

    Raises:
        BillingError: If the line contains invalid or unsupported input.
    """
    if not isinstance(line, BillingLineInput):
        raise BillingError("line must be a BillingLineInput.")

    if not isinstance(line.description, str) or not line.description.strip():
        raise BillingError("description must not be empty.")

    if not isinstance(line.line_type, LineType):
        raise BillingError("line_type is unsupported.")

    quantity = _require_decimal(line.quantity, "quantity")
    rate = _require_decimal(line.unit_rate, "unit_rate")

    if quantity <= 0:
        raise BillingError("quantity must be greater than zero.")

    if line.line_type == LineType.ADJUSTMENT:
        if line.unit != "adjustment":
            raise BillingError("adjustment lines must use unit 'adjustment'.")

        if quantity != Decimal("1"):
            raise BillingError("adjustment quantity must be 1.")

        if not line.adjustment_reason or not line.adjustment_reason.strip():
            raise BillingError("adjustments require a recorded reason.")

        if rate == 0:
            raise BillingError("adjustment amount must not be zero.")

        if rate < 0:
            if not line.contract_permits_deduction:
                raise BillingError("deductions require explicit contract permission.")

            if not line.deduction_evidence or not line.deduction_evidence.strip():
                raise BillingError("deductions require recorded supporting evidence.")

        return

    if rate < 0:
        raise BillingError("unit_rate must not be negative.")

    if line.line_type == LineType.SERVICE:
        try:
            unit = ServiceUnit(line.unit)
        except (TypeError, ValueError) as exc:
            raise BillingError("service unit is unsupported.") from exc

        if unit == ServiceUnit.FIXED_FEE and quantity != Decimal("1"):
            raise BillingError("fixed-fee services must have quantity 1.")

        if quantity != quantity.to_integral_value():
            raise BillingError("service quantities must be whole numbers.")

    elif line.line_type in (
        LineType.CONTRACTED_HOURS,
        LineType.ADDITIONAL_HOURS,
    ):
        if line.unit != "hour":
            raise BillingError("childcare-hour lines must use unit 'hour'.")


def calculate_billing_line(line: BillingLineInput) -> CalculatedLine:
    """Calculate the exact and displayed amounts for one billing line.

    Args:
        line: The billing line input to validate and calculate.

    Returns:
        The calculated line with its exact amount and displayed amount
        in integer pence.

    Raises:
        BillingError: If the billing line contains invalid input.
    """
    validate_billing_line(line)

    exact_amount = line.quantity * line.unit_rate

    displayed_amount = exact_amount.quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )

    displayed_amount_pence = int(displayed_amount * 100)

    return CalculatedLine(
        inputs=line,
        exact_amount=exact_amount,
        displayed_amount_pence=displayed_amount_pence,
    )


def calculate_invoice(
    lines: Sequence[BillingLineInput],
) -> InvoiceCalculation:
    """Calculate an invoice total from its billing lines.

    Sum exact line amounts before rounding the authoritative invoice total.
    Reconcile displayed line amounts with the total when necessary.

    Args:
        lines: The billing lines to validate and calculate.

    Returns:
        The calculated lines, exact subtotal, total in integer pence,
        and display rounding adjustment in pence.

    Raises:
        BillingError: If no lines are provided or a line is invalid.
    """
    if not isinstance(lines, Sequence) or isinstance(lines, (str, bytes)):
        raise BillingError("lines must be a sequence of billing lines.")

    if not lines:
        raise BillingError("invoice must contain at least one billing line.")

    calculated_lines = tuple(calculate_billing_line(line) for line in lines)

    exact_subtotal = sum(
        (line.exact_amount for line in calculated_lines),
        start=Decimal("0"),
    )

    rounded_total = exact_subtotal.quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )
    total_pence = int(rounded_total * 100)

    displayed_lines_total_pence = sum(
        line.displayed_amount_pence for line in calculated_lines
    )

    rounding_adjustment_pence = total_pence - displayed_lines_total_pence

    return InvoiceCalculation(
        lines=calculated_lines,
        exact_subtotal=exact_subtotal,
        total_pence=total_pence,
        rounding_adjustment_pence=rounding_adjustment_pence,
    )
