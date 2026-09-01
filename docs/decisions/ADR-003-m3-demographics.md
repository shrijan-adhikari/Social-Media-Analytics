# ADR-003 — M3-Inference for Demographics

- **Status:** Accepted
- **Date:** 2026-09-01

## Decision

Use `euagendas/m3inference` as the primary demographic inference project.

Supported outputs are probability distributions for:
- age: `<=18`, `19-29`, `30-39`, `>=40`
- gender: female / male
- organization / non-organization

## Constraints

- Do not claim M3 predicts profession, interests, geography or language.
- Use aggregate/probabilistic reporting.
- Use text-only M3 when image input is unavailable.
- Use `unclassified` when inputs/confidence are inadequate.
- Isolate M3 dependencies behind an adapter/service because it is an older research implementation.
