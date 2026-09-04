# INTEL_SYNTHESIS — Social Media Narrative Intelligence Platform

> **SIH26152 — Social Media Analytics** | **Team Adastra**  
> An open-source, jury-ready AI intelligence workstation that ingests X/Twitter conversations, normalizes interaction networks, detects emerging semantic narratives, classifies nuanced sentiment with confidence-aware sarcasm fusion, and maps community influence topologies.

---

## 📑 Table of Contents
1. [What This Project Can Do](#-what-this-project-can-do)
2. [System Architecture](#-system-architecture)
3. [Full Tutorial: How to Use It](#-full-tutorial-how-to-use-it)
   - [Prerequisites](#1-prerequisites)
   - [Step 1: Clone & Configure Environment](#step-1-clone--configure-environment)
   - [Step 2: Start PostgreSQL with Docker](#step-2-start-postgresql-with-docker)
   - [Step 3: Setup Twitter / Session Cookies](#step-3-setup-twitter--session-cookies-vital)
   - [Step 4: Install Dependencies & Run Migrations](#step-4-install-dependencies--run-migrations)
   - [Step 5: Ingest Twitter Data](#step-5-ingest-twitter-data)
   - [Step 6: Run Analytics Pipeline](#step-6-run-analytics-pipeline)
   - [Step 7: Launch Backend & Frontend](#step-7-launch-backend--frontend)
   - [Step 8: Run Tests](#step-8-run-tests)
4. [Models, Methods & Engineering Rationale (Why Each Was Chosen)](#-models-methods--engineering-rationale)
5. [Visual Workflow & Algorithmic Flowcharts](#-visual-workflow--algorithmic-flowcharts)
6. [API Endpoints Overview](#-api-endpoints-overview)
7. [Repository Structure](#-repository-structure)

---

## 🎯 What This Project Can Do

Traditional social listening tools merely count keywords, hashtags, and follower numbers. **INTEL_SYNTHESIS** moves from surface-level keyword counting to **Narrative Propagation Intelligence**:

```
Keyword Volume (Social Listening)  ──►  WHO, WHERE, WHY & HOW FAST (Narrative Intelligence)
```

### Core Capabilities:
- 🔄 **Autonomous Twitter Ingestion**: Collects targeted tweets, replies, quotes, reposts, and author profiles without enterprise API paywalls using session pooling.
- 💬 **Multilingual Sentiment & Sarcasm Fusion**: Classifies sentiment across 100+ languages and pairs it with a dedicated sarcasm transformer. It avoids naive sentiment flipping through a 4-state confidence-aware fusion matrix (`NO_SARCASM`, `SARCASM_CONSISTENT`, `SARCASM_AMBIGUOUS`, `SARCASM_UNCERTAIN`).
- 📈 **Semantic Trend Discovery & Velocity Tracking**: Groups semantically similar tweets (even with differing hashtags) via dense vector embeddings and density clustering. Evaluates real-time 15-minute velocity and acceleration against a 2-hour baseline.
- 🕸️ **Network Influence & Echo Chamber Detection**: Reconstructs directed conversational gravity graphs (source $\to$ target). Computes **Weighted PageRank** for true interaction influence, **Louvain Modularity** for organic community detection, and **Betweenness Centrality** to pinpoint critical narrative bridge accounts connecting polarized communities.
- 🖥️ **Interactive Intelligence Workstation**: High-density Next.js analyst console with Cytoscape.js graph exploration, ego-network filtering, stacked sentiment timelines, and real-time narrative synchronization.

---

## 🏗️ System Architecture

```mermaid
flowchart TD
    subgraph S1["1. Acquisition Layer"]
        X["X / Twitter Web GraphQL"] -->|Session Cookies & Account Pool| TWS["twscrape Collector"]
        TWS -->|Raw Payloads| NORM["Data Normalizer"]
    end

    subgraph S2["2. Relational Storage Layer"]
        NORM -->|ACID Ingestion| PG[("PostgreSQL 17\nUsers • Tweets • Interactions")]
    end

    subgraph S3["3. Multi-Vector Analytics Engines"]
        PG -->|Tweet Text| SA["CardiffNLP XLM-RoBERTa\n(Multilingual Sentiment)"]
        PG -->|Tweet Text| SC["T5 Twitter Sarcasm Model\n+ Confidence Fusion"]
        PG -->|Tweet Text| EMB["all-MiniLM-L6-v2 Embeddings\n+ HDBSCAN Clustering"]
        PG -->|Interactions| NET["NetworkX Interaction Graph\n(PageRank • Louvain • Betweenness)"]
        PG -.->|Profiles (Phase 5)| M3["M3-Inference\n(Multimodal Demographics)"]
    end

    subgraph S4["4. Analytical Storage"]
        SA & SC --> RES_S[("sentiment_results")]
        EMB --> RES_T[("topics & trend_windows")]
        NET --> RES_N[("network_nodes, edges & flows")]
        M3 -.-> RES_D[("demographic_estimates")]
    end

    subgraph S5["5. Intelligence Delivery"]
        RES_S & RES_T & RES_N & RES_D --> API["FastAPI Backend (/api/v1/*)\nO(1) Precomputed Reads"]
        API --> UI["Next.js 14 Analyst Workstation\n(Cytoscape.js • Recharts • Dark UI)"]
    end
```

---

## 🚀 Full Tutorial: How to Use It

Follow this step-by-step guide to run the complete system locally.

### 1. Prerequisites
- **Docker Desktop** (running on Windows, macOS, or Linux)
- **Python 3.11+**
- **Node.js 18+** & **npm**

---

### Step 1: Clone & Configure Environment

1. Clone the repository and navigate to the project root:
   ```bash
   git clone https://github.com/shrijan-adhikari/Social-Media-Analytics.git
   cd "social media analysis"
   ```

2. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

3. Open `.env` and verify database settings:
   ```env
   APP_ENV=development
   POSTGRES_DB=social_media_analytics
   POSTGRES_USER=social_media_app
   POSTGRES_PASSWORD=your_secure_password_here

   # Use 127.0.0.1 on Windows to prevent IPv6 localhost connection delays
   DATABASE_URL=postgresql+psycopg://social_media_app:your_secure_password_here@127.0.0.1:5432/social_media_analytics
   ```

---

### Step 2: Start PostgreSQL with Docker

Start PostgreSQL 17 in detached mode using Docker Compose:
```bash
docker compose up -d
```
*Verify that the container is healthy:*
```bash
docker ps
```
You should see `social-media-postgres` listening on `127.0.0.1:5432` with status `(healthy)`.

---

### Step 3: Setup Twitter / Session Cookies (Vital)

`twscrape` connects directly to Twitter's backend GraphQL endpoints. Twitter enforces strict Cloudflare/bot checks on automated logins. Providing **browser session cookies** is the most reliable method.

#### How to extract your session cookies:
```mermaid
sequenceDiagram
    autonumber
    actor User as Analyst / User
    participant Browser as Web Browser (Chrome / Edge / Firefox)
    participant DevTools as DevTools (F12)
    participant Env as .env File

    User->>Browser: Log in to https://x.com
    User->>DevTools: Press F12 -> Go to "Application" / "Storage" tab
    DevTools->>DevTools: Expand "Cookies" -> Click "https://x.com"
    DevTools-->>User: Copy value of "auth_token" (hex string)
    DevTools-->>User: Copy value of "ct0" (CSRF token)
    User->>Env: Set TWITTER_COOKIES="auth_token=...; ct0=..."
```

1. Open your browser and log into [x.com](https://x.com).
2. Press `F12` (or right-click $\to$ **Inspect**) to open Developer Tools.
3. Click on the **Application** tab (in Chrome/Edge) or **Storage** tab (in Firefox).
4. In the left sidebar, expand **Cookies** and select `https://x.com`.
5. Find and copy the values for:
   - `auth_token` (e.g. `4f8c9...`)
   - `ct0` (e.g. `1a2b3...`)
6. Update `.env` with your username and cookies:
   ```env
   TWITTER_USERNAME=your_x_handle
   TWITTER_COOKIES="auth_token=YOUR_AUTH_TOKEN_VALUE; ct0=YOUR_CT0_VALUE"
   ```

---

### Step 4: Install Dependencies & Run Migrations

1. Activate your Python virtual environment (e.g., in `.venv`):
   ```bash
   # Windows PowerShell:
   .\.venv\Scripts\Activate.ps1
   # Linux / macOS:
   source .venv/bin/activate
   ```

2. Install backend dependencies in editable mode:
   ```bash
   cd backend
   pip install -e ".[dev]"
   ```

3. Run Alembic migrations to create all database tables:
   ```bash
   python -m alembic upgrade head
   ```

4. Verify your Twitter session cookies:
   ```bash
   python scripts/verify_twscrape_session.py
   ```
   *Expected output:*
   ```text
   ACCOUNT_LOADED: True
   ACCOUNT_ACTIVE: True
   TESTING_AUTHENTICATED_REQUEST...
   AUTHENTICATED_REQUEST_SUCCESS: True
   ```

---

### Step 5: Ingest Twitter Data

You can collect data in two ways:

#### Option A: Ad-Hoc Ingestion (Single Query or User)
```bash
# Ingest by search query / hashtag
python backend/scripts/ingest_twitter.py --query "#AI" --limit 25

# Ingest by user profile timeline
python backend/scripts/ingest_twitter.py --user "elonmusk" --limit 25
```

#### Option B: Automated Multi-Topic Collection with Full Provenance
The project comes with a curated multi-topic configuration (`config/collection_queries.yaml`) across tech, finance, economy, national governance, and climate:
```bash
# Collect from all configured queries (with audit tracking)
python backend/scripts/collect_queries.py --limit-per-query 20

# View collection audit and data provenance summary:
python backend/scripts/collect_queries.py --report
```

---

### Step 6: Run Analytics Pipeline

Run the analytics engines in sequence over the collected data:

```mermaid
flowchart LR
    A["1. Collect Tweets"] --> B["2. Sentiment Analysis\nanalyze_sentiment.py"]
    B --> C["3. Sarcasm Detection\nanalyze_sarcasm.py"]
    C --> D["4. Topic & Trend Detection\nanalyze_trends.py"]
    D --> E["5. Network Topology\nanalyze_network.py"]
```

1. **Sentiment Analysis**:
   ```bash
   python backend/scripts/analyze_sentiment.py --limit 200
   ```
2. **Sarcasm Detection & Fusion**:
   ```bash
   python backend/scripts/analyze_sarcasm.py --limit 200
   ```
3. **Trend & Topic Discovery (15-min velocity window)**:
   ```bash
   python backend/scripts/analyze_trends.py --window-minutes 15 --min-cluster-size 3
   ```
4. **Network Influence, PageRank & Community Topology**:
   ```bash
   # Global interaction network
   python backend/scripts/analyze_network.py

   # Or filtered to a specific topic ID:
   python backend/scripts/analyze_network.py --topic-id 1
   ```

---

### Step 7: Launch Backend & Frontend

#### 1. Start the FastAPI Backend:
In `backend/` directory:
```bash
uvicorn app.main:app --reload --port 8000
```
- API is live at: `http://localhost:8000`
- Interactive Swagger Documentation: `http://localhost:8000/docs`

#### 2. Start the Next.js Frontend:
In another terminal, navigate to `frontend/`:
```bash
cd frontend
npm install
npm run dev
```
- Open your browser to: **`http://localhost:3000`**

---

### Step 8: Run Tests

Execute the comprehensive test suite (unit tests, analytics validation, API routes):
```bash
python -m pytest backend/tests -v
```

---

## 🔬 Models, Methods & Engineering Rationale

Every model, algorithm, and architectural decision was deliberately chosen for speed, reproducibility, explainability, and technical rigor:

| Task / Domain | Selected Technology | Why Chosen? (Engineering Rationale) |
|---|---|---|
| **Data Acquisition** | `twscrape` (GraphQL / session pool) | Official X API v2 has prohibitive paywalls and severe rate limits for research. `twscrape` provides robust session pool rotation and accesses rich GraphQL payload structures. |
| **Relational Storage** | PostgreSQL 17 + SQLAlchemy 2.0 + Alembic | Strictly enforces relational integrity across users, tweets, interactions, and versioned analysis runs. Guarantees reproducible provenance without unnecessary NoSQL/graph DB overhead. |
| **Multilingual Sentiment** | `cardiffnlp/twitter-xlm-roberta-base-sentiment` | Pre-trained specifically on social media across 100+ languages. Unlike generic BERT or VADER, it natively handles Twitter colloquialisms, emojis, hashtags, and code-mixed formats. |
| **Sarcasm Detection** | `mrm8488/t5-base-finetuned-sarcasm-twitter` | Dedicated sequence-to-sequence model fine-tuned on Twitter sarcasm datasets. Provides calibrated sarcasm probabilities. |
| **Sentiment-Sarcasm Fusion** | Confidence-Aware Decision Matrix | **Prevents naive sentiment inversion**: Flipping positive to negative on every sarcastic flag ruins accuracy. Instead, fusion evaluates confidence thresholds and categorizes results into transparent analyst evidence tags. |
| **Semantic Embeddings** | `sentence-transformers/all-MiniLM-L6-v2` | Dense 384-dimensional vector embeddings with rapid CPU inference and minimal VRAM requirements. Groups semantically equivalent tweets without keyword overlap. |
| **Topic Clustering** | HDBSCAN (`min_cluster_size=3`, metric: `cosine`) | Density-based hierarchical clustering. Unlike K-Means, it does **not** require pre-specifying cluster count $k$, and it natively tags noise points as outliers instead of creating hallucinated topics. |
| **Trend Velocity & Acceleration** | 15-Min Sliding Window with Baseline Smoothing | $Velocity = \frac{CurrentMentions}{\max(BaselineMentions, 1.0)}$. Detects sudden spikes in narrative attention before they reach peak raw volume. |
| **Network Influence** | Directed Weighted PageRank ($\alpha=0.85$) | Follower counts can be bought or inactive. Incoming interaction edges (replies, reposts, quotes, mentions) quantify **real conversational attention and influence**. |
| **Community Detection** | Louvain Modularity Maximization | Computes organic conversational communities from undirected weighted interaction projections $W\{A,B\} = W(A\to B) + W(B\to A)$ deterministically (`seed=42`). |
| **Bridge Account Discovery** | Shortest-Path Betweenness Centrality | Uses derived distance ($distance = 1.0 / weight$). Finds pivotal accounts that link otherwise disconnected communities, pinpointing cross-pollinating amplifiers. |
| **Demographic Inference** | `euagendas/m3inference` (Phase 5) | Deep-learning multimodal demographic inference (age, gender, org vs human) using profile metadata and images, outputting calibrated probability distributions. |
| **Visualization & UX** | Next.js 14 + Cytoscape.js + Recharts | Dark intelligence console UI. Cytoscape.js delivers sub-millisecond client-side graph physics, ego-network isolation, and synchronized narrative filtering. |

---

## 📊 Visual Workflow & Algorithmic Flowcharts

### 1. Confidence-Aware Sarcasm Fusion Matrix
Rather than bluntly inverting sentiment scores, our fusion algorithm preserves both primary sentiment and sarcasm probability:

```mermaid
flowchart TD
    T["Raw Tweet Text"] --> S_MODEL["XLM-RoBERTa Sentiment"]
    T --> C_MODEL["T5 Sarcasm Detector"]

    S_MODEL -->|"Base Sentiment + Confidence"| FUSION{"Confidence-Aware\nFusion Evaluator"}
    C_MODEL -->|"Sarcasm Probability"| FUSION

    FUSION -->|"Sarcasm < 0.5"| R1["NO_SARCASM\n(Retain Base Sentiment)"]
    FUSION -->|"Sarcasm >= 0.5 & High Base Conf & Opposing Valence"| R2["SARCASM_CONSISTENT\n(Flag Sarcastic Reversal)"]
    FUSION -->|"Sarcasm >= 0.5 & Conflicting Valence"| R3["SARCASM_AMBIGUOUS\n(Tag for Analyst Inspection)"]
    FUSION -->|"Sarcasm >= 0.5 & Low Confidence"| R4["SARCASM_UNCERTAIN\n(Preserve Unaltered)"]

    R1 & R2 & R3 & R4 --> DB[("sentiment_results Table\n(Base + Final + Status Logged)")]
```

---

### 2. Trend Emergence & Velocity Engine
How the system catches rising narratives before they peak:

```mermaid
flowchart LR
    TW["Ingested Tweets (UTC)"] --> BUCKET["15-Min Time Windows\n[t - 15m, t]"]
    BUCKET --> COUNT["Current Mention Count (M_t)"]
    
    BASE["Preceding 2-Hour Windows\n(8 Windows Baseline)"] --> AVG["Compute Baseline Average (M_base)"]
    
    COUNT & AVG --> CALC["Velocity Calculation\nV = M_t / max(M_base, 1.0)"]
    CALC --> ACC["Acceleration Calculation\nA = V_t - V_(t-1)"]
    
    ACC --> FILTER{"Support Filter\nM_t >= 2?"}
    FILTER -->|No| ZERO["Velocity = 0.0\n(Suppresses Spurious Spikes)"]
    FILTER -->|Yes| OUT["Flag Emerging Trend\n(Ranked by Velocity & Accel)"]
```

---

### 3. Interaction Topology: Influence & Bridge Detection
How the network engine identifies conversational leaders and narrative bridges:

```mermaid
flowchart TD
    subgraph Raw["Conversational Interactions"]
        I1["Author replies to Target"]
        I2["Author quotes Target"]
        I3["Author mentions Target"]
        I4["Author reposts Target"]
    end

    Raw --> G["Directed Interaction Graph\nActor (Source) ──► Referenced Account (Target)\nWeight = Sum of Interactions"]

    G --> PR["Weighted PageRank (alpha=0.85)\nIncoming attention = High Influence"]
    G --> PROJ["Undirected Weighted Projection\nW{A,B} = W(A->B) + W(B->A)"]
    
    PROJ --> LOUVAIN["Louvain Community Detection\nDiscovers Echo Chambers"]
    
    G --> DIST["Derive Distance = 1.0 / Weight\n(Stronger interaction = Shorter path)"]
    DIST --> BC["Betweenness Centrality\nMeasures Shortest Path Bottlenecks"]
    
    LOUVAIN & BC --> BRIDGE["Bridge Account Identification\nIdentifies nodes connecting disparate communities"]
```

---

### 4. Analyst Investigation Workflow in Dashboard

```mermaid
flowchart TD
    START["Analyst Enters Dashboard"] --> OVERVIEW["1. Check Key Signals & Overview\n(Total tweets, sentiment ratio, emerging topics)"]
    OVERVIEW --> ROSTER["2. Emerging Narratives Roster\n(Select high-velocity narrative)"]
    ROSTER --> SYNC{"Context Synchronizer"}
    
    SYNC -->|"Filter by Topic"| TIMELINE["3. Sentiment Trajectory\n(Inspect volume & percentage changes)"]
    SYNC -->|"Filter by Topic"| TOPOLOGY["4. Cytoscape.js Network Workstation\n(Explore communities & PageRank leaders)"]
    
    TOPOLOGY --> EGO["5. Activate Ego-Network Mode\n(Isolate 1-hop neighborhood of key influencer)"]
    TOPOLOGY --> BRIDGE_INSPECT["6. Inspect Bridge Nodes\n(Trace which accounts transferred topic between clusters)"]
    
    BRIDGE_INSPECT --> TWEETS["7. Inspect Verified Tweet Stream\n(Review exact quotes, sarcasm status & evidence drawer)"]
```

---

## 🔌 API Endpoints Overview

The backend exposes a high-speed, precomputed REST API (`/api/v1/*`):

| Endpoint | Method | Description |
|---|---|---|
| `/api/v1/overview` | `GET` | High-level dataset summary, sentiment distribution, and top emerging topics. |
| `/api/v1/tweets` | `GET` | Paginated tweets with author info, sentiment tags, and topic assignments. |
| `/api/v1/sentiment/summary` | `GET` | Aggregated positive, neutral, negative counts and sarcasm breakdown. |
| `/api/v1/sentiment/timeline` | `GET` | Chronological sentiment trajectory across 1h, 4h, or 1d intervals. |
| `/api/v1/trends` | `GET` | Ranked list of detected topics with velocity, acceleration, and mention counts. |
| `/api/v1/trends/{topic_id}` | `GET` | In-depth details, representative terms, and metrics for a specific topic. |
| `/api/v1/network/summary` | `GET` | Overall graph topology (nodes, edges, density, components). |
| `/api/v1/network/nodes` | `GET` | Top accounts ranked by PageRank or Betweenness Centrality. |
| `/api/v1/network/communities` | `GET` | Detected Louvain communities with user counts and sentiment distribution. |
| `/api/v1/network/flows` | `GET` | Observed cross-community interaction volume. |
| `/api/v1/analysis/status` | `GET` | Pipeline readiness and status across roadmap dimensions. |

---

## 📂 Repository Structure

```text
social-media-analysis/
├── compose.yaml                    # Docker Compose config (PostgreSQL 17)
├── .env.example                    # Environment variable template
├── AGENTS.md                       # Agent protocol and repository invariants
├── PROJECT_CONTEXT.md              # Authoritative technical & product specification
├── CURRENT_STATE.md                # Real-time implementation status & test log
├── README.md                       # This comprehensive documentation guide
│
├── config/
│   └── collection_queries.yaml     # Curated multi-topic search query definitions
│
├── docs/                           # Architectural contracts & research notes
│   ├── architecture/               # API, Database, and Pipeline specifications
│   ├── decisions/                  # Architecture Decision Records (ADRs)
│   └── research/                   # Model benchmarks, registry & experiment logs
│
├── backend/                        # FastAPI Backend & Analytics Pipelines
│   ├── alembic.ini                 # Database migration configuration
│   ├── pyproject.toml              # Python dependencies & build metadata
│   ├── app/
│   │   ├── main.py                 # FastAPI application factory & CORS setup
│   │   ├── api/v1/                 # REST API endpoints (/api/v1/*)
│   │   ├── core/                   # App configuration & settings
│   │   ├── db/                     # SQLAlchemy session & base classes
│   │   ├── models/                 # ORM Models (User, Tweet, Interaction, Topic, etc.)
│   │   ├── services/               # Twitter collector & ingestion services
│   │   └── analytics/              # ML & graph processing engines:
│   │       ├── sentiment/          # XLM-RoBERTa sentiment analyzer
│   │       ├── sarcasm/            # T5 sarcasm detector & fusion logic
│   │       ├── trends/             # MiniLM + HDBSCAN + velocity engine
│   │       └── network/            # NetworkX PageRank, Louvain & Betweenness
│   ├── migrations/                 # Alembic migration scripts
│   ├── scripts/                    # CLI execution tools:
│   │   ├── ingest_twitter.py       # Single-query/user tweet collector
│   │   ├── collect_queries.py      # Automated multi-query YAML collector
│   │   ├── verify_twscrape_session # Session cookie & auth tester
│   │   ├── analyze_sentiment.py    # Batch sentiment classification
│   │   ├── analyze_sarcasm.py      # Batch sarcasm detection
│   │   ├── analyze_trends.py       # Topic clustering & velocity runner
│   │   └── analyze_network.py      # Graph topology & community runner
│   └── tests/                      # Pytest test suite (80+ unit/integration tests)
│
└── frontend/                       # Next.js 14 Intelligence Workstation
    ├── app/                        # Next.js App Router (pages & layouts)
    ├── components/                 # UI components (Cytoscape graph, charts, drawers)
    ├── lib/                        # API client, TypeScript interfaces & graph helpers
    └── package.json                # Frontend dependencies (React, Cytoscape, Recharts)
```

---

## 👥 Team & Attribution
- **Project**: INTEL_SYNTHESIS
- **Team**: Adastra
- **Problem Statement**: SIH26152 — Social Media Analytics
- **Canonical Specification**: [`PROJECT_CONTEXT.md`](PROJECT_CONTEXT.md)
