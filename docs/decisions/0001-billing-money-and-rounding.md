
# Decision 0001: Billing Money and Rounding

## Status

**Accepted for implementation, subject to technical validation and production compliance checks.**

The childminder has confirmed these business rules:

1. Childcare-hour billing follows the applicable family's contract.

2. Trips, days and meals use whole-number quantities. Fixed-fee services use a quantity of one.

3. Exact line amounts are summed before the invoice total is rounded once using `ROUND_HALF_UP`.

4. When displayed line amounts do not add up to the authoritative invoice total, a clearly labelled rounding-adjustment line reconciles the difference.

These decisions do not imply approval of unverified legal, accounting, childcare-funding or local-authority requirements.

## 1. Context

NurturePatch calculates monthly childcare invoices for families with different contractual arrangements and rates. An invoice may include multiple children, contracted hours, additional hours, extra services and permitted adjustments.

Calculations must be deterministic, auditable and testable. The invoice must show a consistent total, and its issued version must remain unchanged even if rates or other records subsequently change.

## 2. Monetary representation

- Use GBP as the initial currency.

- Store authoritative payable monetary amounts as integer pence.

- Use Python `Decimal` for intermediate monetary calculations.

- Never use binary floating-point arithmetic for currency calculations.

- Parse monetary inputs from strings or other exact representations, not binary floats.

- Define and enforce appropriate numeric precision and range limits before accepting production inputs.

Integer pence provides reliable storage and comparison of payable amounts. `Decimal` supports exact intermediate calculations where amounts may contain fractions of a penny.

## 3. Quantity and rate rules

### Childcare hours

- Apply the billing rules specified by the relevant family's contract.

- Do not assume a universal rule for partial hours, billing increments or minimum bookings.

- Validate quantities against the applicable contract and documented system limits.

### Additional services

- Trips, days and meals use whole-number quantities.

- Fixed-fee services use a quantity of one.

- Each service line records its description, quantity, unit, applicable rate and calculation inputs.

- Rates must reflect the applicable family agreement or other authorised pricing arrangement.

### Adjustments and missed hours

- Adjustments must have a defined type, amount and recorded reason.

- Missed-hour deductions are permitted only when the applicable contract allows them and the required reason and supporting evidence are recorded.

- Do not automatically deduct charges for missed hours.

- Validate adjustment permissions and amounts against documented business rules.

- Correct issued invoices through an authorised correction or credit-note process, not by silently changing the original invoice.

## 4. Rounding policy

The confirmed business rule is **aggregate-first rounding**.

1. Calculate each invoice line using exact intermediate values.

2. Sum the exact line amounts without first rounding each line to integer pence.

3. Apply `ROUND_HALF_UP` once to the aggregate invoice amount, at two decimal places in GBP.

4. Convert the final rounded invoice total to integer pence.

5. Use that integer-pence amount as the authoritative invoice total.

Do not replace this policy with line-by-line rounding before aggregation.

### Example

Two lines each calculate to £1.005.

- Exact aggregate: £1.005 + £1.005 = £2.010.

- Rounded invoice total: £2.01.

- Authoritative invoice total: 201 pence.

This example illustrates the rounding rule; it does not define a general childcare rate or quantity.

### Worked example: multiple children and a service

This synthetic example demonstrates an invoice containing childcare charges for two children at different rates and a service charge. The childminder enters the applicable quantities and rates based on the family's agreed arrangements.

| Description | Quantity | Unit rate | Exact amount |
|---|---:|---:|---:|
| Child A — contracted childcare | 10 hours | £5.00/hour | £50.00 |
| Child B — additional childcare | 2 hours | £8.00/hour | £16.00 |
| Meals | 3 meals | £2.25/meal | £6.75 |
| Total | | | £72.75 |

Expected result

Exact subtotal: £72.75
Authoritative invoice total: 7,275 pence (£72.75)
Displayed line amounts: 5,000 + 1,600 + 675 = 7,275 pence
Rounding adjustment: 0 pence
## 5. Displayed line amounts and rounding adjustment

Customer-facing invoice line amounts are displayed to two decimal places.

Because each displayed line may be rounded independently for presentation, their displayed sum can differ from the authoritative aggregate-first total. NurturePatch must reconcile this difference transparently.

Calculate the adjustment in integer pence:

`rounding adjustment = authoritative invoice total − sum of displayed line amounts`

For example:

| Invoice line | Amount |

|---|---:|

| Service line 1 | £1.01 |

| Service line 2 | £1.01 |

| Rounding adjustment | −£0.01 |

| **Invoice total** | **£2.01** |

Implementation requirements:

- Display a clearly labelled rounding-adjustment line only when the difference is non-zero.

- Ensure the displayed line amounts plus the adjustment equal the authoritative invoice total exactly.

- Do not alter the underlying exact line calculations to manufacture the reconciliation.

- Do not use the adjustment to conceal pricing errors, unauthorised discounts or incorrect calculations.

- Preserve the adjustment and the displayed invoice values in the issued invoice snapshot.

- Test both positive and negative differences where valid.

The adjustment is a presentation and reconciliation mechanism. It does not replace the aggregate-first rounding policy or change the underlying contractual charges.

## 6. Calculation and auditability

The calculation service must be independent of the web API, database and cloud infrastructure.

For each calculation, retain sufficient information to explain and reproduce the result, including:

- The relevant quantity, unit and rate inputs.

- The applicable service or charge description.

- The calculation result before final invoice rounding.

- Permitted adjustment details and recorded reasons.

- The aggregate exact amount, rounding method and authoritative rounded total.

- The displayed line amounts and any rounding adjustment.

The implementation must define a safe, consistent representation for intermediate values that may contain fractions of a penny, while retaining integer-pence values for authoritative payable amounts.

Issued invoices must preserve their original calculation and display snapshots. Subsequent payments affect the balance due, not the original issued invoice total. Corrections must follow the authorised correction process.

## 7. Invoice totals and payments

- Derive invoice totals from validated calculation inputs and exact line amounts.

- Round the aggregate once using the policy in Section 4.

- Reconcile displayed amounts according to Section 5.

- Calculate outstanding balances using the authoritative invoice total and valid payment allocations.

- Reject allocations that exceed the applicable amount available for allocation.

- Record only confirmed payments as received.

- Keep childcare-funding approval, expected funding and received funding distinct.

- Do not treat a funding approval as evidence that funds have been received.

Payment allocations, receipts and funding reconciliation must not silently rewrite an issued invoice.

## 8. Validation and error handling

Reject invalid or unsupported inputs, including:

- Negative or otherwise disallowed quantities.

- Non-finite numeric values, including `NaN` and infinity.

- Unsupported service units or quantities that violate service rules.

- Rates outside documented limits.

- Invalid adjustment types or unauthorised deductions.

- Values that exceed defined precision or range limits.

Validation must distinguish between genuinely invalid inputs and values permitted by the applicable contract. Error messages must be actionable without exposing sensitive information.

## 9. Test requirements

Automated tests must cover:

- Ordinary hourly and additional-service calculations.

- Multiple children and different contractual rates.

- Whole-number quantities for trips, days and meals.

- Fixed-fee services with quantity one.

- Permitted adjustments and missed-hour deductions with required evidence.

- Invalid, non-finite, unsupported and out-of-range inputs.

- Decimal calculations without binary floating-point currency errors.

- `ROUND_HALF_UP` at relevant boundaries.

- Aggregate-first rounding where line-by-line rounding would produce a different result.

- Conversion of the final rounded total to integer pence.

- Positive and negative rounding adjustments where valid.

- No adjustment when displayed lines already reconcile.

- Displayed lines plus adjustment equalling the authoritative total.

- Partial payments, split allocations and over-allocation rejection.

- Issued invoice immutability and correction handling.

- Funding approval, expected funding, partial receipt and received-funding reconciliation.

Include documented sample calculations with expected results. Tests must use synthetic data and must not contain real family or financial information.

## 10. Scope and dependencies

This decision supports the billing calculation engine and related invoice functionality. It does not itself implement the API, database, PDF generation, payment processing or cloud deployment.

The calculation service must remain independently testable and must not require HTTP, database or cloud dependencies.

## 11. Remaining implementation and verification work

The childminder-confirmed business rules in this document are settled. The following work remains for implementation and production readiness:

- Define precise numeric limits and input validation rules.

- Select and document the representation used to retain exact intermediate calculation values.

- Implement contract-specific hourly and adjustment validation.

- Confirm applicable accounting, funded-hours and local-authority requirements before production use.

- Verify the invoice presentation with the childminder before finalising the customer-facing layout.

These tasks must be completed or appropriately validated before the relevant functionality is released. They must not silently change the confirmed business rules.

## 12. Decision summary

NurturePatch will use integer pence for authoritative payable amounts and `Decimal` for exact intermediate calculations. It will calculate invoice totals by summing exact line amounts and applying `ROUND_HALF_UP` once to the aggregate. Customer-facing line amounts will be displayed to two decimal places, with a clearly labelled rounding-adjustment line when needed to reconcile them to the authoritative invoice total.

Childcare-hour billing will follow each family's contract. Trips, days and meals will use whole-number quantities, and fixed-fee services will use a quantity of one. Calculation inputs and issued invoice snapshots must remain traceable and auditable.