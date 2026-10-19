# NurturePatch — Delivery Backlog

**Status:** Initial draft
**Product requirements:** `docs/product-spec.md`
**Purpose:** Decompose product requirements into deliverable, testable work.

## 1. How to use this backlog

The product specification defines what the application must achieve. This backlog decomposes those requirements into epics and user stories.

- **Epic:** a broad capability grouping related work.
- **User story:** a user-focused outcome with acceptance criteria.
- **GitHub Issue:** the trackable work item used to plan, implement and review changes.
- **Pull request:** the proposed code or documentation change used for review and CI.

An epic or user story does not automatically require a separate GitHub Issue. The existing 13 issues are the initial work packages. Split stories into additional issues when doing so improves implementation, review or delivery tracking.

Requirement IDs refer to `docs/product-spec.md`. When requirements change, update both documents and review the affected acceptance criteria.

## 2. EPIC-001 — Billing Calculation Engine

**Goal:** Calculate itemised childcare charges accurately and consistently.

**Requirements:** REQ-BILL-01 to REQ-BILL-06.

### US-001 — Calculate invoice line amounts

As a childminder, I want line amounts calculated from quantities and rates so that charges are consistent and accurate.

**Acceptance criteria**
- The calculation uses a documented quantity precision and rounding policy.
- Monetary amounts use integer pence.
- Invalid quantities and rates are rejected.
- Automated tests cover normal, boundary and invalid inputs.

**Requirement coverage:** REQ-BILL-06.

### US-002 — Calculate additional service charges

As a childminder, I want additional services priced using their configured units and rates so that extras are itemised accurately.

**Acceptance criteria**
- Supported units include trips, days, meals and fixed fees.
- Each line includes a description, quantity, unit, unit rate and calculated amount.
- Different families or agreements can use different rates.
- Automated tests cover supported units and invalid inputs.

**Requirement coverage:** REQ-BILL-03, REQ-BILL-04.

### US-003 — Apply permitted adjustments

As a childminder, I want adjustments to be recorded explicitly so that changes to charges are explainable.

**Acceptance criteria**
- Each adjustment records its type, amount and reason.
- Missed-hour deductions are applied only when the applicable agreement permits them.
- Invalid or unauthorised adjustments are rejected.
- Original charges remain traceable.

**Requirement coverage:** REQ-BILL-05.

### US-004 — Calculate invoice totals

As a childminder, I want totals derived from validated invoice lines so that invoice amounts are consistent.

**Acceptance criteria**
- Invoice totals are derived from validated lines.
- The documented rounding policy is applied consistently.
- Empty or invalid invoices are handled explicitly.
- Tests cover multiple lines, siblings, mixed services and adjustments.

**Requirement coverage:** REQ-BILL-06, REQ-INV-01.

## 3. EPIC-002 — Family and Contract Management

**Goal:** Maintain reliable family, child, contract and rate relationships.

**Requirements:** REQ-DATA-01, REQ-BILL-01, REQ-BILL-02, REQ-SEC-01.

### US-005 — Manage families and children

**Acceptance criteria**
- A family can have multiple children.
- Each record belongs to the correct business.
- Invalid family-child relationships are rejected.
- Tests cover valid relationships and cross-business attempts.

**Requirement coverage:** REQ-DATA-01, REQ-SEC-01.

### US-006 — Manage effective-dated contracts and rates

**Acceptance criteria**
- Contracts and rates have effective dates.
- Rates can differ between families, children and services as required.
- The applicable rate can be determined for a billing period.
- Overlapping or ambiguous rate periods are prevented or handled by documented rules.
- Historical invoices are unaffected by later rate changes.

**Requirement coverage:** REQ-BILL-01, REQ-BILL-02.

### US-007 — Validate invoice relationships

**Acceptance criteria**
- Every invoice belongs to a business and family.
- Every referenced child is associated with the invoice's family.
- Cross-business relationships are rejected.
- Validation is enforced by the application and appropriate database constraints.

**Requirement coverage:** REQ-DATA-01, REQ-SEC-01.

## 4. EPIC-003 — Invoice Lifecycle

**Goal:** Preview, issue, preserve and correct invoices safely.

**Requirements:** REQ-INV-01 to REQ-INV-04.

### US-008 — Preview monthly billing

**Acceptance criteria**
- A preview identifies the billing period and applicable rates.
- Contracted charges, additional services and permitted adjustments are included.
- Generating a preview does not issue an invoice or cause unintended financial side effects.
- Unchanged inputs produce the same calculated result.

**Requirement coverage:** REQ-INV-01, REQ-BILL-01 to REQ-BILL-06.

### US-009 — Issue immutable invoices

**Acceptance criteria**
- An invoice can be issued only after required validation.
- Issuing captures a snapshot of lines, quantities, rates and totals.
- Later changes to source records do not alter the issued invoice.
- Invoice numbering is safe under concurrent requests.
- Duplicate issue requests are handled safely and idempotently.

**Requirement coverage:** REQ-INV-02.

### US-010 — Generate invoice PDFs

**Acceptance criteria**
- A PDF can be generated from an issued invoice snapshot.
- The document matches the saved invoice details.
- Documents are stored privately.
- Unauthorised document access is rejected.

**Requirement coverage:** REQ-INV-04, REQ-SEC-03.

### US-011 — Correct issued invoices

**Acceptance criteria**
- Issued invoices cannot be silently edited.
- Corrections use a controlled credit-note or correction process.
- The original and its corrections remain linked and auditable.
- Tests cover full and partial corrections and their effect on balances.

**Requirement coverage:** REQ-INV-03.

## 5. EPIC-004 — Payments and Receipts

**Goal:** Record payments, allocate funds and produce accurate receipts.

**Requirements:** REQ-PAY-01 to REQ-PAY-04.

### US-012 — Record confirmed payments

**Acceptance criteria**
- A payment records its amount, date, method and relevant reference.
- Confirmed and unconfirmed payment information are distinguishable.
- Duplicate submissions cannot create duplicate financial effects.
- Important payment actions are auditable.

**Requirement coverage:** REQ-PAY-01, REQ-PAY-03.

### US-013 — Allocate full and partial payments

**Acceptance criteria**
- Partial payments are supported.
- A payment can be allocated across invoices where the business rules permit it.
- An invoice can receive multiple allocations.
- Outstanding balances are derived consistently from invoices, valid corrections and confirmed allocations.

**Requirement coverage:** REQ-PAY-02.

### US-014 — Prevent duplicate processing and over-allocation

**Acceptance criteria**
- Financial operations have suitable idempotency safeguards.
- Allocations cannot exceed the available payment amount or permitted invoice balance.
- Concurrent operations preserve these limits.
- Related financial updates are atomic.
- Tests cover duplicate requests, over-allocation and concurrent operations.

**Requirement coverage:** REQ-PAY-02, REQ-PAY-03.

### US-015 — Issue receipts

**Acceptance criteria**
- Receipts can be issued only for confirmed payments.
- Receipts identify the relevant payment and allocation details.
- Receipts are auditable.
- Reversals or corrections preserve the history.

**Requirement coverage:** REQ-PAY-04.

## 6. EPIC-005 — Childcare Funding Reconciliation

**Goal:** Distinguish funding status from cash received and reconcile amounts accurately.

**Requirements:** REQ-FUND-01 to REQ-FUND-03.

### US-016 — Track funding status

**Acceptance criteria**
- Funding records distinguish expected, claimed, approved and received amounts as applicable.
- Status changes preserve relevant history.
- Approval is never treated as proof of receipt.
- Tests cover valid status transitions and partial amounts.

**Requirement coverage:** REQ-FUND-01.

### US-017 — Reconcile funding and parent payments

**Acceptance criteria**
- Funding records are associated with the relevant business and billing period.
- Partial funding receipts are supported.
- Funding and parent payments remain distinguishable.
- Outstanding or unmatched amounts can be identified.
- Reconciliation does not silently treat approved funds as received cash.

**Requirement coverage:** REQ-FUND-02.

### US-018 — Enforce funded-hours and optional-extra rules

**Acceptance criteria**
- Eligible funded hours are not charged to parents as ordinary childcare charges.
- Optional extras are separately identified and itemised.
- Applicable official and local authority rules are documented and verified before production use.
- Tests cover documented compliant and non-compliant billing scenarios.

**Requirement coverage:** REQ-FUND-03.

## 7. EPIC-006 — API Security and Audit

**Goal:** Protect business, family, child and financial information.

**Requirements:** REQ-SEC-01 to REQ-SEC-05.

### US-019 — Authenticate and authorise users

**Acceptance criteria**
- Protected API operations require authentication.
- Access is authorised against business membership and permissions.
- Cross-business access attempts are rejected.
- Tests cover unauthenticated, unauthorised and authorised requests.

**Requirement coverage:** REQ-SEC-01, REQ-SEC-02.

### US-020 — Audit financial and administrative actions

**Acceptance criteria**
- Required actions record actor, timestamp, action and relevant record reference.
- Audit records are protected against unauthorised modification.
- Logs do not expose secrets or unnecessary personal information.
- Tests verify the required audit events.

**Requirement coverage:** REQ-SEC-04.

## 8. EPIC-007 — Engineering and DevOps

**Goal:** Make development, testing and deployment repeatable and reviewable.

**Requirements:** REQ-ENG-01, REQ-ENG-02, REQ-SEC-03, REQ-SEC-05.

### US-021 — Establish engineering standards and repository structure

**Acceptance criteria**
- Repository structure and local setup instructions are documented.
- Formatting, linting and testing commands are documented.
- Configuration is separated from secrets.
- Branch, commit and pull-request practices are documented.
- Relevant engineering decisions are recorded when justified.

**Requirement coverage:** REQ-ENG-01, REQ-SEC-03, REQ-SEC-05.

### US-022 — Implement automated CI

**Acceptance criteria**
- Pull requests run the required automated checks.
- Failed checks are visible and cannot be mistaken for passing checks.
- Test and dependency requirements are documented.
- Checks can be reproduced locally where practical.

**Requirement coverage:** REQ-ENG-01, REQ-ENG-02.

### US-023 — Containerise the application

**Acceptance criteria**
- The application can be built into a container image.
- Runtime configuration is supplied externally.
- Secrets are not embedded in the image.
- Startup, health checks and local execution are documented.

**Requirement coverage:** REQ-ENG-02, REQ-SEC-03.

### US-024 — Provision and deploy infrastructure

**Acceptance criteria**
- Infrastructure is defined and version-controlled using Terraform.
- AWS access follows least-privilege principles.
- Sensitive configuration is managed securely.
- Logging, monitoring, backup and recovery expectations are documented and implemented as appropriate to the deployment stage.
- AWS costs and resource cleanup are considered.

**Requirement coverage:** REQ-ENG-02, REQ-SEC-05.

## 9. Traceability to existing GitHub Issues

The following table maps the backlog to the 13 issues already created. It uses issue titles rather than assumed issue numbers; fill in the actual GitHub numbers once you check your repository.

| Existing GitHub Issue title | Related backlog items |
|---|---|
| Establish product requirements and backlog | This document; all epics and stories |
| Define engineering standards and test strategy | US-021, US-022 |
| Establish initial repository structure | US-021 |
| Implement/test billing calculation engine | US-001 to US-004 |
| Automated testing and CI | US-001 to US-024 as relevant; US-022 |
| Family, child, contract data model | US-005 to US-007 |
| Invoice preview/issue/correction | US-008, US-009, US-011 |
| Payments, allocations, receipts | US-012 to US-015 |
| Childcare funding reconciliation | US-016 to US-018 |
| Invoice PDFs and receipts | US-010, US-015 |
| API authentication/authorisation/audit | US-019, US-020 |
| Containerise application | US-023 |
| AWS/Terraform deployment | US-024 |

### Mapping rules

- A GitHub Issue may cover several related user stories.
- A user story may be split into multiple GitHub Issues if it is too large.
- Add new issues only when they represent useful, independently trackable work.
- The issue's acceptance criteria must remain consistent with the referenced user stories and product requirements.
- When a change affects a requirement, update the specification, backlog and relevant issue as needed.
- Do not treat a proposed mapping as proof that an issue's acceptance criteria are already satisfied.

## 10. Definition of done

Unless a story explicitly requires a different approach, completed implementation work should satisfy these checks:

- Acceptance criteria are met.
- Relevant automated tests have been added or updated.
- Tests and other required CI checks pass.
- Security, privacy and tenant-isolation implications have been considered.
- Documentation is updated where needed.
- Changes are reviewed through a pull request.
- Known limitations and outstanding follow-up work are recorded.

A story is not complete merely because its code exists; its acceptance criteria and required verification must also be satisfied.