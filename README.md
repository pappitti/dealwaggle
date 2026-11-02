# DealWaggle

Private dealflow, shared with intent. Named after the waggle dance bees use to tell the hive where they found something worth knowing.

DealWaggle turns forwarded email and WhatsApp messages into sourced knowledge about people, companies, funds and transactions. New facts are **shared with the team by default**; choose **Only me** for exceptions. Watchlists share selected facts with particular people or organisations, without exposing everything else known about an entity.

This repository now contains a runnable first product slice, not a production-ready SaaS. Provider connections, customer onboarding and agent implementations still need to be completed before real customer data is introduced.

## Run locally

Requires Python 3.13, [uv](https://docs.astral.sh/uv/) and Node.js 20.19+ (22 recommended).

```sh
make install
make demo
```

Start these in separate terminals:

```sh
make demo-api    # API on http://127.0.0.1:8000; explicitly enables demo auth
make worker      # Durable ingestion/extraction queue
make frontend    # App on http://127.0.0.1:5173
```

Open [the app](http://127.0.0.1:5173) or [API documentation](http://127.0.0.1:8000/docs). SQLite keeps local data in `.data/dealwaggle.db`. The seed is idempotent and contains fictional data. The persona selector demonstrates Claire (team owner), Marc (teammate) and Sofia (another firm). Sofia initially sees no deals. Demo identity is forbidden when `DEALWAGGLE_ENVIRONMENT=production`; never expose a demo server outside localhost.

The existing `.env` is preserved. Add settings from [.env.example](.env.example) as needed; environment variables use the `DEALWAGGLE_` prefix. `make api` runs without enabling demo authentication.

## What works

- React/TypeScript frontend using the supplied DealWaggle design system, with theme switching, search, entity filters, personal review statuses, capture forms, inbox review, watchlists and message drafts.
- FastAPI endpoints and a shared SQLAlchemy database package with a versioned Alembic migration.
- People, companies, funds and transactions on companies; sourced assertions hold facts, opinions, confidence and disclosure scope.
- Team visibility, private exceptions, individual/organisation watchlist grants and revocation; a deliberate all-knowledge watchlist includes current and future non-internal facts.
- Forward previews preserve attribution, confidence and an authenticated app link. Internal notes and other people's private facts cannot be exported through the draft endpoint. The user copies the draft; nothing is sent automatically.
- Verified WhatsApp, Resend and Stripe webhooks; durable deduplication; bounded worker retries; explicit blocked states and manual review when extraction is unconfigured.
- Stripe Checkout and billing-portal endpoints for organisation owners, subscription synchronisation from verified events and entitlement checks for enrichment requests. Prices and credentials are configuration, not hard-coded product decisions.
- RS256 JWT validation against a configured issuer/JWKS endpoint. Production browser sign-in and account provisioning are still pending.

## Repository

| Component | Responsibility |
| --- | --- |
| `database/` | Entity and knowledge models; access grants; sources; durable jobs; subscriptions; migrations |
| `backend/` | API, authentication, authorization, provider webhooks, queue worker and tests |
| `frontend/` | React application, built with Vite |
| `design-system/` | Existing brand assets, CSS, tokens and React components; shared npm workspace |
| `docs/` | Architecture, integration contracts, roadmap and verification notes |

Read [the architecture](docs/architecture.md) first, particularly the rules for knowledge ownership and disclosure. [Integrations](docs/integrations.md) describes provider setup and worker operations. [The roadmap](docs/roadmap.md) distinguishes this foundation from the launch scope.

## PostgreSQL

PostgreSQL is the production target. SQLite is only for a single-process local demo and fast tests; it does not validate PostgreSQL worker locking.

```sh
docker compose up -d database
export DEALWAGGLE_DATABASE_URL='postgresql+psycopg://dealwaggle:local-development-only@localhost:5432/dealwaggle'
make migrate
make demo
```

Alternatively, `docker compose up --build` starts PostgreSQL, a migration container, the API and a worker. The API is not authenticated as a demo by default. To run the container stack as a **local demo**:

```sh
DEALWAGGLE_DEMO_MODE=true docker compose up --build -d
DEALWAGGLE_DEMO_MODE=true docker compose exec api /app/.venv/bin/dealwaggle-demo
make frontend
```

Compose contains local development credentials and binds ports to loopback; it is not a production deployment manifest. Do not use both a local and container API on port 8000 at once.

## Validation

```sh
make check
uv run alembic check
```

To run the same tests against PostgreSQL, set `TEST_DATABASE_URL` to a **test database** where the test role can create schemas. Each test creates and removes its own randomly named schema:

```sh
TEST_DATABASE_URL='postgresql+psycopg://dealwaggle:local-development-only@localhost:5432/dealwaggle' uv run pytest -q
```

CI runs the tests against PostgreSQL 17, checks migration drift and downgrade/upgrade, and builds the frontend. See [verification notes](docs/verification.md) for what was actually checked locally.
