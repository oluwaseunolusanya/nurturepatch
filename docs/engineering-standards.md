# Engineering Standards

**Status:** Initial baseline  
**Applies to:** NurturePatch  
**Scope:** Application code, tests, documentation and delivery workflow

## 1. Purpose

These standards establish consistent development and review practices for NurturePatch. They aim to make the application maintainable, testable, secure and suitable for reliable financial record keeping.

Standards will evolve as the application develops. Any material change to an agreed standard should be documented and reviewed.

## 2. General engineering principles

- Prefer simple, readable solutions over unnecessary abstraction.
- Separate business rules from API handling, persistence and presentation.
- Make financial and business rules explicit rather than relying on implicit behaviour.
- Validate input at system boundaries and fail safely when input is invalid.
- Avoid duplicated business logic.
- Keep functions and modules focused on clear responsibilities.
- Document non-obvious decisions and important trade-offs.
- Do not claim that a control or check exists until it has been implemented and verified.

## 3. Python coding conventions

- Follow PEP 8 naming and formatting conventions.
- Use descriptive names that communicate intent.
- Use type hints for public functions and important domain interfaces.
- Keep functions focused and avoid unnecessary complexity.
- Raise and handle specific exceptions; do not silently suppress unexpected errors.
- Use automated formatting, linting and type checking as the relevant tools are introduced.
- Avoid embedding secrets, environment-specific configuration or personal data in source code.

The precise tool configuration will be established in the repository setup and CI work.

## 4. Application architecture

- Keep business logic independent of HTTP request handling wherever practical.
- Separate API routes, domain or service logic, persistence and document generation.
- Keep database transactions explicit around related financial operations.
- Use database constraints as well as application validation for critical integrity rules.
- Store monetary amounts in integer pence.
- Represent issued invoices as immutable financial snapshots; use controlled correction records rather than editing issued content.
- Enforce business ownership and tenant isolation at appropriate application and persistence boundaries.

## 5. Data, security and privacy

- Use synthetic data in development and automated tests.
- Never commit real family information, payment details, credentials, tokens or private documents.
- Follow least-privilege access principles.
- Keep secrets outside source control and use appropriate secret management for each environment.
- Restrict access to invoices, receipts and other generated documents.
- Record appropriate audit events for important financial and administrative actions.
- Treat authentication, authorisation and tenant isolation as separate controls.

## 6. Git and branch conventions

Create a separate branch for each meaningful issue or work item, based on the latest `main` branch.

Use this branch naming format:

`<type>/<issue-number>-<short-description>`

Examples:

- `docs/2-engineering-standards`
- `feat/4-billing-calculation`
- `test/5-ci-pipeline`

Use the actual GitHub Issue number; examples do not establish issue numbering.

Commit messages should use a consistent, descriptive format:

`<type>: <short description>`

Examples:

- `docs: define engineering standards`
- `test: cover billing rounding boundaries`
- `feat: implement invoice calculation`

Keep commits focused on related changes. Do not include unrelated files or changes merely because they are available in the working tree.

## 7. Pull request and review practices

- Push issue branches to GitHub and open pull requests targeting `main`.
- Reference the relevant issue in the pull request description.
- Use `Closes #N` when the pull request fully completes the referenced issue.
- Review the diff before requesting or completing a merge.
- Describe the change, tests performed and any limitations in the pull request.
- Require applicable automated checks to pass before merging once those checks are configured.
- Do not bypass failing checks without understanding and documenting the reason.

For the initial project, these practices are followed manually until repository rules and automated enforcement are introduced.

## 8. Financial correctness

- Use integer pence for stored monetary amounts.
- Document the precision of quantities, intermediate calculations, conversions and rounding points.
- Make rounding behaviour explicit and deterministic.
- Prevent duplicate financial operations where retries could otherwise create duplicate records.
- Reject payment allocations that exceed the available payment amount or outstanding invoice balance.
- Distinguish funding approval from funds actually received.
- Preserve issued invoice content and correct errors through the approved correction process.

The detailed arithmetic policy is maintained in `docs/decisions/0001-billing-money-and-rounding.md`.

## 9. Definition of done

A change is complete when:

- Relevant acceptance criteria are satisfied.
- Appropriate automated tests have been added or updated and pass.
- Configured formatting, linting, type and other quality checks pass.
- Security, privacy and financial integrity implications have been considered.
- Relevant documentation has been updated.
- No secrets or real family or financial data have been introduced.
- The change has been reviewed through the agreed pull request workflow.

Checks that have not yet been implemented must not be represented as active automated controls.

## 10. Maintaining these standards

These standards are the initial engineering baseline. Changes should be proportionate to the project's risk and maturity, recorded in version control and reviewed as part of the normal pull request workflow.