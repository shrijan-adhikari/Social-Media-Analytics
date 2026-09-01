# ADR-001 — PostgreSQL as Canonical Application Database

- **Status:** Accepted
- **Date:** 2026-09-01

## Context

The application needs concurrent Twitter collection, relational joins across users/tweets/topics/analytics, model-result persistence, and deployment independent of the frontend.

## Options considered

- SQLite as central DB
- Supabase-hosted PostgreSQL with Supabase-specific services
- Plain managed PostgreSQL

## Decision

Use **plain PostgreSQL** as the canonical application database, accessed through SQLAlchemy and migrated with Alembic.

SQLite is limited to twscrape/session/cache/local testing.

## Rationale

PostgreSQL provides the required relational/concurrency capabilities without coupling application code to Supabase-specific APIs, authentication, or PostgREST.

## Consequences

A managed PostgreSQL hosting provider still needs to be selected. That provider choice should not change application data-access code.
