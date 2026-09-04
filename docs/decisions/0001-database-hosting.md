# 0001. Database Hosting Strategy

Date: 2026-09-02

## Status
Accepted

## Context
Per `PROJECT_CONTEXT.md` §11, plain PostgreSQL is required as the canonical application database, and Supabase is forbidden. We need to decide how to host and provision this database for both local development and production.

## Decision
- **Local Development**: We will use a local containerized PostgreSQL instance via `docker-compose`. This ensures parity without polluting the host environment, while adhering to the requirement to avoid SQLite for the primary data layer.
- **Testing**: Automated integration tests will use the same Dockerized PostgreSQL instance (or an in-memory SQLite fixture when testing domain models and non-PostgreSQL-specific queries).
- **Production (Phase 4)**: To be determined (e.g., Neon or Railway), but the connection string will be provided exclusively via the `DATABASE_URL` environment variable.

## Consequences
- Developers must have Docker installed.
- Network configurations (e.g., `127.0.0.1` vs `localhost`) must be carefully managed to avoid IPv6 `psycopg` connection hangs.
- All migrations must be thoroughly tested against the local PostgreSQL instance.
