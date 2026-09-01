# API.md — FastAPI Contract

> Directional API contract. Adapt to existing routes instead of creating duplicates.

## Principles

- HTTP routes orchestrate services; they do not contain ML implementation logic.
- Long-running collection/analysis returns a job ID/status instead of blocking.
- API responses must distinguish unavailable/unclassified analytics from zero values.
- Use stable internal IDs plus Twitter IDs where the UI needs provenance.
- Use UTC ISO-8601 timestamps.

## Planned endpoints

```text
GET  /api/overview
GET  /api/tweets

GET  /api/trends
GET  /api/trends/{topic_id}
GET  /api/trends/{topic_id}/timeline
GET  /api/trends/{topic_id}/sentiment
GET  /api/trends/{topic_id}/demographics
GET  /api/trends/{topic_id}/network
GET  /api/trends/{topic_id}/propagation

GET  /api/sentiment/summary
GET  /api/demographics/summary
GET  /api/network/communities
GET  /api/network/users/{user_id}

POST /api/analysis
GET  /api/analysis/{analysis_id}/status
```

## Error behavior

Prefer structured errors:
- `400` invalid input
- `404` unknown resource
- `409` conflicting job/state where appropriate
- `422` validation failure
- `503` model/collector dependency temporarily unavailable

Do not return fabricated analytics when an upstream model has not run.
