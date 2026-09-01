# MODELS.md — Model Registry Quick Reference

> Quick-reference extract of `PROJECT_CONTEXT.md` §24.
> If this file disagrees with `PROJECT_CONTEXT.md`, the latter is authoritative.

## Registry

| Component | Model / project | Status | Fine-tuned by us? | Context |
|---|---|---|---|---|
| Sentiment | `cardiffnlp/twitter-xlm-roberta-base-sentiment` | PRIMARY / APPROVED | No | §24.1 |
| Sentiment alt | `cardiffnlp/twitter-xlm-roberta-base-sentiment-multilingual` | EVALUATION CANDIDATE | No | §24.1 |
| XLM-R backbone | `FacebookAI/xlm-roberta-base` | REFERENCE ONLY | N/A | §24.1 |
| Sarcasm | `mrm8488/t5-base-finetuned-sarcasm-twitter` | PRIMARY / APPROVED | No | §24.4 |
| Emotion | not yet selected | NOT SELECTED | TBD | §24.4b |
| Stance | not yet selected | NOT SELECTED | TBD | §24.4c |
| Indian-language backbone | `google/muril-base-cased` | DISABLED / EXPERIMENTAL | Required before task use | §24.5 |
| Demographics | `euagendas/m3inference` | PRIMARY / APPROVED | No | §24.7 |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` | PRIMARY / APPROVED | No | §24.6 |
| Topic clustering | HDBSCAN | PRIMARY / APPROVED | N/A | §24.6 |
| Influence | Weighted PageRank / NetworkX | PRIMARY / APPROVED | N/A | §8 |
| Communities | Louvain | PRIMARY / APPROVED | N/A | §8 |

## Sentiment

**Outputs:** Positive / Neutral / Negative probabilities.

**Does not:** detect sarcasm, emotion, or stance.

Input preparation:
- mentions → `@user`
- URLs → `http`
- preserve hashtags, emojis, negations, Hindi/Hinglish
- keep original tweet text unchanged

Never overwrite base sentiment after sarcasm processing. Persist base and final interpretation separately.

## Sarcasm

`mrm8488/t5-base-finetuned-sarcasm-twitter`

Outputs sarcasm/not-sarcasm with confidence. Sarcasm is additional evidence; it does not automatically mean `positive → negative`.

External model-card metrics are not project evaluation results.

## Demographics

`euagendas/m3inference`

Outputs probability distributions for:
- age: `<=18`, `19-29`, `30-39`, `>=40`
- gender: female / male
- account type: organization / non-organization

Does **not** output profession, interests, geography, or language.

Routing:

```text
full multimodal M3
        ↓ image unavailable
M3 text-only
        ↓ inadequate input/confidence
UNCLASSIFIED
```

Keep M3 isolated behind `analytics/demographics/m3_service.py` or equivalent.

## Embeddings

`sentence-transformers/all-MiniLM-L6-v2`

Used only for semantic similarity/topic discovery:

`tweet → embedding → HDBSCAN → cluster → TF-IDF/representative terms`

Do not repurpose embedding distance as sentiment or stance.

## MuRIL

`google/muril-base-cased`

**DISABLED BY DEFAULT.** It is a pretrained Indian-language representation model, not a ready sentiment/sarcasm classifier.

Enable only after task-specific fine-tuning/evaluation demonstrates improvement over the approved pipeline.

## Emotion and stance

Both are **NOT SELECTED**.

Before implementation:
1. propose 1–2 candidate checkpoints with links,
2. verify label taxonomy,
3. log an experiment,
4. obtain explicit approval.

Until then use `NULL` / `unclassified`.

## Model replacement process

1. Do not silently replace a primary model.
2. Record candidate + repository.
3. Explain expected advantage.
4. Benchmark on the same local evaluation set.
5. Compare quality, latency, memory.
6. Log under `docs/research/model-experiments/`.
7. Recommend only after evidence exists.
8. Obtain user approval before changing PRIMARY status.

## Fine-tuning policy

```text
Sentiment → NO project fine-tuning for MVP
Sarcasm   → NO project fine-tuning for MVP
M3        → NO project fine-tuning for MVP
MiniLM    → NO project fine-tuning for MVP
MuRIL     → DISABLED
```
