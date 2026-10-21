
# NurturePatch

NurturePatch is a childminder invoicing application intended to help manage
childcare invoices, payments, receipts, and funding reconciliation.

The project is being developed incrementally, with an emphasis on financial
accuracy, maintainable code, automated testing, and reliable delivery.

## Project status

Early development. The initial repository structure and engineering
documentation are being established before the application features are built.

## Core capabilities planned

- Manage families, children, and childcare agreements.
- Calculate invoice charges using agreed rates and billing rules.
- Generate invoices and handle corrections.
- Record full and partial payments and allocate them to invoices.
- Generate receipts for confirmed payments.
- Reconcile expected childcare funding with approvals and amounts received.
- Protect family information and maintain an audit trail.

These are planned capabilities, not claims that the features are implemented.

## Repository structure

- `.github/workflows/` — GitHub Actions workflow files.
- `app/` — Python application package.
- `app/schemas/` — Application data schemas and validation.
- `app/services/` — Business logic and application services.
- `docs/` — Product requirements, backlog, engineering standards, and decisions.
- `tests/` — Automated tests.

## Prerequisites

- Git
- Python 3
- `pip`, Python's package installer

Check your Python and Git installations:

```bash
python3 --version
python3 -m pip --version
git --version
```

## Local development setup

Run these commands from the repository root.

1. Create a virtual environment:

   ```bash
   python3 -m venv .venv
   ```

2. Activate it on Linux or macOS:

   ```bash
   source .venv/bin/activate
   ```

3. Install the development dependencies:

   ```bash
   python -m pip install -r requirements-dev.txt
   ```

4. Run the automated checks:

   ```bash
   python -m ruff check .
   python -m ruff format --check .
   python -m pytest
   ```

   These commands check code quality, verify formatting without modifying files, and run the automated test suite, respectively. Run all three before submitting a pull request.

Development dependencies are declared in `requirements-dev.txt`. The same checks run in GitHub Actions for pull requests and pushes to `main`. The initial test suite verifies that the application packages can be imported. Additional tests will be added as application features are implemented.

## Configuration and sensitive data

- `.env.example` documents example local configuration variables.
- Keep real credentials in local environment configuration or an appropriate
  secret manager; never commit them.
- Do not commit real family information, invoices, receipts, or private
  financial documents.
- Use fictional data for development and testing.

## Documentation

- `docs/product-spec.md` — Product requirements and open questions.
- `docs/backlog.md` — Planned work and acceptance criteria.
- `docs/engineering-standards.md` — Coding and development conventions.
- `docs/test-strategy.md` — Testing approach.
- `docs/decisions/0001-billing-money-and-rounding.md` — Proposed money and
  rounding policy.

## Contributing

Follow the engineering standards, work on a dedicated branch for each issue,
run the relevant automated checks, and submit changes through a pull request.
