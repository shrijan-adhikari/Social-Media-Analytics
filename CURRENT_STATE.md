# CURRENT_STATE.md

> Update this file after every substantial milestone, per
> PROJECT_CONTEXT.md §18/§26. Keep it short and current — this is a
> status snapshot, not a design document.

## Status: Frontend ↔ Backend Integration Complete

- **Last updated:** 2026-09-03
- **Current phase:** Frontend ↔ Backend Integration - Implemented, Tested, and Verified
- **Milestone Matrix:**
  - Twitter ingestion:                 **COMPLETE**
  - Sentiment (XLM-RoBERTa):           **COMPLETE**
  - Sarcasm / fusion (T5):             **COMPLETE**
  - Trend detection (MiniLM + HDBSCAN):**COMPLETE**
  - Multi-query collection/provenance: **COMPLETE**
  - Network analysis (PageRank/Louvain):**COMPLETE**
  - Frontend Read API (FastAPI v1):    **COMPLETE**
  - Intelligence Dashboard (Next.js):  **COMPLETE**
  - Demographics (M3):                 NOT STARTED (Phase 5)
  - Emotion:                           NOT STARTED
  - Stance:                            NOT STARTED
  - Narrative propagation:             NOT STARTED

## What exists in the repo right now:
- Python project environment (`pyproject.toml`) with dependencies including `torch`, `transformers`, `sentencepiece`, `protobuf`, `scikit-learn`, and `networkx`.
- SQLAlchemy 2.x ORM models:
  - Phase 1: `User`, `Tweet`, `Interaction`
  - Phase 2: `SentimentResult`
  - Phase 3: `TrendAnalysisRun`, `Topic`, `TweetTopic`, `TrendWindow`
  - Post-Phase-3A: `CollectionQuery`, `CollectionRun`, `TweetCollectionSource`
  - Phase 4: `NetworkAnalysisRun`, `NetworkNode`, `NetworkEdge`, `CommunityFlow`
- Alembic migrations applied up to `0006_add_network_analysis`.
- Real Twitter dataset in PostgreSQL: **256 stored live tweets** and **206 interactions** across diverse topics.
- Network Analysis & Influence Topology Engine:
  - Directed interaction graph builder with actor $\to$ referenced user semantics.
  - PageRank influence scoring on incoming directed edges.
  - Degree centrality (in/out degree and weighted volume).
  - Explicit undirected weighted Louvain projection ($W\{A,B\} = W(A\to B) + W(B\to A)$).
  - Shortest-path betweenness centrality using derived distance ($distance = 1.0 / weight$).
  - Bridge metrics (cross-community edge count, communities reached).
  - Observed cross-community interaction flows.
  - Topic-specific graph filtering with read-only community sentiment joins.
- Full Pytest suite: **82 unit tests passing, 0 failed**.

## Completed
- **Phase 1**: Ingestion, normalization, idempotency, PostgreSQL persistence.
- **Phase 2A & 2B**: Primary sentiment, T5 sarcasm, confidence-aware fusion.
- **Phase 3A**:
  - MiniLM checkpoint: `sentence-transformers/all-MiniLM-L6-v2`
  - HDBSCAN hyperparameters: `min_cluster_size=3`, `min_samples=2`, `metric="cosine"` (MVP baseline, configurable)
  - Time window size: `TREND_WINDOW_MINUTES = 15`
  - Baseline window span: `BASELINE_WINDOW_COUNT = 8` (2-hour preceding window span)
  - Velocity formula: `velocity = current_mentions / max(baseline_mentions, 1.0)`
  - Acceleration formula: `acceleration = current_velocity - previous_velocity`
  - Smoothing/minimum support rule: `MIN_SUPPORT_MENTIONS = 2`; topics with < 2 mentions receive `velocity = 0.0` (eliminates 0 -> 1 spurious spikes).
  - Dataset evaluated: 194 stored live tweets spanning ~3.6 days (`2026-08-30 01:29:11` to `2026-09-02 17:38:54 UTC`).
  - Rerun / idempotency verified: Executed multiple runs producing versioned `trend_analysis_runs` without duplicate conflicts.
- **Post-Phase-3A Collection & Data Provenance Improvement:**
  - Config location: `config/collection_queries.yaml` (supporting diverse topics: technology, finance/stocks/crypto, economy, governance, national/India, politics, climate, entertainment, sports).
  - Added schema (Migration `0005_add_collection_provenance`): `collection_queries`, `collection_runs`, `tweet_collection_sources`.
  - Provenance architecture: Each run preserves `config_version` and `effective_query_text`. Deduplication preserved: duplicate tweets across multiple queries/runs maintain a single row in `tweets` while creating multiple provenance links in `tweet_collection_sources`.
  - Strict separation: `collection_query_id` != `topic_id`. Predefined query categories are strictly decoupled from HDBSCAN/MiniLM and never used as semantic cluster labels.
  - Failure isolation: Per-query error isolation; auth failures halt cleanly to avoid spamming X.
  - CLI: `python backend/scripts/collect_queries.py` (with `--config`, `--limit-per-query`, `--query-id` repeated, and `--report`).
- **Phase 4 Network Analysis & Influence Topology:**
  - NetworkX version: `3.6.1`
  - Graph direction semantics: `source_user_id` (author/actor) $\to$ `target_user_id` (referenced/engaged account). Incoming edges represent attention received.
  - Interaction weighting rule: Baseline $w = 1.0$; pairwise repeated interactions summed to `total_weight` across reply, mention, repost, and quote types.
  - PageRank configuration: $\alpha = 0.85$, $max\_iter = 100$, $tol = 10^{-6}$, weighted on canonical interaction strength.
  - Louvain community detection: Explicit undirected weighted projection where $W\{A,B\} = W(A\to B) + W(B\to A)$; run-local community IDs; deterministic `seed = 42`.
  - Shortest-path betweenness semantics: Derived distance attribute ($distance = 1.0 / weight$ for $weight > 0$), ensuring stronger interaction equals shorter graph distance without overwriting canonical weights.
  - Bridge metrics: Betweenness centrality, cross-community edge counts, and communities reached.
  - Cross-community flows: Observed chronological interaction flow between Louvain communities (no causal claims).
  - Scope: Global graph and topic-specific graph filtering (`--topic-id T`) with read-only sentiment aggregation.
  - Real dataset evaluated: 401 total users, 311 connected users, 90 isolated users, 206 interactions (202 aggregated edges).
  - Graph quality: Density $\approx 0.0021$, 127 weakly connected components, 310 strongly connected components, largest WCC = 7 users.
  - Schema: Migration `0006_add_network_analysis` (`network_analysis_runs`, `network_nodes`, `network_edges`, `community_flows`).
  - Tests: 82 unit tests passed, 0 failed.
- **Frontend ↔ Backend Integration Milestone:**
  - FastAPI Read API (`/api/v1/*`):
    - `GET /api/v1/overview`: Global dataset counts, coverage, sentiment percentages, top emerging topic, network summary.
    - `GET /api/v1/tweets`: Paginated tweets with author info, sentiment, and topic tags; raw payload stripped.
    - `GET /api/v1/sentiment/summary` & `/timeline`: Aggregates and chronological trajectory (1h, 4h, 1d) with exact stored fusion statuses (`NO_SARCASM`, `SARCASM_CONSISTENT`, `SARCASM_AMBIGUOUS`, `SARCASM_UNCERTAIN`).
    - `GET /api/v1/trends` & `/trends/{topic_id}` & `/timeline` & `/sentiment`: Real velocity, acceleration, mentions, and term metrics (no fake topic confidence).
    - `GET /api/v1/trends/{topic_id}/network`: Topic-scoped network topology with explicit fallback.
    - `GET /api/v1/network/summary` & `/nodes` & `/edges` & `/communities` & `/flows`: Structural graph telemetry and uncollapsed centrality scores.
    - `GET /api/v1/analysis/status`: Pipeline readiness across all roadmap dimensions.
    - O(1) read operations with zero ML execution during requests.
  - Next.js 14 Frontend Application (`frontend/`):
    - Dark intelligence dashboard aesthetic adhering strictly to `design-reference/dashboard.html`.
    - Key Signals overview cards with 100% PostgreSQL-backed metrics.
    - Recharts 24h Sentiment Trajectory line chart with interval toggles.
    - Sarcasm & Fusion Breakdown with documented threshold evidence.
    - Observed Narrative Progression synchronized to `selectedTopicId` without causal assertions.
    - Topic Signal Board with search, semantic/lexical filtering, and representative tweets drawer.
    - Audience Demographics with explicit unavailable state for Phase 5 (zero fake numbers).
    - Interactive Cytoscape.js network graph with node sizing by PageRank, Louvain coloring, directed arrows, edge widths by weight, and node inspection drawer.
    - Non-silent topic-network fallback banner: `GLOBAL NETWORK — NOT FILTERED TO SELECTED TOPIC`.
    - Unit/Integration Tests: 88 total tests passed (6 new API tests, 0 failed). Full production build succeeded (`next build`).
- **UX / Visualization Refinement Milestone:**
  - Transformed into an **Interactive Narrative Intelligence Workstation** centered on `selectedTopicId`.
  - Persistent **Analysis Context Bar** displaying active narrative, 15m trend window vs total dataset range, and run IDs.
  - **Emerging Narratives Roster** as primary entry point with `INVESTIGATE ->` action that pins the narrative context.
  - **Observed Narrative Progression Workspace** with `FIRST OBSERVED IN SAMPLE` timing, velocity, acceleration, top PR node (`Rank #1 of N`), top bridge account, and representative terms.
  - **Stacked Sentiment Timeline Area Chart** with `[ Volume ]` and `[ Percentage ]` toggles, exact tooltip counts, and stored fusion states.
  - **Interactive Tweets Stream** with sentiment pills (`All`, `Positive`, `Negative`, `High Sarcasm`) and click-to-inspect modal.
  - **Network Topology Workstation (Cytoscape.js)**:
    - Component filtering: `[ Largest Component (Default) ]`, `[ Top 5 Components ]`, `[ All Components ]`.
    - Toggles: Isolated nodes and self-loops OFF by default, node labels, directed arrows, cross-community edge styling.
    - Sliders: Minimum edge weight slider + **Observed Interaction Evolution** time-range slider.
    - Deterministic categorical Louvain community palette (no numeric magnitude gradients).
    - Node Inspector with PageRank rank, betweenness rank, and derived interaction totals.
    - **Ego Network Mode:** Isolates 1-hop in/out neighborhood with one click and `BACK TO FULL NETWORK` toggle.
    - **Related Tweets:** Additive `GET /api/v1/tweets?user_id=X` query loading author's real posts.
    - Edge inspection popover showing interaction weights, types, and observation timestamps.
  - **Slide-Over Evidence / Provenance Drawer:** Exact formulas and model parameters for velocity, PageRank, betweenness, and sentiment.
  - **Guided Tour Modal:** 5-step interactive walkthrough (`INVESTIGATE TOP SIGNAL`) navigating real data.
  - **Compact Demographics Banner:** Replaced 4 empty cards with single elegant Phase 5 scheduled strip.

## Known limitations / open decisions
- **Real Graph Sparsity:** The current interaction graph is very sparse (density $\approx 0.0021$, largest WCC = 7 users), consisting primarily of isolated pairwise replies/mentions. Algorithms execute cleanly and deterministically, but community and bridge results reflect the initial bootstrap sample rather than rich, fully-formed real-world communities.
- **Sampling Bias from Collection Queries:** Collection queries directly shape the observed dataset. Discovering technology-heavy topics indicates narratives trending *within the observed sample*, not necessarily across all global X activity.
- **Sparse Temporal Distribution:** Historical tweets have temporal clustering (bursts during search scrapes), meaning early windows have sparse baselines. Real-world continuous streaming will populate more uniform 15-minute intervals.
- **Multilingual Limitation of all-MiniLM-L6-v2:** Trained primarily on English. Tokenization and embeddings degrade on Hindi/Devanagari text. Per §9/§24.6, preserved as approved MVP baseline; multilingual models (e.g. `paraphrase-multilingual-MiniLM-L12-v2`) logged for future evaluation.
- Emotion model not yet selected (PROJECT_CONTEXT.md §24.4b).
- Stance model not yet selected (§24.4c).
- MuRIL fallback remains DISABLED pending evaluation (§24.5).

## Next recommended step
Select and begin implementing the Emotion analysis model or Demographics (M3-Inference) pipeline per project plan.
