# ADR-002 — Twitter-Only MVP

- **Status:** Accepted
- **Date:** 2026-09-01

## Context

The SIH problem statement is multi-platform, but implementing and validating every platform simultaneously would dilute the first working vertical slice.

## Decision

Current implementation scope is **X/Twitter only**, collected through twscrape.

Telegram, Instagram, Facebook, Reddit and YouTube are explicitly deferred.

## Rationale

The team can demonstrate the complete analytical pipeline—collection, sentiment, demographics, trends, networks and narrative propagation—on one platform before expanding adapters.

## Consequences

Do not add multi-platform abstractions that materially slow the Twitter MVP. Keep collection boundaries clean enough for future adapters.
