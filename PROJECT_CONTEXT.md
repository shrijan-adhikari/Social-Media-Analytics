# PROJECT_CONTEXT.md --- INTEL_SYNTHESIS

> **Read this file before doing any work in this repository.**
>
> This file is the canonical technical/product context for AI coding
> agents. Do not redesign the project from scratch unless explicitly
> asked. Inspect `CURRENT_STATE.md` and existing code before
> implementing anything.

## 0. Project Identity

-   **Project:** Social Media Analytics
-   **Team:** Adastra
-   **SIH Problem Statement:** SIH26152 --- Social Media Analytics
-   **Current implementation scope:** **X/Twitter only**
-   **Primary language:** Python
-   **Goal:** Build a jury-ready AI social intelligence system that
    analyzes X/Twitter conversations across sentiment, demographics,
    trends and interaction networks, then combines them to explain how
    narratives emerge and propagate.

## 1. Current Scope --- Important

### Implement now

-   X/Twitter collection
-   timeline/history management
-   normalized tweets/users/interactions
-   sentiment + emotion
-   sarcasm signal
-   demographic inference using **M3-Inference**
-   trend/topic detection
-   interaction graph
-   PageRank influence
-   Louvain communities
-   temporal narrative propagation
-   unified analyst dashboard

### Explicitly out of current scope

Do **not** implement Telegram, Instagram, Facebook, Reddit or YouTube
unless the user explicitly expands scope later.

Do not add multi-platform abstractions merely for theoretical future
support if they materially slow the Twitter MVP. Keep boundaries clean
enough that another collector could be added later.

## 2. Product Thesis

Do not build five disconnected dashboards.

All analysis is attached to the same Twitter users, tweets, topics and
timestamps:

``` text
X/Twitter
    ↓
twscrape
    ↓
Collection + Raw Preservation
    ↓
Normalization
    ↓
PostgreSQL
    ↓
┌────────────┬──────────────┬──────────────┬─────────────┐
│ Sentiment  │ Demographics │ Trends       │ Network     │
└────────────┴──────────────┴──────────────┴─────────────┘
                         ↓
               Cross-Vector Analysis
                         ↓
            Narrative Propagation Intelligence
                         ↓
                 Analyst Dashboard
```

The jury-facing differentiator is:

> **From Social Listening to Narrative Intelligence:** detect emerging
> narratives and reconstruct how they move through communities, how
> sentiment changes during diffusion, which aggregate audience segments
> participate, and which bridge/influence nodes accelerate the spread.

## 3. Twitter Data Acquisition --- twscrape

**Required library:** `twscrape`\
Repository: `https://github.com/vladkens/twscrape`

Use twscrape as the current Twitter collection adapter.

Relevant capabilities: - asynchronous Python API - Twitter/X search and
GraphQL endpoints - parsed models or raw responses - local
account/session persistence - rate-limit-aware account handling

### Collection responsibilities

Collect the fields needed for analytics, subject to what twscrape/X
currently exposes: - tweet ID - author/user ID - text - UTC timestamp -
reply relationship - repost/retweet relationship - quote relationship -
mentions - engagement counts - hashtags/entities when available - public
user/profile fields needed by M3 and analysis - raw response/payload or
a recoverable raw representation where practical

### Engineering rule

All twscrape-specific code belongs inside `collectors/twitter/`.

Analytics modules must consume our normalized domain models, **not
twscrape objects directly**.

### Session database

twscrape may use SQLite internally for its account/session state. That
SQLite file is **not** the project's analytics database.

Never commit: - account cookies - auth tokens - session secrets - proxy
credentials - collector SQLite files containing credentials/session
state

## 4. Canonical Database --- PostgreSQL

Use **PostgreSQL** as the application database.

Use: - SQLAlchemy - Alembic migrations - PostgreSQL indexes - `pgvector`
only if/when semantic vector storage is required

SQLite is permitted only for twscrape/session/cache/local testing.

### Core tables

#### `users`

Suggested fields: - `id` - `twitter_user_id` UNIQUE - `username` -
`display_name` - `bio` - `profile_image_url` - `declared_location` -
`followers_count` - `following_count` - `created_at` - `last_seen_at` -
optional raw/profile metadata

#### `tweets`

-   `id`
-   `twitter_tweet_id` UNIQUE
-   `author_id` FK
-   `text`
-   `created_at_utc`
-   `conversation_id`
-   `reply_to_tweet_id`
-   `reply_to_user_id`
-   `repost_of_tweet_id`
-   `quoted_tweet_id`
-   engagement counts
-   raw payload/reference
-   ingestion timestamp

#### `interactions`

Persistent graph edge/event: - `source_user_id` - `target_user_id` -
`tweet_id` - `interaction_type` - `timestamp_utc` - `weight`

Supported types initially: - reply - repost - quote - mention

#### `sentiment_results`

-   `tweet_id`
-   base sentiment
-   adjusted/final sentiment
-   emotion
-   sarcasm probability
-   confidence
-   model name/version
-   analyzed_at

#### `demographic_estimates`

-   `user_id`
-   M3 age probability distribution
-   M3 gender probability distribution
-   M3 organization probability distribution
-   detected language
-   confidence/coverage metadata
-   model/version
-   inferred_at

#### `topics`

-   `id`
-   label
-   representative terms
-   centroid/embedding if stored
-   created_at

#### `tweet_topics`

-   `tweet_id`
-   `topic_id`
-   similarity/confidence

#### `trend_windows`

-   `topic_id`
-   `window_start`
-   `window_end`
-   mention_count
-   velocity
-   acceleration
-   engagement metrics
-   community-spread metrics when available

## 5. Demographics --- M3-Inference Is the Primary Model

**Required project:** `euagendas/m3inference`\
Repository: `https://github.com/euagendas/m3inference`

Do not substitute another demographic model without explicit approval.

M3 is the project's primary demographic inference engine.

### What M3 predicts

Use its probability outputs for: - **age:** `<=18`, `19-29`, `30-39`,
`>=40` - **gender:** female / male - **account type:** organization /
non-organization

Do not invent finer age buckets from M3 output.

### M3 inputs

Prepare M3-compatible input from collected Twitter profiles: - `id` -
`name` - `screen_name` - `description` - `lang` - `img_path` when full
multimodal inference is used

M3 can use profile image + text/profile signals. The repository also
exposes a text-only mode (`use_full_model=False`) when images are
unavailable.

### Integration design

``` text
twscrape User
     ↓
User/Profile Normalizer
     ↓
M3 Input Adapter
     ├── name
     ├── screen_name
     ├── description
     ├── language
     └── profile image (when available)
     ↓
M3Inference
     ↓
Probability distributions
     ↓
demographic_estimates
     ↓
Aggregate dashboard
```

### Critical demographic rules

-   Store **probabilities**, not only argmax labels.
-   Present results as inferred/estimated, not verified identity.
-   Jury/dashboard reporting should be aggregate wherever possible.
-   Keep organization accounts separable from human-audience demographic
    summaries.
-   If confidence/inputs are inadequate, classify as `unclassified`
    rather than inventing a result.
-   Do not claim M3 predicts profession, interests, geography or
    language demographics. Those require separate signals/modules.
-   Treat language detection and declared location as separate metadata,
    not M3 outputs.

### Compatibility warning

M3 is an older research implementation. Isolate it behind
`analytics/demographics/m3_service.py` or a similar adapter so
dependency/version issues do not contaminate the rest of the backend.

If its dependencies conflict with the main application, prefer a
separate environment/container/service for M3 rather than rewriting the
entire backend around its dependency versions.

## 6. Sentiment / Emotion / Sarcasm

Pipeline:

``` text
Tweet text
   ↓
Text preprocessing
   ↓
Multilingual sentiment
   ↓
Emotion
   ↓
Sarcasm classifier
   ↓
Confidence-aware fusion
   ↓
sentiment_results
```

Current model direction: - XLM-RoBERTa family for multilingual
sentiment - dedicated T5 Twitter sarcasm classifier - MuRIL
experimentation only where useful for Indian/code-mixed text

Do not automatically invert every positive result when sarcasm is
detected. Preserve: - base sentiment - sarcasm probability -
final/adjusted interpretation - confidence

This keeps the system explainable.

## 7. Trend & Narrative Detection

### Layer A --- lexical/hashtag velocity

-   preprocess with spaCy
-   extract useful keywords/entities/hashtags
-   bucket tweets into 15-minute windows
-   compute mention frequency
-   compare against baseline
-   calculate velocity and acceleration

Initial metric:

`velocity = mentions_current_window / average_mentions_baseline`

### Layer B --- semantic topic discovery

Initial stack: - Sentence Transformers: `all-MiniLM-L6-v2` - HDBSCAN -
TF-IDF / representative phrases for topic naming

Goal: group semantically equivalent tweets even when they do not share
the same hashtag.

### Optional Narrative Emergence Score

Do not implement until basic trend detection works.

`NES = αV + βA + γE + δC + εB`

Where: - V = velocity - A = acceleration - E = engagement growth - C =
community adoption - B = bridge/cross-community activity

Weights must be configurable and must not be presented as scientifically
validated until evaluated.

## 8. Network / Link Analysis

Build the graph from **interactions**, not follower count.

``` text
Twitter interaction records
        ↓
PostgreSQL interactions table
        ↓
NetworkX directed weighted graph
        ↓
PageRank + Louvain + bridge metrics
        ↓
Temporal topic subgraphs
```

### Direction

Represent information/interaction flow consistently and document the
convention in code/tests.

### Algorithms

-   Weighted PageRank → interaction influence
-   Louvain → community detection
-   Betweenness/bridge metrics → brokers between communities
-   temporal snapshots → propagation

Follower count may be displayed as context but is not the primary
influence metric.

### Narrative-specific graph

For selected topic: 1. obtain tweets assigned to topic 2. obtain
relevant interactions 3. sort by timestamp 4. create time-window
snapshots 5. find earliest observed participants 6. find amplifiers 7.
detect community crossover 8. identify bridge users 9. correlate
crossover with velocity/sentiment changes

Use **"first observed in collected data"**, not "true origin".

## 9. Cross-Vector Intelligence --- Core Jury Feature

Every selected narrative should support:

``` text
Narrative
 ├── Timeline
 ├── Velocity
 ├── Sentiment / emotion transition
 ├── M3 aggregate demographic distribution
 ├── Communities
 ├── Influential accounts
 ├── Bridge accounts
 └── Propagation timeline
```

Examples of useful questions: - Which community adopted the narrative
immediately before acceleration? - Did sentiment change after a
high-PageRank account amplified it? - What M3 age distribution is
observed among classified human accounts participating in this topic? -
Which account connected otherwise separated communities? - Was observed
spread primarily influencer-driven, grassroots or bridge-driven?

Do not imply causation when the data only supports temporal association.

## 10. Frontend --- Preserve the Existing Visual Direction

Use the supplied UI screenshots as the target design. Do not redesign
the application into a generic admin dashboard.

### Visual identity

-   dark intelligence/analyst console
-   near-black background
-   restrained bright green accent
-   thin borders
-   dense but readable information
-   monospace metadata/details
-   strong section titles
-   confidence/provenance visible
-   limited animation

### Main navigation

1.  Overview
2.  Demographics
3.  Sentiment
4.  Trends
5.  Network

No platform switcher is required while the product is Twitter-only.

### Overview

Preserve the screenshot concept: - total tweets/posts - engagement - net
sentiment - active threads/conversations - sentiment over time -
trending now - audience snapshot - recent analysis activity -
affinity/community clusters - engagement activity

### Demographics

Preserve the supplied layout but map it to **actual M3 outputs**: - M3
age distribution (`<=18`, `19-29`, `30-39`, `>=40`) - gender
distribution for classified human accounts - human vs organization
distribution - language distribution as a separate detector/metadata
signal - location only from disclosed/geocoded metadata, clearly
labeled - demographics-over-time when sample size permits - model
coverage/confidence

Do not show unsupported fabricated categories just because the mockup
contains them.

### Sentiment

Preserve: - positive / negative / neutral - sarcasm probability -
sentiment-over-time - emotion vector - anomaly/sarcasm log

### Trends

Preserve: - top rising topics - mentions - velocity - change - selected
trend details - timeline heatmap - cross-vector insights

### Network

Preserve: - large interactive graph - community legend - PageRank-sized
nodes - selected-user panel - rank/PageRank - interaction counts -
community affiliation - generated system insight - propagation timeline

### Critical UI behavior

Selecting a trend should synchronize: - trend detail - sentiment -
demographics - network - propagation timeline

This interaction is more valuable than adding many extra pages.

## 11. Recommended Application Architecture

``` text
Browser
  ↓
Next.js / React frontend
  ↓ HTTPS
FastAPI backend
  ├── Twitter collection service
  ├── analytics orchestration
  ├── sentiment service
  ├── M3 demographic service
  ├── trend service
  └── network service
  ↓
PostgreSQL
```

For long jobs, use background workers/processes rather than blocking API
requests.

### Deployment

**Decision (locked):** plain managed PostgreSQL, **not** Supabase.
Supabase is a Postgres-as-a-service wrapper with extra tooling
(auth, auto-generated APIs, dashboard UI) that this project does not
use. Reach the database only via SQLAlchemy + Alembic, as already
specified in §4. Do not introduce Supabase's client SDK or
Supabase-specific features (row-level security policies, Supabase
Auth, PostgREST) anywhere in the codebase.

Suitable hosting options for the managed PostgreSQL instance: Railway,
Render, Neon, or a self-managed instance on the same VM/container as
the backend for the hackathon demo. Pick one and record it in an ADR
under `docs/decisions/` once chosen — do not leave it implicit.

-   frontend → Vercel
-   FastAPI / ML / collector → persistent container/VM service
-   PostgreSQL → managed PostgreSQL (plain Postgres, not Supabase)
-   M3 → same backend only if dependencies work cleanly; otherwise
    isolated worker/container

Do not attempt to run the complete transformer + M3 + continuous
twscrape workload as Vercel serverless functions.

## 12. Recommended Repository Layout

``` text
Social Media Analytics/
├── AGENTS.md
├── PROJECT_CONTEXT.md
├── CURRENT_STATE.md
├── README.md
├── .env.example
│
├── frontend/
│   └── web/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   ├── schemas/
│   │   └── services/
│   └── migrations/
│
├── collectors/
│   └── twitter/
│       ├── client.py
│       ├── normalizer.py
│       └── repository.py
│
├── analytics/
│   ├── sentiment/
│   ├── demographics/
│   │   ├── m3_adapter.py
│   │   └── service.py
│   ├── trends/
│   └── network/
│
├── workers/
├── tests/
├── scripts/
├── docs/
│   ├── architecture/
│   ├── decisions/
│   └── research/
└── requirements/
    ├── requirements.txt
    └── requirements-dev.txt
```

Adapt this to existing code rather than moving working files
unnecessarily.

## 13. Implementation Order

Agents should prefer this order unless `CURRENT_STATE.md` says
otherwise:

### Phase 1 --- Twitter foundation

1.  environment/config/secrets
2.  PostgreSQL + SQLAlchemy
3.  Alembic migrations
4.  users/tweets/interactions schema
5.  twscrape client wrapper
6.  tweet/user normalization
7.  persistence
8.  small reproducible Twitter dataset

### Phase 2 --- independent analytics

9.  sentiment pipeline
10. sarcasm pipeline
11. M3 adapter + inference
12. lexical trend velocity
13. semantic clustering
14. NetworkX graph construction
15. PageRank
16. Louvain

### Phase 3 --- integration

17. topic↔tweet mapping
18. topic-specific sentiment
19. topic-specific M3 demographic aggregation
20. topic-specific graph
21. temporal propagation
22. bridge detection
23. cross-vector API

### Phase 4 --- frontend

24. Overview
25. Demographics
26. Sentiment
27. Trends
28. Network
29. synchronized trend selection
30. propagation narrative

### Phase 5 --- jury readiness

31. confidence/provenance
32. model/version display where useful
33. error/loading states
34. evaluation
35. stable demo dataset
36. optional live collection
37. scripted demo

## 14. API Direction

Suggested endpoints; adapt to implementation rather than duplicating
existing routes:

``` text
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

## 15. Jury Demo Story

Do not demo the system as unrelated pages.

Use one Twitter narrative:

1.  **Overview:** rising narrative appears.
2.  **Trends:** show velocity/heatmap.
3.  **Sentiment:** show reaction and emotional change.
4.  **Demographics:** show M3 aggregate distribution and classification
    coverage.
5.  **Network:** show communities, PageRank and bridge account.
6.  **Propagation:** replay first observation → community crossover →
    acceleration.
7.  **Cross-vector conclusion:** explain what changed and when.

Target takeaway:

> **"Social Media Analytics does not only count Twitter mentions. It
> reconstructs the observed lifecycle of an emerging narrative across
> time, audience reaction and interaction communities."**

## 16. Evaluation Rules

Do not invent accuracy numbers.

Track: - sentiment macro-F1 / precision / recall on an evaluation
sample - English vs Hinglish/code-mixed performance where relevant -
sarcasm metrics - M3 classification coverage and probability
distributions - trend precision@K/manual validation - topic-cluster
quality - community modularity - processing latency - API/dashboard
latency

M3's published/repository claims may be cited as external model
background, but they are **not equivalent to measured accuracy on our
collected dataset**.

## 17. Privacy / Ethics / Claims

-   Use appropriately accessible Twitter data.
-   Never commit account credentials/cookies.
-   Report demographics as estimates.
-   Prefer aggregate demographic views.
-   Separate organizations from human demographic aggregates.
-   Allow `unclassified`.
-   Preserve model/version/probability where practical.
-   Distinguish declared location from inferred information.
-   Distinguish observed propagation from real-world causality.
-   Say "first observed in our dataset", not "originated here".
-   Do not make unsupported misinformation/bot/coordination claims.

## 18. Instructions for Every AI Coding Agent

### Before coding

1.  Read this file completely.
2.  Read `CURRENT_STATE.md`.
3.  Inspect the repository tree.
4.  Inspect relevant existing code/tests.
5.  Determine the smallest change required for the requested task.

### While coding

6.  **Do not change project scope. Twitter only.**
7.  **Use twscrape for Twitter acquisition.**
8.  **Use M3-Inference for primary demographic inference.**
9.  **Use PostgreSQL as canonical application DB.**
10. Do not replace agreed technologies merely because another library is
    familiar.
11. Do not introduce Kafka, Neo4j, Redis, MongoDB or another DB unless
    explicitly justified/approved.
12. Keep twscrape behind a collector adapter.
13. Keep M3 behind a demographic adapter/service.
14. Keep ML code separate from HTTP route handlers.
15. Keep graph computation separate from persistence.
16. Use UTC internally.
17. Preserve raw IDs and relationships required for graph
    reconstruction.
18. Make analytics reproducible and testable.
19. Do not hardcode fake dashboard data into production paths.
20. Do not fabricate benchmark/accuracy claims.

### Before finishing a task

21. Run relevant tests/lint/type checks available in the repo.
22. State what files changed.
23. State what was tested.
24. State unresolved limitations.
25. Update `CURRENT_STATE.md` after a substantial milestone.
26. If an architectural decision changed, create/update an ADR under
    `docs/decisions/`.

## 19. Agent Decision Policy

When requirements are ambiguous:

1.  Preserve working code.
2.  Preserve this architecture.
3.  Choose the simplest reversible implementation.
4.  Avoid unnecessary dependencies.
5.  Prefer a working end-to-end vertical slice over premature scale.
6.  Ask the user only when the decision is expensive, irreversible or
    changes product behavior substantially.

When documentation conflicts: 1. explicit latest user instruction 2.
`CURRENT_STATE.md` 3. this `PROJECT_CONTEXT.md` 4. ADRs 5. README/older
documents

Flag contradictions instead of silently guessing.

## 20. Current Fixed Technology Choices

  Area                 Choice
  -------------------- ----------------------------------------------------
  Source               X/Twitter only
  Collection           twscrape
  Main DB              PostgreSQL
  ORM                  SQLAlchemy
  Migrations           Alembic
  Backend              FastAPI / Python
  Demographics         M3-Inference
  Sentiment            XLM-R family
  Sarcasm              dedicated classifier
  Embeddings           Sentence Transformers
  Topic clustering     HDBSCAN
  Graph engine         NetworkX
  Influence            weighted PageRank
  Communities          Louvain
  Frontend target      Next.js / React / TypeScript
  Frontend hosting     Vercel
  ML/backend hosting   persistent container/VM
  Project context      this file + CURRENT_STATE.md + ADRs + Git

## 21. Non-Goals Right Now

Do not implement: - Telegram - Reddit - YouTube - Instagram/Facebook -
Neo4j - Kafka - custom vector DB - foundation-model training -
individual-level demographic certainty - large distributed
architecture - causal inference

## 22. Definition of a Good Contribution

A good agent contribution: - moves one vertical feature closer to
working end-to-end - respects existing architecture - uses real
normalized Twitter data - persists outputs rather than only printing
them - includes tests where practical - exposes confidence/provenance -
avoids unnecessary rewrites - leaves the next agent clear context in
`CURRENT_STATE.md`

## 23. Final Product Position

**Social Media Analytics is currently a Twitter-focused narrative intelligence
system.**

Its value is not that it independently contains sentiment, demographics,
trends and graph analysis. Its value is that these signals are joined
chronologically around the same narrative to explain:

**what is rising → who is participating → how they react → who amplifies
it → which communities it crosses → how the narrative changes as it
spreads.**

## 24. Model Registry --- Final Decisions

This section is authoritative for model selection. AI agents MUST NOT
silently replace a primary model. Any replacement requires a controlled
comparison and user approval.

### 24.1 Sentiment --- Primary Model

**Primary model:** `cardiffnlp/twitter-xlm-roberta-base-sentiment`\
**Repository:**
`https://huggingface.co/cardiffnlp/twitter-xlm-roberta-base-sentiment`\
**Status:** `PRIMARY / APPROVED`\
**Fine-tuning by this project:** `NO` for MVP\
**Task:** Twitter text → Positive / Neutral / Negative probabilities

#### Why this model

Do NOT use `FacebookAI/xlm-roberta-base` directly as the production
sentiment classifier. It is a general multilingual pretrained backbone,
not a Positive/Neutral/Negative Twitter sentiment checkpoint.

The CardiffNLP checkpoint is preferred because it is XLM-R-based,
Twitter-domain adapted, already fine-tuned for sentiment, and suitable
as the initial multilingual Twitter baseline.

#### Sentiment alternative

**Candidate:**
`cardiffnlp/twitter-xlm-roberta-base-sentiment-multilingual`\
**Repository:**
`https://huggingface.co/cardiffnlp/twitter-xlm-roberta-base-sentiment-multilingual`\
**Status:** `EVALUATION CANDIDATE`\
**Fine-tuning by this project:** `NO`

Do not automatically replace the primary checkpoint. Benchmark both on
the same manually reviewed local evaluation set, especially
English/Hindi/Hinglish samples, before proposing a switch.

#### Base backbone reference

**Backbone:** `FacebookAI/xlm-roberta-base`\
**Repository:** `https://huggingface.co/FacebookAI/xlm-roberta-base`\
**Status:** `REFERENCE / BACKBONE ONLY`

Agents MUST NOT treat the raw backbone as a ready sentiment classifier.

### 24.2 Sentiment Preprocessing

Normalize Twitter-specific tokens consistently for inference:

-   replace `@mentions` with `@user`
-   replace URLs with `http`
-   preserve hashtags where useful
-   preserve emojis
-   preserve negations
-   preserve Hindi/Hinglish/transliterated text
-   do not aggressively strip punctuation
-   do not stem or lemmatize before transformer inference
-   always store original tweet text unchanged

Example:

``` text
Original:
@rahul this policy is amazing 😂 https://example.com

Inference text:
@user this policy is amazing 😂 http
```

### 24.3 Sentiment Output Contract

Persist probabilities and provenance, not only the winning label:

``` text
tweet_id
model_id
model_revision
negative_probability
neutral_probability
positive_probability
base_sentiment
base_confidence
sarcasm_probability
final_sentiment
final_confidence
pipeline_version
analyzed_at
```

Example:

``` text
negative_probability = 0.81
neutral_probability  = 0.14
positive_probability = 0.05
base_sentiment       = "negative"
base_confidence      = 0.81
```

### 24.4 Sarcasm --- Primary Model

**Primary model:** `mrm8488/t5-base-finetuned-sarcasm-twitter`\
**Repository:**
`https://huggingface.co/mrm8488/t5-base-finetuned-sarcasm-twitter`\
**Status:** `PRIMARY / APPROVED`\
**Fine-tuning by this project:** `NO` for MVP

Purpose:

``` text
Tweet
  ↓
Sarcasm classifier
  ↓
SARCASM / NOT_SARCASM
  +
confidence/probability
```

The model is already fine-tuned for Twitter sarcasm. External model-card
metrics are background evidence only and MUST NOT be reported as
accuracy on this project's dataset.

#### Sarcasm fusion rule

Sarcasm does NOT automatically mean:

``` text
positive → negative
```

Preserve: - base sentiment - sarcasm probability/confidence - final
interpretation - fusion/pipeline version

The fusion algorithm must be separately versioned and testable.

### 24.4b Emotion --- Status Pending Selection

**Status:** `NOT YET SELECTED`

`sentiment_results.emotion` and the "Emotion" pipeline stage referenced
in §0 and §6 currently have **no approved model**. Agents MUST NOT
silently pick an emotion model to fill this gap.

Before implementing emotion classification:

1.  Propose 1--2 candidate checkpoints (e.g. a GoEmotions-trained
    multilingual classifier) with repository links.
2.  Confirm label taxonomy (e.g. anxiety, excitement, anger, joy) maps
    to what the problem statement asks for.
3.  Record the candidate under
    `docs/research/model-experiments/EXP-00X-emotion.md` per §24.9.
4.  Get user approval before marking it `PRIMARY / APPROVED`.

Until approved, leave `emotion` as `NULL`/`unclassified` in
`sentiment_results` rather than inventing a label.

### 24.4c Stance Detection ("Supportive" / "Against") --- Status Pending Selection

**Status:** `NOT YET SELECTED`

The problem statement explicitly requires detecting whether a post is
supportive of or against a topic/narrative (stance), which is distinct
from positive/negative/neutral polarity. No model is currently
registered for this.

Do not repurpose the sentiment model's positive/negative output as a
stance proxy without recording that decision explicitly in an ADR ---
polarity and stance frequently diverge (e.g. a negative-polarity post
can still be "supportive" of a cause by criticizing its opponents).

Follow the same candidate → experiment-log → approval flow as §24.4b
before implementation.

### 24.5 Hinglish / Indian-Language Fallback --- MuRIL

**Backbone:** `google/muril-base-cased`\
**Repository:** `https://huggingface.co/google/muril-base-cased`\
**Status:** `EXPERIMENTAL / DISABLED BY DEFAULT`

MuRIL is a pretrained representation model for Indian languages and
transliterated text. It is NOT automatically a sentiment or sarcasm
classifier.

Agents MUST NOT implement:

``` text
MuRIL(tweet) → sentiment
```

unless a task-specific checkpoint has been selected/fine-tuned and
evaluated.

#### When MuRIL may be enabled

Only if evaluation demonstrates a meaningful failure of the primary
pipeline on Hindi/Hinglish/code-mixed tweets:

``` text
MuRIL
  ↓
task-specific fine-tuning
  ↓
controlled evaluation
  ↓
comparison with primary models
  ↓
enable only if measured improvement exists
```

Until then:

``` text
MuRIL fallback = DISABLED
```

No automatic fallback model is approved for sentiment/sarcasm.
Low-confidence cases should retain uncertainty rather than silently
routing to an unvalidated model.

### 24.6 Semantic Embeddings --- Primary Model

**Primary model:** `sentence-transformers/all-MiniLM-L6-v2`\
**Repository:**
`https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2`\
**Status:** `PRIMARY / APPROVED`\
**Fine-tuning by this project:** `NO` for MVP

Purpose:

``` text
Tweet text
   ↓
all-MiniLM-L6-v2
   ↓
dense embedding
   ↓
HDBSCAN
   ↓
semantic topic cluster
   ↓
TF-IDF / representative terms
   ↓
topic label
```

This model is for semantic similarity/topic discovery, NOT sentiment.

No embedding fallback is approved initially. If multilingual/Hinglish
clustering quality is poor, benchmark a multilingual
sentence-transformer before changing the primary model.

### 24.7 Demographics --- M3-Inference

**Primary project:** `euagendas/m3inference`\
**Repository:** `https://github.com/euagendas/m3inference`\
**Status:** `PRIMARY / APPROVED`\
**Fine-tuning by this project:** `NO` for MVP

M3 outputs probability distributions for: - age: `<=18`, `19-29`,
`30-39`, `>=40` - gender: female / male - account type: organization /
non-organization

Do NOT invent additional M3 output categories.

#### M3 routing/fallback

``` text
Twitter profile
      ↓
Full multimodal M3
(text/profile + image)
      ↓ if image unavailable
M3 text-only mode
      ↓ if inputs/results are inadequate
UNCLASSIFIED
```

Do not automatically substitute another demographic model.

Store probability distributions, model/version and coverage metadata.
Keep organization accounts separable from human demographic aggregates.

### 24.8 Final Model Registry

  --------------------------------------------------------------------------------------------------------------------
  Component         Primary model/project                                          Status            Project
                                                                                                     fine-tuning
  ----------------- -------------------------------------------------------------- ----------------- -----------------
  Sentiment         `cardiffnlp/twitter-xlm-roberta-base-sentiment`                PRIMARY /         No
                                                                                   APPROVED          

  Sentiment         `cardiffnlp/twitter-xlm-roberta-base-sentiment-multilingual`   EVALUATE          No
  alternative                                                                                        

  XLM-R backbone    `FacebookAI/xlm-roberta-base`                                  REFERENCE ONLY    N/A

  Sarcasm           `mrm8488/t5-base-finetuned-sarcasm-twitter`                    PRIMARY /         No
                                                                                   APPROVED          

  Indian-language   `google/muril-base-cased`                                      DISABLED /        Required before
  backbone                                                                         EXPERIMENTAL      task-specific use

  Demographics      `euagendas/m3inference`                                        PRIMARY /         No
                                                                                   APPROVED          

  Emotion           not yet selected --- see \S24.4b                              NOT SELECTED      TBD

  Stance            not yet selected --- see \S24.4c                              NOT SELECTED      TBD

  Embeddings        `sentence-transformers/all-MiniLM-L6-v2`                       PRIMARY /         No
                                                                                   APPROVED          

  Topic clustering  HDBSCAN                                                        PRIMARY /         N/A
                                                                                   APPROVED          

  Influence         Weighted PageRank / NetworkX                                   PRIMARY /         N/A
                                                                                   APPROVED          

  Communities       Louvain                                                        PRIMARY /         N/A
                                                                                   APPROVED          
  --------------------------------------------------------------------------------------------------------------------

### 24.9 Fine-Tuning Policy

For the initial MVP:

``` text
Sentiment → NO project fine-tuning
Sarcasm   → NO project fine-tuning
M3        → NO project fine-tuning
MiniLM    → NO project fine-tuning
MuRIL     → DISABLED
```

First build the complete end-to-end pipeline using approved existing
checkpoints.

Only consider fine-tuning after evaluating the baseline on
representative collected Twitter data.

If fine-tuning becomes necessary, create:

``` text
docs/research/model-experiments/
    EXP-001-<model>.md
```

Every experiment MUST record:

``` text
base model
model repository
dataset
dataset source/license
number of examples
label distribution
languages
train/validation/test split
preprocessing
hyperparameters
random seed
precision
recall
macro-F1
accuracy where appropriate
confusion matrix
inference latency
memory/compute notes
saved checkpoint/version
limitations
```

Never state that a locally fine-tuned model is better unless the
controlled evaluation supports that claim.

### 24.10 Model Selection Rules for AI Agents

If an agent finds a potentially better model:

1.  Do not silently replace the current primary.
2.  Record the candidate and repository.
3.  Explain the expected advantage.
4.  Benchmark both models on the same local evaluation set.
5.  Compare quality, latency and memory use.
6.  Record the experiment under `docs/research/model-experiments/`.
7.  Recommend a replacement only after evidence exists.
8.  User approval is required before changing `PRIMARY / APPROVED`.

### 24.11 Model Provenance in PostgreSQL

Where practical, analytical result tables should preserve:

``` text
model_id
model_revision_or_version
pipeline_version
inference_timestamp
confidence/probabilities
fallback_used
fallback_reason
```

This is required for reproducibility, debugging and jury-facing
explainability.

## 25. Model-Aware Agent Checklist

Before implementing any ML component, the agent must answer internally:

1.  Is the exact approved repository/checkpoint listed above?
2.  Is this checkpoint already fine-tuned for the intended task?
3.  What preprocessing does its model card expect?
4.  What labels/probabilities does it actually output?
5.  Is a fallback explicitly approved?
6.  Are model/version/confidence being persisted?
7.  Is the implementation claiming project accuracy without local
    evaluation?

If any answer is unclear, inspect the model documentation or ask before
inventing behavior.
