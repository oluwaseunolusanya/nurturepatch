# NurturePatch — Roadmap

**Current stage:** Stage 0 (update this line whenever a stage closes) **Product goal:** a correct, secure invoicing, payment and receipt tool that a UK childminder uses for real, and that other childminders may use later. **Engineering goal:** deliver and run it to a professional DevOps standard (CI/CD, containers, Terraform, AWS, observability, security), so each piece of infrastructure has a product reason. **Related docs:** `docs/product-spec.md`, `docs/backlog.md`, `docs/decisions/`

## Fixed decisions (change only via ADR)

- **Stack:** Python 3.12, SQLAlchemy, Alembic, PostgreSQL.
- **UI:** server-rendered pages (FastAPI, Jinja templates, HTMX). No separate JavaScript frontend. A JSON API may be added later alongside it.
- **Money:** integer pence for authoritative totals, `Decimal` for intermediate calculations, never floats (see ADR 0001).
- **Tenancy:** every business-owned record carries `business_id`; isolation is enforced by scoped queries and composite foreign keys.
- **Cloud:** AWS, defined in Terraform. ECS Fargate before anything heavier. No Kubernetes in this repo.
- **Data:** fictional data only until the Stage 6 pilot checks pass.

## Rules for sticking to the plan

1. **One stage at a time.** The next stage does not start until every exit criterion of the current one is ticked.
2. **One issue per branch, one branch per pull request.** Each issue cites the backlog story it implements (for example US-013).
3. **Parking lot.** New ideas go in the Parking lot below, not into the current stage. Review it only at stage boundaries.
4. **Changing the plan needs an ADR.** Stack, order and scope changes are written down first.
5. **CI hardening is incremental.** Add small CI improvements inside stages 1 to 3 (each as its own issue) instead of a stage of its own.
6. **Timebox.** Target 2–3 weeks per stage at evenings/weekends pace. If a stage overruns by 50%, cut scope instead of extending it.
7. **Definition of done:** acceptance criteria met, tests added, CI green, docs updated, reviewed through a pull request.
8. **AI assistant rule:** start each session by pasting the current issue, ask for a plan before code, and reject changes outside the issue.

## Stage 0 — Baseline and guardrails

*Backlog: US-021, part of US-022*

- [ ] `requirements-dev.txt` exists and CI installs from it
- [ ] CI is green on `main`; branch protection requires a pull request and passing CI
- [ ] ADR 0001 (money and rounding) accepted, including how negative adjustments round
- [ ] Open issues mapped to stages and labelled

## Stage 1 — Payments, allocations and receipts

*Backlog: US-011, US-012 to US-015. The original pain point.*

- [ ] `payments`, `payment_allocations` and `receipts` models with migration
- [ ] Idempotent payment recording
- [ ] Allocations cannot exceed the payment amount or invoice balance, including under concurrency (tests)
- [ ] Outstanding balance derived from issued invoices, corrections and confirmed allocations
- [ ] Receipts only for confirmed payments; unique numbering per business
- [ ] Invoice `due_date` added
- [ ] Database protection against edits to lines of non-draft invoices
- [ ] CI additions: coverage reporting, `pip-audit`, Dependabot, `Makefile` for local checks

## Stage 2 — API, authentication and container

*Backlog: US-019, US-023*

- [ ] FastAPI app with `/health` and `/ready`
- [ ] Business-scoped operations: create draft, issue invoice, record payment, allocate payment
- [ ] Authentication with secure sessions; cross-business access tests
- [ ] Multi-stage Dockerfile, non-root user, healthcheck
- [ ] Compose runs app and database together
- [ ] CI builds the image and scans it (Trivy); Dockerfile linted
- [ ] CI additions: migration check (upgrade to head, no pending autogenerate diff), secret scanning

## Stage 3 — Minimal UI and PDFs

*Backlog: US-008, US-010, US-015 (documents), US-005, US-006*

- [ ] Pages for families and children, rates, invoice preview and issue, payment entry and allocation
- [ ] Mobile-friendly layout, tested on a phone-sized browser
- [ ] Invoice and receipt PDFs generated from saved snapshots, stored privately, served by short-lived access
- [ ] Rate plans with effective dates and overlap prevention
- [ ] **Milestone:** your friend can complete the full workflow on fictional data (create invoice, record part-payment, download receipt)

## Stage 4 — AWS, deployment, backups and monitoring

*Backlog: US-024, US-022*

- [ ] Terraform remote state (S3 with locking), VPC, ECR, ECS Fargate (or App Runner), RDS PostgreSQL
- [ ] Secrets in Secrets Manager; least-privilege IAM; GitHub Actions authenticates through OIDC
- [ ] Billing budget and alert set; destroy runbook written and tested
- [ ] `terraform fmt`, `validate` and `checkov` (or `tfsec`) in CI
- [ ] Merge to `main` deploys to staging; production behind a manual approval gate
- [ ] Alembic migrations as a controlled deploy step; rollback documented
- [ ] Post-deploy smoke test; image tagged by commit SHA; SBOM generated
- [ ] Structured JSON logs without personal data or secrets
- [ ] CloudWatch alarms and dashboard; one or two written SLOs
- [ ] Encrypted backups; restore drill completed and invoice/payment/receipt relationships verified
- [ ] One deliberate failure injected and a post-incident review written

## Stage 5 — Funding rules and audit trail

*Backlog: US-016 to US-018, US-020*

- [ ] UK nation confirmed and recorded in an ADR; applicable guidance linked
- [ ] Funding records separate expected, claimed, approved and received amounts
- [ ] Funded entitlement hours kept distinct from private paid hours and optional extras
- [ ] Parent opt-in or opt-out recorded for optional extras; mandatory extras cannot be added to funded hours
- [ ] Audit events for issue, payment, correction, export and access changes
- [ ] Tests for compliant and non-compliant billing scenarios

## Stage 6 — Pilot

- [ ] Privacy notice, retention periods and DPIA screening documented
- [ ] ICO fee and registration position checked for the childminder
- [ ] Data export and correction/erasure process tested
- [ ] Parallel run: fictional data first, then a few real invoices alongside her current process
- [ ] Her sign-off recorded; known limitations and follow-ups written down

## Stage 7 — Other childminders

- [ ] Controller/processor roles decided; data processing agreement and terms drafted (take legal advice)
- [ ] Onboarding flow and tenant provisioning
- [ ] Per-tenant data export and deletion
- [ ] Support process, incident response and insurance considered
- [ ] Cost and pricing model (or confirmation that it stays free for friends)

## Parking lot

Ideas not in the current stage. Review at stage boundaries only.

- Email delivery with retry and delivery tracking
- Reporting dashboard and monthly overview
- Row-level security in PostgreSQL as defence in depth
- JSON API for a future mobile client
- Kubernetes redeploy of the same image (separate learning exercise)
- Funding claim submission to local authorities

## Stage log

| Stage | Started | Closed | Notes |
| ----- | ------- | ------ | ----- |
| 0     |         |        |       |