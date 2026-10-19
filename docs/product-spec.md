# NurturePatch — Product Specification

**Status:** Draft for stakeholder review
**Version:** 0.1
**Jurisdiction:** England
**Requirements owner:** Nurture Patch Childminder

## 1. Purpose

The application will replace manual Word-based invoicing and receipt process with a consistent, auditable system for calculating childcare charges, issuing invoices, recording payments and reconciling childcare funding.

The product must prioritise financial correctness, understandable invoices, privacy and the ability to explain how every amount was calculated.

## 2. Problem statement

The current manual process requires the childminder to prepare invoices and receipts and reconcile different charging arrangements by hand. Families can have different contractual rates, multiple children, additional services, adjustments, partial payments and childcare funding.

The application should reduce repetitive administration and calculation errors while retaining sufficient detail to explain each charge, payment, adjustment and funding transaction.

## 3. Users and tenancy

### 3.1 Primary user

**Nurture Patch Childminder:** manages families, children, contracts, billing, payments, funding and documents.

### 3.2 Future users

The design should accommodate multiple childminding businesses in the future. A parent-facing portal and additional business roles are not required for the initial MVP.

### 3.3 Tenant isolation

**REQ-SEC-01 — Business data isolation**

- Every business-owned record must belong to a business.
- A user must access only businesses and records for which they have appropriate authorisation.
- Relationships between records must not allow data from different businesses to be combined accidentally.
- Automated tests must verify cross-business access is rejected.

## 4. MVP scope

The MVP is intended to provide:

1. Family and child records.
2. Contracts and effective-dated rates.
3. Monthly invoice previews.
4. Itemised charges, additional services and permitted adjustments.
5. Invoice issue and private PDF generation.
6. Confirmed payments and full or partial payment allocations.
7. Childcare funding status tracking and reconciliation.
8. Receipts for confirmed payments.
9. Outstanding-balance and reconciliation visibility.
10. Auditable financial actions.
11. Automated testing and continuous integration.
12. A repeatable path to containerised deployment and, subsequently, AWS infrastructure.

The implementation sequence will be managed through GitHub Issues. Not every capability needs to be delivered in the first release.

## 5. Families, children and contracts

**REQ-DATA-01 — Family and child relationships**

- A family may have multiple children.
- An invoice may include multiple children belonging to the same family.
- Child, family, contract and invoice relationships must be validated.
- Invalid or cross-business relationships must be rejected.

**REQ-BILL-01 — Contracted hours and family-specific rates**

- Recurring charges are based on the applicable contract and billing period.
- Rates may differ by family, child, contract and service, where the agreement requires it.
- Contracted hours and rates must be represented clearly.
- Historical calculations must use the rates applicable to the relevant period.

**REQ-BILL-02 — Effective-dated rates**

- Rate changes must have effective dates.
- The applicable rate must be determinable for a given billing period.
- Later rate changes must not silently change previously issued invoices.
- Ambiguous overlapping rate periods must be prevented or handled by explicitly documented rules.

## 6. Billing and adjustments

**REQ-BILL-03 — Itemised invoice charges**

Each invoice line must retain sufficient information to explain its charge, including:

- Description.
- Relevant child, where applicable.
- Quantity and unit.
- Unit rate.
- Calculated amount.

The invoice must clearly identify the billing period and the family being charged.

**REQ-BILL-04 — Additional services**

- Additional services may include pickup, drop-off, meals or other agreed services.
- Supported units may include trips, days, meals and fixed fees.
- Service rates may differ between families or agreements.
- Additional services must be separately identifiable on the invoice.

**REQ-BILL-05 — Permitted adjustments**

- Extra hours, missed hours and other adjustments must be recorded explicitly.
- A missed-hour deduction must not be applied automatically.
- A missed-hour deduction is permitted only when the applicable agreement allows it.
- Each adjustment must have a reason and sufficient supporting context.
- Original charges must remain traceable when adjustments are applied.

**REQ-BILL-06 — Monetary representation and rounding**

- Monetary amounts must use integer pence in application and persistence logic.
- Binary floating-point arithmetic must not be used for currency calculations.
- Quantity precision, rounding method and rounding points must be documented.
- Calculations must be deterministic and covered by automated tests.
- Invoice totals must be derived from validated line amounts using a documented policy.

## 7. Invoice lifecycle

**REQ-INV-01 — Invoice preview**

- A user must be able to review a billing result before issuing an invoice.
- The preview must identify the billing period and applicable charges.
- Preview generation must not issue an invoice or create unintended financial side effects.
- Repeating a preview with unchanged inputs must produce the same result.

**REQ-INV-02 — Immutable issued invoices**

- Issuing an invoice must capture a snapshot of its lines, descriptions, quantities, rates and totals.
- Subsequent contract, rate or service configuration changes must not alter that snapshot.
- Issued invoices must not be silently edited.
- Invoice numbering must remain safe under concurrent issue requests.
- Duplicate requests must be handled safely.

**REQ-INV-03 — Controlled corrections**

- An issued invoice must be corrected through a controlled credit-note or correction process.
- The original invoice and its corrections must remain linked and auditable.
- A correction must not erase the historical record.
- The implementation must document how corrections affect outstanding balances and subsequent billing.

**REQ-INV-04 — Document consistency**

- A PDF representing an issued invoice must match its saved invoice snapshot.
- Documents must not change retrospectively when current family or contract data changes.
- Invoice documents must be accessible only to authorised users.

## 8. Payments and receipts

**REQ-PAY-01 — Confirmed payments**

- Payments must record the amount, date, method and relevant reference.
- The system must distinguish unconfirmed payment information from confirmed payments.
- A receipt must not be issued for an unconfirmed payment.
- Important payment actions must be auditable.

**REQ-PAY-02 — Payment allocations**

- Full and partial payments must be supported.
- A payment may be allocated across invoices if the implemented business rules permit it.
- An invoice may receive multiple partial payments.
- Allocations must not exceed the available unallocated payment amount or the invoice's remaining allocatable balance.
- Outstanding balances must be derived consistently from invoice amounts, valid corrections and confirmed allocations.

**REQ-PAY-03 — Financial operation integrity**

- Duplicate financial requests must not create duplicate effects.
- Concurrent operations must preserve allocation limits.
- Related financial changes must be committed atomically.
- Failed operations must not leave partial financial updates.

**REQ-PAY-04 — Receipts**

- Receipts may be issued only for confirmed payments.
- A receipt must identify the payment and relevant allocation details.
- Receipts and subsequent corrections or reversals must remain auditable.

## 9. Childcare funding

**REQ-FUND-01 — Funding status**

Funding records must distinguish, as applicable:

- Expected.
- Claimed.
- Approved.
- Received.

Approval must not be treated as receipt of funds.

**REQ-FUND-02 — Funding reconciliation**

- Funding amounts must be traceable to relevant billing periods and records.
- Partial funding receipts must be supported.
- Funding and parent payments must remain distinguishable.
- Outstanding, unmatched or unexplained amounts must be identifiable.
- Reconciliation must not silently treat an expected or approved amount as cash received.

**REQ-FUND-03 — Funded hours and optional extras**

- Eligible funded hours must not be charged to parents as ordinary childcare charges.
- Optional extras must be separately identified and itemised.
- Applicable requirements for voluntary extras, opt-out arrangements and local authority rules must be verified before production use.
- Funding-related calculations must be tested against documented, approved scenarios.

The exact rules must be confirmed against current official guidance and the relevant local authority's requirements before the application is used for real billing.

## 10. Security, privacy and audit

**REQ-SEC-02 — Authentication and authorisation**

- Protected operations must require appropriate authentication.
- Access must be checked on the server, not trusted solely to the user interface.
- Authorisation must be enforced for every relevant business-owned resource.

**REQ-SEC-03 — Private documents and secrets**

- Invoice PDFs and receipts must be stored privately.
- Document retrieval must require authorisation.
- Credentials and secrets must not be committed to source control or embedded in container images.
- Sensitive configuration must be supplied through appropriate runtime configuration and secret-management mechanisms.

**REQ-SEC-04 — Auditability**

- Important financial and administrative actions must record the actor, timestamp, action and relevant record reference.
- Audit records must be protected from unauthorised modification.
- Logs must not expose secrets or unnecessary personal information.

**REQ-SEC-05 — Development data and operational readiness**

- Development and automated tests must use synthetic data.
- Retention, deletion, backup and recovery requirements must be defined before production use.
- Production readiness requires appropriate security, privacy, access-control and operational checks.

## 11. Engineering and operational constraints

**REQ-ENG-01 — Testable and maintainable implementation**

- Billing rules must be separated sufficiently from transport, persistence and presentation code to support independent testing.
- Important business rules must have automated tests.
- API contracts and configuration must be documented.
- Changes must be reviewed through pull requests.

**REQ-ENG-02 — Repeatable delivery**

- Continuous integration must run relevant automated checks.
- The application must be containerisable.
- Infrastructure changes should be managed through version-controlled Terraform.
- Deployment and runtime behaviour must be observable through appropriate logs, health checks and monitoring.
- AWS resources and operational costs must be managed deliberately.

These are intended engineering outcomes. Specific libraries, AWS services and implementation details will be documented in the engineering standards or relevant technical decision records.

## 12. Out of scope for the initial MVP

- Parent self-service portal.
- Online payment processing.
- Automatic bank-feed integration.
- Direct local authority system integration.
- Automated production provisioning before security and operational controls are established.

## 13. Open questions requiring stakeholder confirmation

1. Which invoice and receipt fields, branding and layout does the childminder approve?
2. How do contracts define rate changes, extra hours, missed hours and notice periods?
3. Which payment methods are used, and how are payments currently allocated?
4. How are funding claims, approvals, payments and discrepancies currently recorded?
5. Which local authority rules apply to funded hours and optional extras?
6. What invoice numbering, tax treatment and record-retention requirements apply?
7. Which user roles and permissions will be needed?
8. How should invoice corrections, refunds, reversals and credit notes affect balances?
9. Which document delivery methods are needed, and what should happen if delivery fails?

Unconfirmed items must not be treated as agreed business rules.

## 14. Success criteria

The MVP will be considered successful when:

- Billing calculations are deterministic and covered by automated tests.
- Family-specific rates, sibling invoices and additional services are supported.
- Permitted adjustments are explicit and traceable.
- Issued invoices remain unchanged by later data changes.
- Partial payments, receipts and funding can be reconciled and audited.
- Cross-business access is prevented by automated tests.
- Pull requests run the required CI checks.
- Deployment is repeatable and runtime behaviour is observable.
- The childminder has reviewed and approved the workflow and invoice layout before real data is introduced.