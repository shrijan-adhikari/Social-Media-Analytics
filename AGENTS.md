# AGENTS.md — Agent Entry Point

> Applies to every coding agent working in this repository.

## Mandatory startup sequence

Before editing code:

1. Read `PROJECT_CONTEXT.md`.
2. Read `CURRENT_STATE.md`.
3. Read the relevant quick-reference document under `docs/`.
4. Inspect the repository tree and existing implementation/tests.
5. Make the smallest change needed for the requested task.

## Canonical sources

When documentation conflicts, use this precedence:

1. Latest explicit user instruction
2. `CURRENT_STATE.md`
3. `PROJECT_CONTEXT.md`
4. Accepted ADRs under `docs/decisions/`
5. Architecture/research quick references
6. `README.md`

`PROJECT_CONTEXT.md` is the canonical product/technical specification.

## Fixed constraints

- Current source scope: **X/Twitter only**
- Twitter acquisition: **twscrape**
- Canonical application database: **PostgreSQL**
- ORM: **SQLAlchemy**
- Migrations: **Alembic**
- Backend: **FastAPI / Python**
- Demographics: **M3-Inference**
- Graph processing: **NetworkX**
- Influence: **weighted PageRank**
- Communities: **Louvain**
- Frontend target: **Next.js / React / TypeScript**
- Do not introduce Supabase, MongoDB, Neo4j, Kafka, Redis, or another primary database without explicit approval.

## Engineering rules

- Never commit credentials, cookies, tokens, proxy secrets, or twscrape session databases.
- Keep twscrape behind `collectors/twitter/`.
- Keep ML inference behind analytics/service interfaces.
- Keep M3 isolated behind its adapter/service.
- Keep graph computation separate from persistence.
- Use UTC internally.
- Preserve raw Twitter IDs and interaction relationships.
- Persist model/checkpoint/version/confidence where required by `PROJECT_CONTEXT.md`.
- Never fabricate benchmark results.
- Never silently select a model marked `NOT SELECTED`.
- Never silently replace a `PRIMARY / APPROVED` model.
- Do not hardcode fake analytics into production code paths.
- Prefer a working vertical slice over premature infrastructure.

## Completion protocol

After substantial work:

1. Run relevant tests/lint/type checks.
2. Update `CURRENT_STATE.md`.
3. State files changed.
4. State tests performed and results.
5. State remaining limitations/blockers.
6. If architecture changed, create/update an ADR.

Do not mark a milestone complete when tests are failing unless the failure and reason are explicitly recorded.
