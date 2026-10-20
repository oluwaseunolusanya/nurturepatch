
"""Tests for billing input validation and calculation rules."""

from decimal import Decimal

import pytest

from app.services.billing import (
    BillingError,
    BillingLineInput,
    LineType,
    ServiceUnit,
    validate_billing_line,
    calculate_billing_line,
)


def make_line(**overrides: object) -> BillingLineInput:
    """Create a valid default billing line for validation tests.

    Args:
        **overrides: Fields that should replace the default input values.

    Returns:
        A billing line input suitable for use as a test fixture.
    """
    values: dict[str, object] = {
        "description": "Contracted childcare",
        "line_type": LineType.CONTRACTED_HOURS,
        "quantity": Decimal("10"),
        "unit_rate": Decimal("5.00"),
        "unit": "hour",
    }
    values.update(overrides)
    return BillingLineInput(**values)  # type: ignore[arg-type]


def test_valid_contracted_hours_are_accepted() -> None:
    """Accept a valid contracted-hours line."""
    line = make_line()
    validate_billing_line(line)


@pytest.mark.parametrize(
    "quantity",
    [
        Decimal("0"),
        Decimal("-1"),
        Decimal("NaN"),
        Decimal("Infinity"),
    ],
)
def test_invalid_quantities_are_rejected(quantity: Decimal) -> None:
    """Reject zero, negative, and non-finite quantities."""
    line = make_line(quantity=quantity)

    with pytest.raises(BillingError):
        validate_billing_line(line)


@pytest.mark.parametrize(
    "unit_rate",
    [
        Decimal("-0.01"),
        Decimal("NaN"),
        Decimal("Infinity"),
    ],
)
def test_invalid_rates_are_rejected(unit_rate: Decimal) -> None:
    """Reject negative and non-finite rates."""
    line = make_line(unit_rate=unit_rate)

    with pytest.raises(BillingError):
        validate_billing_line(line)


def test_float_quantity_is_rejected() -> None:
    """Reject binary floating-point quantities."""
    line = make_line(quantity=10.0)

    with pytest.raises(BillingError, match="quantity must be a Decimal"):
        validate_billing_line(line)


def test_float_rate_is_rejected() -> None:
    """Reject binary floating-point rates."""
    line = make_line(unit_rate=5.00)

    with pytest.raises(BillingError, match="unit_rate must be a Decimal"):
        validate_billing_line(line)


@pytest.mark.parametrize(
    "unit",
    [
        ServiceUnit.TRIP.value,
        ServiceUnit.DAY.value,
        ServiceUnit.MEAL.value,
        ServiceUnit.FIXED_FEE.value,
    ],
)
def test_supported_service_units_are_accepted(unit: str) -> None:
    """Accept supported additional-service units."""
    quantity = Decimal("1") if unit == ServiceUnit.FIXED_FEE.value else Decimal("2")
    line = make_line(
        line_type=LineType.SERVICE,
        quantity=quantity,
        unit=unit,
    )

    validate_billing_line(line)


def test_fixed_fee_service_requires_quantity_one() -> None:
    """Reject fixed-fee services with a quantity other than one."""
    line = make_line(
        line_type=LineType.SERVICE,
        quantity=Decimal("2"),
        unit=ServiceUnit.FIXED_FEE.value,
    )

    with pytest.raises(BillingError, match="fixed-fee services must have quantity 1"):
        validate_billing_line(line)


def test_unsupported_service_unit_is_rejected() -> None:
    """Reject additional services with unsupported units."""
    line = make_line(
        line_type=LineType.SERVICE,
        unit="week",
    )

    with pytest.raises(BillingError, match="service unit is unsupported"):
        validate_billing_line(line)


def test_fractional_service_quantity_is_rejected() -> None:
    """Reject fractional quantities for additional services."""
    line = make_line(
        line_type=LineType.SERVICE,
        quantity=Decimal("1.5"),
        unit=ServiceUnit.TRIP.value,
    )

    with pytest.raises(BillingError, match="service quantities must be whole numbers"):
        validate_billing_line(line)


def test_adjustment_requires_a_reason() -> None:
    """Reject adjustments without a recorded reason."""
    line = make_line(
        line_type=LineType.ADJUSTMENT,
        quantity=Decimal("1"),
        unit="adjustment",
        adjustment_reason=" ",
    )

    with pytest.raises(BillingError, match="recorded reason"):
        validate_billing_line(line)


def test_deduction_requires_contract_permission() -> None:
    """Reject deductions without explicit contract permission."""
    line = make_line(
        line_type=LineType.ADJUSTMENT,
        quantity=Decimal("1"),
        unit="adjustment",
        unit_rate=Decimal("-5.00"),
        adjustment_reason="Missed hours",
        contract_permits_deduction=False,
        deduction_evidence="Attendance record",
    )

    with pytest.raises(BillingError, match="contract permission"):
        validate_billing_line(line)


def test_deduction_requires_evidence() -> None:
    """Reject deductions without supporting evidence."""
    line = make_line(
        line_type=LineType.ADJUSTMENT,
        quantity=Decimal("1"),
        unit="adjustment",
        unit_rate=Decimal("-5.00"),
        adjustment_reason="Missed hours",
        contract_permits_deduction=True,
        deduction_evidence=" ",
    )

    with pytest.raises(BillingError, match="supporting evidence"):
        validate_billing_line(line)


def test_deduction_with_permission_and_evidence_is_accepted() -> None:
    """Accept deductions with permission, a reason, and evidence."""
    line = make_line(
        line_type=LineType.ADJUSTMENT,
        quantity=Decimal("1"),
        unit="adjustment",
        unit_rate=Decimal("-5.00"),
        adjustment_reason="Missed hours",
        contract_permits_deduction=True,
        deduction_evidence="Attendance record",
    )

    validate_billing_line(line)


def test_calculate_billing_line_returns_exact_and_displayed_amounts() -> None:
    """Calculate a line while preserving its exact monetary amount."""
    line = make_line(
        quantity=Decimal("2.5"),
        unit_rate=Decimal("8.20"),
    )

    result = calculate_billing_line(line)

    assert result.inputs == line
    assert result.exact_amount == Decimal("20.500")
    assert result.displayed_amount_pence == 2050


def test_calculate_billing_line_rounds_half_up() -> None:
    """Round a displayed line amount half up to the nearest penny."""
    line = make_line(
        quantity=Decimal("1"),
        unit_rate=Decimal("1.005"),
    )

    result = calculate_billing_line(line)

    assert result.exact_amount == Decimal("1.005")
    assert result.displayed_amount_pence == 101


def test_calculate_billing_line_rejects_invalid_input() -> None:
    """Do not calculate a line that fails validation."""
    line = make_line(quantity=Decimal("0"))

    with pytest.raises(
        BillingError,
        match="quantity must be greater than zero",
    ):
        calculate_billing_line(line)