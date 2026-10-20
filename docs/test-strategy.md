# Test Strategy

**Status:** Initial baseline  
**Applies to:** NurturePatch  
**Scope:** Automated and manual verification of application behaviour

## 1. Purpose

This document defines how NurturePatch will be tested to provide confidence in functional correctness, financial accuracy, data integrity, security, and maintainability.

Tests should verify observable behaviour and important business rules. Financial calculations and record integrity require particular care because defects can cause incorrect invoices, payment balances, or funding records.

This document defines the intended test approach. A test level or check must not be described as implemented until it exists and has been verified.

## 2. Test principles

- Test business requirements and acceptance criteria, not only implementation details.
- Prefer deterministic tests that produce the same result for the same inputs.
- Use synthetic test data only.
- Cover normal cases, boundary conditions, invalid inputs, and important failure paths.
- Test financial invariants explicitly.
- Keep unit tests fast so they can run frequently.
- Use integration tests to verify interactions with databases and other components.
- Use end-to-end tests for critical user journeys where their additional cost is justified.
- Do not rely on manual testing alone for repeatable financial rules.
- Keep tests maintainable and update them when requirements intentionally change.

## 3. Test levels

### 3.1 Unit tests

**Purpose:** Verify a small unit of logic in isolation.

Use unit tests for pure business rules and calculations that do not require a database, network, or running application.

Examples include:

- Calculating invoice line amounts from quantities and rates.
- Calculating invoice totals and outstanding balances.
- Applying the agreed quantity precision and rounding policy.
- Validating permitted adjustments and additional service charges.
- Rejecting invalid quantities, rates, or monetary inputs.
- Distinguishing expected funding from funding actually received.

Unit tests should be fast, deterministic, and easy to diagnose when they fail.

### 3.2 Integration tests

**Purpose:** Verify that components work correctly together.

Use integration tests where correctness depends on interactions between components, particularly application services and PostgreSQL.

Examples include:

- Persisting and retrieving invoices and invoice lines.
- Enforcing database constraints and relationships.
- Creating an invoice within a transaction.
- Allocating payments without exceeding payment or invoice balances.
- Ensuring related financial records are committed or rolled back together.
- Enforcing tenant ownership and access boundaries at the persistence and service layers.
- Applying database migrations to a test database.

Integration tests should use an isolated test database or equivalent disposable environment. They must not use production data.

### 3.3 API tests

**Purpose:** Verify externally observable API behaviour.

Test successful requests as well as validation failures, unauthorised access, forbidden access, and missing resources.

Examples include:

- Creating and retrieving permitted records.
- Rejecting malformed or invalid requests.
- Enforcing authentication and authorisation.
- Returning consistent error responses.
- Preventing one business from accessing another business's records.
- Handling duplicate requests safely where idempotency is required.

API tests may use the application with test dependencies and a dedicated test database.

### 3.4 End-to-end tests

**Purpose:** Verify important user journeys across multiple application components.

Prioritise a small number of high-value journeys, such as:

1. Configure a family, children, and contracted rates.
2. Generate and review a monthly invoice.
3. Issue the invoice and generate its document.
4. Record a payment, allocate it, and generate a receipt.
5. Reconcile expected childcare funding against funding received.
6. Correct an issued invoice using the approved correction process.

End-to-end tests provide useful confidence in complete workflows but are generally slower and more expensive to maintain than unit tests. They should complement, not replace, lower-level tests.

### 3.5 Manual and exploratory testing

Manual testing is appropriate for usability, visual layout, accessibility, and workflows that are difficult to evaluate fully through automation.

Before approving the invoice layout, obtain feedback from the intended childminder. Verify that invoice lines, totals, payment information, and relevant funding information are understandable.

Manual testing does not replace automated regression tests for calculations and financial invariants.

## 4. Financial correctness and invariants

Financial tests must cover more than example outputs. They must verify rules that must remain true across valid operations.

### 4.1 Monetary calculations

Test:

- Integer-pence storage for monetary amounts.
- The agreed strategy for precise intermediate calculations.
- Quantity precision, conversion to monetary amounts, and rounding boundaries.
- Zero values and the smallest supported valid values.
- Large valid values and documented limits.
- Invalid, negative, or out-of-range values where prohibited.
- Consistent totals between invoice lines, invoice totals, payments, and balances.

Expected results should be calculated independently where practical, rather than repeating the implementation's calculation in the test.

### 4.2 Invoice lifecycle

Test:

- Draft invoices can be edited within the defined rules.
- Issuing an invoice records the intended snapshot of its lines, quantities, rates, and totals.
- Issued invoices cannot be silently modified.
- Corrections follow the approved correction process.
- Concurrent attempts to issue or number invoices cannot create duplicate or inconsistent records.

### 4.3 Payments and allocations

Test:

- Full and partial payments.
- One payment allocated across multiple invoices, if supported.
- Multiple payments allocated to one invoice.
- Rejection of allocations greater than the remaining unallocated payment amount.
- Rejection of allocations greater than the invoice's outstanding balance.
- Prevention of duplicate processing where idempotency is required.
- Correct outstanding balances after allocations and any permitted reversals or corrections.
- Receipts are generated only for confirmed payments.

### 4.4 Funding reconciliation

Test funding states separately, including:

- Expected funding.
- Funding approved or confirmed by the relevant authority.
- Funding actually received.
- Partial funding receipts.
- Differences between expected, approved, and received amounts.
- Reconciliation updates without incorrectly treating approval as cash received.
- Correct handling of funded hours and separately itemised optional extras in accordance with verified applicable requirements.

Legal and local-authority rules must be verified before being encoded as confirmed product behaviour.

### 4.5 Data integrity and tenant isolation

Test:

- An invoice cannot contain children or family records belonging to an incompatible family or business.
- Relationships remain consistent when records are created or updated.
- One business cannot read or modify another business's records.
- Database constraints reject invalid relationships even if application-level validation is bypassed.
- Failed multi-step financial operations do not leave partial or inconsistent records.

## 5. Test data and environments

- Use synthetic families, children, rates, invoices, payments, and funding records.
- Include realistic edge cases without copying actual personal or financial information.
- Keep test data isolated from development and production data.
- Use controlled clocks or fixed dates where time-dependent behaviour is tested.
- Make test setup repeatable and clean up test data safely.
- Never send real invoices or payment receipts from automated tests.

## 6. Automated checks and CI

As repository tooling is introduced, automated checks should run locally and in GitHub Actions.

The intended checks include:

- Unit tests.
- Integration and API tests where configured.
- Formatting and linting.
- Type checking where configured.
- Database migration validation where appropriate.
- Relevant security and dependency checks as the application matures.

A check is considered active only after its configuration and execution have been verified. Pull requests must not claim that an unconfigured check passed.

The CI pipeline should fail when a required check fails and should make the failure visible to the developer.

## 7. Regression testing

When a defect is fixed, add a test that reproduces the defect when practical. The test should fail against the faulty behaviour and pass against the corrected behaviour.

Changes to financial rules must include regression tests for the affected calculations, boundaries, and invariants.

Changes to schemas or relationships should include appropriate migration, persistence, and integrity tests.

## 8. Definition of done

A change is ready for review when:

- Its acceptance criteria have been addressed.
- Relevant tests have been added or updated.
- Tests and configured automated checks pass.
- Financial invariants and security implications have been considered where relevant.
- Documentation has been updated where behaviour, decisions, or operating procedures change.
- Tests use synthetic data and introduce no secrets or real family or financial information.
- Any outstanding limitations or checks that are not yet automated are stated clearly.

The definition of done applies proportionately to documentation-only work: relevant documentation should be reviewed for accuracy and consistency, and unrelated application tests are not required merely because a documentation file changed.

## 9. Review and evolution

This strategy is an initial baseline. As the application develops, update it to reflect actual architecture, tooling, risks, and lessons learned. Changes should be reviewed and version controlled.