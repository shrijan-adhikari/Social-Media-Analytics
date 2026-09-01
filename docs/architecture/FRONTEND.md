# FRONTEND.md — Jury UI Contract

The supplied UI concepts define the intended visual direction.

## Visual identity

- near-black analyst/intelligence-console background
- restrained bright-green accent
- thin borders
- dense but readable information
- monospace metadata/details
- strong headings
- confidence/provenance visible
- limited decorative animation

Do not turn the product into a generic admin dashboard.

## Navigation

1. Overview
2. Demographics
3. Sentiment
4. Trends
5. Network

Current scope is Twitter only; no platform switcher is needed.

## Critical interaction

Selecting a narrative/trend must synchronize:
- trend details
- sentiment
- demographics
- network
- propagation timeline

This is more important than adding additional pages.

## Screen requirements

### Overview
Total tweets, engagement, net sentiment, active conversations, sentiment over time, rising narratives, audience snapshot, analysis activity, affinity/community clusters.

### Demographics
Only show supported outputs:
- M3 age buckets
- gender distribution for classified human accounts
- organization/non-organization
- language as a separate signal
- declared/geocoded location only when available
- coverage/confidence

### Sentiment
Positive/neutral/negative, sarcasm probability, timeline, emotion only after a model is approved, anomaly/sarcasm log.

### Trends
Rising topics, mentions, velocity, change, heatmap, selected narrative details and cross-vector insights.

### Network
Interactive graph, PageRank-sized nodes, community differentiation, selected-user detail, interaction counts, bridge information and propagation timeline.

## Technology target

Next.js + React + TypeScript. Use an appropriate chart library and Cytoscape.js/Sigma.js for network visualization. Frontend may deploy to Vercel.
