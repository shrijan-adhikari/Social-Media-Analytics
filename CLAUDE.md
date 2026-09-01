# CLAUDE.md — Claude Agent Instructions

Before any implementation task:

1. Read `PROJECT_CONTEXT.md` completely.
2. Read `CURRENT_STATE.md`.
3. Read `AGENTS.md`.
4. Inspect relevant code and tests before proposing changes.

`PROJECT_CONTEXT.md` is authoritative for architecture, model selection, scope, data contracts, and jury-facing claims.

Do not redesign the project or replace approved technologies unless explicitly asked.

For ML work, also read `docs/research/MODELS.md`.

For database/API work, also read:
- `docs/architecture/DATABASE.md`
- `docs/architecture/API.md`

For frontend work, also read:
- `docs/architecture/FRONTEND.md`

For a substantial task:
- first give a short implementation plan,
- implement incrementally,
- run relevant verification,
- update `CURRENT_STATE.md`,
- summarize changed files, tests, and unresolved limitations.
