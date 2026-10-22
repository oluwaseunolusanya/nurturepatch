# NurturePatch

NurturePatch is a childminder invoicing application intended to help manage childcare invoices, payments, receipts, and funding reconciliation.

The project is being developed incrementally, with an emphasis on financial accuracy, maintainable code, automated testing, and reliable delivery.

## Project status

Early development. The initial repository structure, database models, and engineering workflow are being established before the application features are built.

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
- `app/db/` — SQLAlchemy database base and models.
- `app/schemas/` — Application data schemas and validation.
- `app/services/` — Business logic and application services.
- `alembic/` — Database migration configuration and revision files.
- `docs/` — Product requirements, backlog, engineering standards, and decisions.
- `tests/` — Automated tests.
- `compose.yaml` — Local PostgreSQL test database configuration.

## Prerequisites

- Git
- Python 3.12
- Docker Engine and Docker Compose

Check your installations:

```bash
python3 --version
python3 -m pip --version
git --version
sudo docker --version
sudo docker compose version
```

## Local development setup

Run these commands from the repository root.

### 1. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the project and development dependencies:

```bash
python -m pip install -r requirements-dev.txt
```

### 2. Start the local PostgreSQL test database

Start the database defined in `compose.yaml`:

```bash
sudo docker compose up -d postgres-test
sudo docker compose ps
```

Wait until the database reports a healthy status before running the model tests or migrations.

The Compose configuration binds PostgreSQL to `127.0.0.1:5433`, keeping the test database accessible only through the local machine's loopback interface.

The configured database is named `nurturepatch_test`. Its credentials are for local development only and must never be reused in production.

To stop the service when you have finished:

```bash
sudo docker compose down
```

This stops and removes the container but does not explicitly delete the Compose-managed data volume, if one is added in future.

### 3. Configure the database connection

The model tests and Alembic migrations use separate environment variables.

For the dedicated local test database, set both in the current terminal:

```bash
export TEST_DATABASE_URL='postgresql+psycopg://nurturepatch_test:test_only_password@127.0.0.1:5433/nurturepatch_test'
export DATABASE_URL="$TEST_DATABASE_URL"
```

- `TEST_DATABASE_URL` is used by the model-test fixture. The fixture checks that it targets the dedicated `nurturepatch_test` PostgreSQL database and creates an isolated schema for each test.
- `DATABASE_URL` is used by Alembic to connect to the database for migrations.

These example credentials match the local `compose.yaml` configuration. They are not production credentials.

Environment variables set this way apply only to the current shell and its child processes. Set them again in a new terminal session when needed. Never commit real database credentials or production connection URLs.

### 4. Apply and inspect database migrations

With the virtual environment activated, the local PostgreSQL database healthy, and `DATABASE_URL` set, run:

```bash
alembic upgrade head
alembic current
```

`alembic upgrade head` applies outstanding migrations. `alembic current` displays the revision recorded by the database.

To generate a new migration after changing SQLAlchemy models:

```bash
alembic revision --autogenerate -m "describe the schema change"
```

Review the generated migration before applying it. Autogeneration is not a substitute for reviewing foreign keys, constraints, column types, and upgrade or downgrade operations.

Do not run development migration commands against a production database.

### 5. Run automated checks

With `.venv` activated, run:

```bash
python -m ruff check .
python -m ruff format --check .
python -m pytest
```

These commands check code quality, verify formatting without modifying files, and run the automated test suite, respectively.

The model tests require the dedicated PostgreSQL test database and `TEST_DATABASE_URL`. Keep that database available while running the suite.

Run all three checks before submitting a pull request.

Development dependencies are declared in `requirements-dev.txt`. The same checks run in GitHub Actions for pull requests and pushes to `main`.

## Configuration and sensitive data

- `.env.example` documents example local configuration variables.
- Keep real credentials in local environment configuration or an appropriate secret manager; never commit them.
- Do not commit real family information, invoices, receipts, or private financial documents.
- Use fictional data for development and testing.

## Documentation

- `docs/product-spec.md` — Product requirements and open questions.
- `docs/backlog.md` — Planned work and acceptance criteria.
- `docs/engineering-standards.md` — Coding and development conventions.
- `docs/test-strategy.md` — Testing approach.
- `docs/decisions/0001-billing-money-and-rounding.md` — Proposed money and rounding policy.

## Contributing

Follow the engineering standards, work on a dedicated branch for each issue, run the relevant automated checks, and submit changes through a pull request.