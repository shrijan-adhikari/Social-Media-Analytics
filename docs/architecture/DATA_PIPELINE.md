# DATA_PIPELINE.md — Twitter Data Flow

## End-to-end path

```text
twscrape
   ↓
raw Twitter objects/responses
   ↓
collectors/twitter normalizer
   ↓
normalized users/tweets/interactions
   ↓
PostgreSQL
   ↓
independent analytics
   ├── sentiment/sarcasm
   ├── M3 demographics
   ├── trend/topic detection
   └── NetworkX analysis
   ↓
cross-vector aggregation
   ↓
FastAPI
   ↓
Next.js dashboard
```

## Boundary rules

- twscrape objects must not leak into analytics modules.
- Normalize once at the collection boundary.
- Persist normalized records before expensive analytics where practical.
- Analytics results link back to canonical tweet/user/topic IDs.
- Raw source information should remain recoverable for debugging/provenance.
- Re-running analytics should not require recollecting Twitter data when stored data is sufficient.

## Twitter interaction extraction

Initial interaction types:
- reply
- repost
- quote
- mention

Document edge direction in code/tests before graph metrics are implemented.

## Reproducibility

A small reproducible stored dataset should exist before Phase 2 analytics so models can be tested without relying on live collection for every run.
