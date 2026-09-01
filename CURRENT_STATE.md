# CURRENT_STATE.md

> Update this file after every substantial milestone, per
> PROJECT_CONTEXT.md §18/§26. Keep it short and current — this is a
> status snapshot, not a design document.

## Status: Not yet started

- **Last updated:** 2026-09-01
- **Current phase:** Phase 1 — Twitter foundation (see PROJECT_CONTEXT.md §13)
- **What exists in the repo right now:** nothing yet / describe here
  once code exists.

## Completed

- (nothing yet)

## In progress

- (nothing yet)

## Known limitations / open decisions

- Emotion model not yet selected (PROJECT_CONTEXT.md §24.4b)
- Stance ("supportive"/"against") model not yet selected (§24.4c)
- MuRIL fallback remains DISABLED pending evaluation (§24.5)

## Resolved decisions

- **Database:** plain managed PostgreSQL, not Supabase (§11). Specific
  hosting provider (Railway/Render/Neon/self-managed) still needs to be
  picked and recorded in an ADR under `docs/decisions/`.

## Next recommended step

Begin Phase 1, step 1: environment/config/secrets setup, then
PostgreSQL schema via SQLAlchemy + Alembic migrations.
