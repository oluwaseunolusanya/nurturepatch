# Decision 0001: Billing Money and Rounding

**Status:** Proposed — confirm through implementation tests before treating as final  
**Date:** 2026-10-20  
**Scope:** Monetary representation and arithmetic for NurturePatch billing

## 1. Context

NurturePatch calculates childcare charges from contracted rates, quantities, additional services, adjustments, payments, and funding records.

Floating-point arithmetic can introduce binary representation errors when handling decimal values. Financial calculations therefore need an explicit representation, precision model, conversion point, and rounding policy.

This decision establishes a proposed baseline for implementation and testing. Any material change to the policy must be documented and reviewed.

## 2. Monetary representation

**Decision:** Store monetary amounts as integer pence.

Examples:

| Amount | Stored value |
|---|---:|
| £0.01 | 1 |
| £12.34 | 1234 |
| £100.00 | 10000 |

Rules:

- Monetary amounts persisted in the database and exposed in internal financial records use integer pence.
- Do not use binary floating-point types for currency calculations.
- API and document formatting must distinguish the stored integer from its display representation. For example, `1234` pence is displayed as `£12.34`.
- Currency is GBP for the initial England-focused product. Multi-currency support is outside the initial scope.
- Validate permitted ranges and signs at the relevant business boundary. Negative values must only be permitted for explicitly defined operations, such as an authorised credit or reversal.

## 3. Quantities, rates, and intermediate calculations

**Proposed approach:** Use Python `Decimal` for decimal inputs, rates where necessary, and intermediate arithmetic. Convert final monetary results to integer pence using the rounding policy in this document.

Rationale:

- Decimal arithmetic avoids the binary representation issues associated with `float`.
- Integer pence provides a consistent representation for stored financial amounts.
- Keeping intermediate arithmetic precise allows quantities such as fractional hours to be handled without prematurely rounding every operation to a penny.

Rules:

- Do not convert a binary floating-point value into a monetary calculation and assume the original decimal value has been preserved.
- Parse decimal inputs from strings or other exact decimal representations where practical.
- Define the supported precision for each quantity type before implementing the corresponding feature.
- Validate quantities against their business rules; do not assume all services use the same unit or precision.
- Keep calculations deterministic: the same validated inputs and policy must produce the same result.

## 4. Quantity precision

Quantity precision must be defined by the relevant business rule, not chosen implicitly by a programming language or database default.

The initial design must support documenting:

- **Time-based charges:** the permitted precision for hours and minutes, including how partial hours are represented.
- **Session or day-based charges:** whether quantities must be whole units or can be fractional.
- **Fixed-fee services:** the applicable unit and whether a quantity other than one is allowed.
- **Adjustments and credits:** the permitted input precision and validation rules.

**Open decision:** Confirm the required quantity precision with the childminder before finalising billing behaviour. Do not assume that all hourly charges can be rounded to the nearest whole hour or that all fractional hours are billed in the same way.

## 5. Rounding policy

**Proposed policy:** Use decimal arithmetic for intermediate calculations and round each invoice line's calculated amount to the nearest whole penny using the `ROUND_HALF_UP` rule. Calculate the invoice total by summing the rounded integer-pence line amounts.

For this rule:

- A fractional penny with an absolute value below half a penny rounds towards zero.
- A fractional penny at or beyond half a penny rounds away from zero.
- The implementation must use the explicitly configured decimal rounding mode, not a language or library default.

Examples:

| Calculated line amount | Rounded amount |
|---|---:|
| £10.004 | £10.00 |
| £10.005 | £10.01 |
| £10.006 | £10.01 |

These examples illustrate the proposed rounding rule, not actual childcare rates.

Rationale:

- Rounding each line gives a clear, auditable amount for every invoice line.
- Summing stored line amounts ensures the displayed invoice total matches the sum of the amounts being billed.
- Explicit rounding prevents behaviour from depending on an implicit programming-language default.

The chosen line-level rounding rule must be confirmed against the childminder's requirements before production use. If a different policy is needed, update this decision and its tests before implementing billing.

## 6. Conversion to integer pence

For each invoice line:

1. Validate the input quantity and rate.
2. Parse decimal values without introducing binary floating-point currency arithmetic.
3. Calculate the line amount using decimal arithmetic at the defined precision.
4. Apply the explicit rounding rule once at the agreed line-total conversion point.
5. Convert the rounded GBP amount into integer pence.
6. Store the integer-pence line amount.
7. Calculate invoice totals by summing the stored line amounts.

The implementation must ensure the conversion to pence is exact after rounding. Do not silently truncate fractional pennies or repeatedly round intermediate values without an explicit rule.

The final implementation must define appropriate decimal precision and validation limits so calculations cannot silently overflow or lose required precision.

## 7. Invoice totals and balances

- The invoice total is the sum of its persisted integer-pence line amounts.
- Any permitted adjustments must have explicit rules and be represented in the invoice records.
- The outstanding balance is derived from the issued invoice amount and valid payment allocations under the defined correction and allocation rules.
- Funding expected, approved, or received must not be silently mixed with parent charges or confirmed payments.
- Any displayed totals must be derived from the authoritative stored monetary values, not independently recalculated using a different rounding method.

## 8. Issued invoices and corrections

- Issuing an invoice creates an immutable snapshot of the billed lines, quantities, rates, rounded line amounts, and invoice total.
- Later changes to a contract or rate must not change an already issued invoice.
- Issued invoices must not be silently edited to correct an error.
- Corrections must use an explicit, auditable correction process, such as a credit note and, where required, a replacement invoice.
- Corrections must preserve a traceable relationship to the original invoice and must not rewrite historical payment records without an explicit correction or reversal process.

## 9. Required tests

The billing implementation must include tests for:

- Integer-pence representation and display conversion.
- Exact decimal input handling without binary floating-point currency arithmetic.
- Values immediately below, exactly at, and immediately above a half-penny boundary.
- Positive and negative rounding where negative values are permitted.
- Quantity precision and invalid quantities.
- Zero values and documented minimum and maximum values.
- Summation of rounded line amounts into the invoice total.
- Multiple lines whose individual rounded amounts differ from rounding the aggregate unrounded amount.
- Partial payments and outstanding balances.
- Rejection of over-allocation.
- Immutability of issued invoice snapshots.
- Corrections that preserve the original financial history.
- Funding reconciliation that distinguishes approval from cash actually received.

Tests must assert the expected integer-pence results, not merely that the calculation completes.

## 10. Consequences and trade-offs

**Benefits**

- Avoids binary floating-point currency errors.
- Produces deterministic stored monetary amounts.
- Makes invoice totals and line amounts auditable.
- Defines a consistent basis for payment allocation and reconciliation.

**Trade-offs**

- Quantity precision and rounding rules require explicit business decisions.
- Line-level rounding can produce a different total from rounding the aggregate unrounded value.
- Changing the policy after invoices have been issued could cause discrepancies, so the policy must be version controlled and applied consistently.

## 11. Outstanding decisions

Before production billing is approved, confirm:

- The required precision and billing increments for time-based charges.
- The supported quantity precision for other service types.
- Whether the proposed line-level `ROUND_HALF_UP` rule matches the childminder's invoicing expectations.
- The treatment of any exceptional adjustments or credits.
- Any additional accounting or local requirements that affect invoice presentation or funding reconciliation.

These questions must be resolved with the relevant stakeholders and verified requirements; this document does not claim that the proposed policy has already been approved.