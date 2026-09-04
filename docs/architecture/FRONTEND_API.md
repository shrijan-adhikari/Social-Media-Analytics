# FRONTEND ↔ BACKEND INTEGRATION ARCHITECTURE

> **Milestone Status:** Implemented, Tested, and Verified against PostgreSQL 17.

## 1. Overview & Architectural Boundaries

The frontend provides a dark, high-density intelligence dashboard for Twitter/X analytical telemetry. It is strictly separated from the analytical inference pipeline and the database layer:

- **Frontend Target:** Next.js 14 (`app/` router), React 18, Tailwind CSS, Recharts, Cytoscape.js.
- **Backend Target:** FastAPI (`/api/v1/*`), SQLAlchemy 2.0 ORM, PostgreSQL 17.
- **Security Boundary:** The frontend never connects directly to PostgreSQL and never receives database credentials, Twitter credentials, or model checkpoint filesystem paths.
- **Computation Boundary:** The FastAPI read layer **never** performs on-demand HuggingFace model inference, MiniLM embeddings, HDBSCAN clustering, or graph construction. Endpoints are strictly **O(1) read operations over persisted PostgreSQL tables**.

---

## 2. API Endpoints Specification

### Base URL: `/api/v1`

| Method | Endpoint | Description | Primary Database Table(s) |
|---|---|---|---|
| `GET` | `/overview` | Global KPIs: tweet counts, coverage, sentiment %, emerging topic, network summary | `tweets`, `sentiment_results`, `trend_windows`, `network_analysis_runs` |
| `GET` | `/tweets` | Paginated tweets with username, sentiment, and topic (supports `topic_id`, `sentiment`, `fusion_status`) | `tweets`, `users`, `sentiment_results`, `tweet_topics` |
| `GET` | `/sentiment/summary` | Global or topic-filtered sentiment breakdown & exact stored sarcasm fusion states | `sentiment_results`, `tweet_topics` |
| `GET` | `/sentiment/timeline` | Chronological sentiment trajectory for 24h charting (`1h`, `4h`, `1d` intervals) | `tweets`, `sentiment_results` |
| `GET` | `/trends` | Discovered topics from latest run with velocity, acceleration, and terms | `trend_analysis_runs`, `topics`, `trend_windows` |
| `GET` | `/trends/{topic_id}` | Detailed topic metadata and latest window metrics | `topics`, `trend_windows` |
| `GET` | `/trends/{topic_id}/timeline` | 15-minute windowed velocity/acceleration points for charting | `trend_windows` |
| `GET` | `/trends/{topic_id}/sentiment` | Read-only join of topic tweets with sentiment classifications | `sentiment_results`, `tweet_topics` |
| `GET` | `/trends/{topic_id}/network` | Topic-specific network topology and influence metrics (with fallback) | `network_analysis_runs`, `network_nodes`, `network_edges` |
| `GET` | `/network/summary` | Quality metrics (density, components, sparsity warnings) for interaction network | `network_analysis_runs` |
| `GET` | `/network/nodes` | Ranked nodes by PageRank, betweenness, degrees, and community ID | `network_nodes`, `users` |
| `GET` | `/network/edges` | Directed interaction edges with aggregated interaction weights | `network_edges`, `users` |
| `GET` | `/network/communities` | Detected Louvain communities with member volume and top users | `network_nodes` |
| `GET` | `/network/flows` | Observed cross-community interaction flows | `community_flows` |
| `GET` | `/analysis/status` | Real pipeline execution status across all roadmap capabilities | Multi-table telemetry |

---

## 3. Approved User Corrections & Implementation Truths

1. **Non-Causal Terminology:**
   - Terminology strictly adheres to empirical observation: *observed narrative progression*, *observed interaction flow*, *cross-vector signals*, *narrative intelligence*.
   - Temporal association is reported without making unsupported causal assertions.
2. **Deterministic Metric Representation (No Fake Topic Confidence):**
   - Removed manufactured "topic confidence" score.
   - Real persisted metrics exposed: `tweet_count`, `current_mentions`, `baseline_mentions`, `velocity`, `acceleration`, and `representative_terms`.
3. **Explicit Sarcasm Proxy Semantics:**
   - Exposed as `sarcasm_score` (representing uncalibrated T5 sequence log-likelihood) and `high_sarcasm_evidence` (`score >= 0.85`).
   - Stored fusion statuses used verbatim: `NO_SARCASM`, `SARCASM_CONSISTENT`, `SARCASM_AMBIGUOUS`, `SARCASM_UNCERTAIN`.
4. **Near-Real-Time Analytics:**
   - Dashboard is labeled: `Latest Analysis Run: <timestamp> UTC` with `PIPELINE ACTIVE` badge, replacing fake simulated "LIVE" socket indicators.
5. **Interactive Cytoscape.js Topology:**
   - Directed interaction graphs render with node sizing proportional to PageRank score, node border colors mapped to Louvain `community_id`, and edge widths scaled to `total_weight`.
   - Clicking a node reveals real uncollapsed metrics: PageRank, betweenness centrality, in-degree volume, cross-community edge counts, and communities reached.
6. **Non-Silent Topic Network Fallback:**
   - If a selected topic lacks a topic-specific network run, the UI explicitly shows:
     *"No topic-specific network analysis available for #<topic>. Showing global network."*
   - Banner clearly denotes: `GLOBAL NETWORK — NOT FILTERED TO SELECTED TOPIC`.
7. **Explicit Unavailable Audience State:**
   - Audience / demographic cards explicitly report: *"Demographic inference is not available in the current analysis run. M3-Inference demographic profiling is scheduled for Phase 5."*
