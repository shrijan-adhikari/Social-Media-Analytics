# ADR-004 — PostgreSQL + NetworkX Instead of a Graph Database

- **Status:** Accepted
- **Date:** 2026-09-01

## Context

The MVP needs interaction-graph analysis: PageRank, Louvain communities, bridge metrics and temporal topic subgraphs.

## Decision

Persist interaction events in PostgreSQL and load relevant subsets into NetworkX for graph computation.

## Rationale

This is sufficient for hackathon-scale analysis and avoids operating another database.

## Consequences

Do not add Neo4j unless graph size/query requirements demonstrate that PostgreSQL + NetworkX is insufficient.
