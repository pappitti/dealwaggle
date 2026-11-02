# Working on DealWaggle

Use the Python/uv and npm workspace lockfiles. Keep API behavior in `backend/`, shared persistence in `database/`, and interface code in `frontend/`.

For frontend changes, read `design-system/AGENTS.md` and `design-system/GUIDELINES.md`; import the shared styles, reuse the supplied brand assets, and extend the design system's specimen when adding a reusable component.

Every entity/fact read must apply the shared visibility predicate. Avoid serializing ORM records directly. Search, counts, exports, recommendations and future agents must respect the same access boundary. Never grant access using identifiers extracted from a forwarded message. A fact someone can read is not necessarily a fact they may re-share.

Use migrations for schema changes. The initial migration is explicit and independent of future model changes. Regenerate a revision with `uv run alembic revision --autogenerate -m 'Describe the change'`, inspect it, then apply it. Do not use `create_all` at application startup.

Run `make check` for a functional change and `uv run alembic check` for persistence changes. Use PostgreSQL tests for locking/concurrency changes. Add regression tests for actual isolation or workflow failures, not tests that merely restate implementation details.

Secrets stay in local environment configuration. Synthetic demo identities and channel examples are not customer data. Keep raw message contents and provider response bodies out of logs, audit records and exception strings.
