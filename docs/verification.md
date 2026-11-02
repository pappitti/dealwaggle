# Verification of the initial foundation

Checked locally on 2 November 2026:

- **25 backend tests passed.** Coverage includes team defaults, private exceptions, selected-fact sharing, raw-source isolation, membership/grant revocation, all-knowledge access, internal-note export rejection, JWT validation, webhook signatures/replay handling, mixed-sender batches, provider body retrieval, queue rollback/retries, subscription refresh and duplicate checkout protection.
- **1 PostgreSQL-only test skipped locally.** It checks that a worker skips a row already locked by another transaction. CI is configured to run it against PostgreSQL 17.
- TypeScript checking and the Vite production build passed.
- Initial Alembic migration applied to the local demo database; schema drift check passed.
- Upgrade → downgrade → upgrade succeeded on a separate temporary SQLite database.
- PostgreSQL migration SQL generated successfully (19 application tables plus Alembic's version table); this is SQL-generation verification, not a PostgreSQL execution test.
- `/ready` returned ready, and the local frontend returned HTTP 200.
- OpenAPI generated successfully for 24 paths.
- Python static checks and whitespace checks passed.
- Browser checks completed after the preview eventually attached: capture of a private fact, its absence for a teammate, explicit watchlist sharing, recipient access, revocation and forward preview generation.
- Inspected dealflow, inbox, watchlist and workspace screens in light/dark themes. Checked the dealflow at a 390px mobile viewport; the document width matched the viewport with no horizontal page overflow. Fixed native sidebar button backgrounds and mobile control sizing.
- Saved a full-page interface screenshot outside the source tree. The local demo includes one clearly labelled fictional record from the browser check; the temporary recipient grant was revoked.

Limits:

- Docker is installed but its daemon was not running. PostgreSQL runtime tests and container builds were not executed locally. The committed CI configuration has not been run on a remote CI service in this session.
- Browser checks are a focused manual smoke test, not a full automated accessibility or cross-browser test suite.
- No live Meta, Resend, Stripe, identity or LLM requests were made. Provider tests use signed fixtures and mocks; real integration setup and testing remain necessary.
- The installed Starlette test client emits a deprecation warning for its HTTPX adapter. Tests pass; adopt the replacement adapter when upgrading the test tooling.

The local preview processes were used for readiness checks only. Follow the README to start the application again.
