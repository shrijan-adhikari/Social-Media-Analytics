# INTEL_SYNTHESIS

Twitter-focused narrative intelligence platform for **SIH26152 — Social Media Analytics**, Team Adastra.

The system collects X/Twitter data, normalizes it into PostgreSQL, and joins four analytical dimensions:

- sentiment / sarcasm
- aggregate demographic inference
- trend and semantic narrative detection
- interaction-network analysis

The main product objective is **Narrative Propagation Intelligence**: explain what is rising, who participates, how audiences react, who amplifies it, which communities it crosses, and how it changes over time.

## Canonical documentation

- `PROJECT_CONTEXT.md` — authoritative product and technical specification
- `CURRENT_STATE.md` — current implementation status
- `AGENTS.md` — cross-agent working rules
- `docs/research/MODELS.md` — model registry quick reference
- `docs/architecture/` — implementation contracts
- `docs/decisions/` — architecture decision records

## Current scope

**X/Twitter only.** Other platforms are intentionally out of scope for the MVP.

## Planned stack

- Collection: twscrape
- Backend: FastAPI / Python
- Database: PostgreSQL + SQLAlchemy + Alembic
- Demographics: M3-Inference
- Sentiment: CardiffNLP Twitter XLM-R sentiment checkpoint
- Sarcasm: T5 Twitter sarcasm checkpoint
- Embeddings: all-MiniLM-L6-v2
- Clustering: HDBSCAN
- Graph: NetworkX + PageRank + Louvain
- Frontend: Next.js / React / TypeScript
- Frontend deployment: Vercel
- Backend/ML: persistent container/VM service

See `PROJECT_CONTEXT.md` before implementing.
