# DATABASE.md — PostgreSQL Contract

> Quick implementation contract. `PROJECT_CONTEXT.md` remains authoritative.

## Decision

Canonical application database: **plain PostgreSQL**.

Do not use Supabase-specific SDK/Auth/PostgREST features. Access PostgreSQL through SQLAlchemy and manage schema with Alembic.

SQLite is allowed only for twscrape/session/cache/local testing.

## Core entities

### users
Twitter identity/profile information required by analytics and M3.

### tweets
Normalized tweet content, relationships, engagement and ingestion metadata.

### interactions
Persistent directed interaction events for reply/repost/quote/mention.

### sentiment_results
Base sentiment probabilities, sarcasm evidence, final interpretation, confidence and model provenance.

### demographic_estimates
M3 probability distributions, coverage/confidence and model provenance.

### topics
Semantic narrative/topic metadata.

### tweet_topics
Tweet↔topic membership/similarity.

### trend_windows
Windowed mention/velocity/acceleration and later community-spread metrics.

## Database rules

- Store Twitter IDs in a form that preserves full identifier precision.
- Enforce uniqueness on canonical Twitter tweet/user IDs.
- Store timestamps in UTC.
- Preserve ingestion timestamps separately from tweet creation timestamps.
- Keep raw/recoverable source payload references where practical.
- Add indexes based on real query patterns, especially timestamps, author IDs, topic membership and interaction endpoints.
- Use migrations for every schema change.
- Do not edit production schema manually without a corresponding migration.
- Keep model provenance fields needed by `PROJECT_CONTEXT.md` §24.11.

## Graph persistence

PostgreSQL stores interaction events/edges. NetworkX performs graph computation.

Do not introduce a graph database unless a demonstrated requirement is approved via ADR.
