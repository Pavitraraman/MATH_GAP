# Architecture

## Modules

- `app/`: API layer, models, schemas, services, configuration, database access
- `recommendation_engine/`: deterministic domain logic such as weak-topic detection
- `prompts/`: versioned prompt templates used by LLM orchestration
- `evaluation/`: offline metrics utilities
- `data_pipeline/`: streaming CSV normalization and standardized attempt records

## Request flow

1. `POST /assessments` stores student assessment data and topic-level scores.
2. `POST /recommendations/{assessment_id}` loads the assessment, detects weak topics, resolves the active prompt version, calls Gemini, validates structured JSON, persists the recommendation, and logs LLM latency/cost.
3. `GET /metrics/dashboard` returns aggregate operational and product metrics.

## Dataset analytics flow

1. `data_pipeline.preprocess` streams raw CSV records into standardized attempt objects.
2. `recommendation_engine.performance` aggregates topic-wise accuracy and weak topics.
3. `StudentAnalysisService` sends compact summaries to Gemini using a dedicated prompt version.
4. `recommendation_engine.question_bank` maps weak topics to practice questions using empirical difficulty inferred from historical correctness rates.

## Design choices

- Deterministic weak-topic detection stays outside the LLM for auditability.
- Prompt templates are both file-backed and persisted in the database for traceability.
- Gemini responses are validated against a Pydantic schema before persistence.
- Cost is configurable because provider pricing can change over time.
