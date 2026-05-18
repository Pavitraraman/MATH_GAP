# Math Gap

FastAPI backend for an LLM-powered adaptive math recommendation engine.

## Features

- student assessment ingestion
- weak topic detection
- Gemini API integration
- prompt version tracking
- recommendation engine
- evaluation metrics dashboard
- PostgreSQL integration
- JSON structured outputs
- latency and cost logging
- graceful Gemini provider error handling
- Gemini-powered learning gap analysis with retry support

## Project structure

```text
app/                    # API, schemas, services, models, database access
prompts/                # versioned LLM prompts
evaluation/             # offline evaluation utilities
recommendation_engine/  # deterministic recommendation logic
data_pipeline/           # dataset preprocessing and standardization
docs/                   # architecture documentation
main.py                 # root FastAPI entry point
requirements.txt        # pip-friendly dependency list
```

## Quick start

```powershell
Copy-Item .env.example .env
docker compose up -d
python -m pip install -r requirements.txt
alembic upgrade head
uvicorn main:app --reload
```

For development tooling such as tests, you can also install the project extras:

```powershell
python -m pip install -e ".[dev]"
```

## Endpoints

- `GET /health`
- `POST /assessments`
- `POST /recommendations/{assessment_id}`
- `GET /metrics/dashboard`
- `GET /metrics/llm-logs`
- `POST /analysis/learning-gap`

## Gemini configuration

Configure Gemini via environment variables in `.env`:

```env
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-2.5-flash
DEFAULT_PROMPT_NAME=adaptive_recommendation
DEFAULT_PROMPT_VERSION=v1
```

The backend requests structured JSON responses, validates them against the recommendation schema, records latency/cost metadata for every call, and returns `502 Bad Gateway` when Gemini fails or produces invalid structured output.

The learning-gap analysis endpoint accepts a processed student performance summary and returns weak concepts, confidence scores, a recommended difficulty progression, and a suggested practice strategy. The service persists both the prompt metadata and model output, and retries bounded transient failures before surfacing an error.

## Dataset preprocessing

The repository includes a streaming preprocessing pipeline for the downloaded educational dataset:

```powershell
python preprocessing.py
python analytics.py --student-id 8
```

This writes:

- standardized JSONL attempt records to `data/processed/student_attempts.jsonl`
- sample processed records to `sample_outputs/standardized_attempts_sample.json`
- a student performance summary to `sample_outputs/student_8_summary.json`
- a Gemini-ready structured input payload to `sample_outputs/student_8_gemini_input.json`
- execution logs under `logs/`

## Streamlit dashboard

Start the API first, then launch the dashboard:

```powershell
uvicorn main:app --reload
streamlit run dashboard/streamlit_app.py
```

The dashboard shows uploaded student data, topic-wise accuracy, weak concepts, live Gemini analysis output, recommended questions, latency metrics, prompt versions, and model response logs, with filtering by `student_id`.

## Example assessment payload

```json
{
  "student_id": "student-123",
  "grade_level": 8,
  "overall_score": 68,
  "topic_scores": [
    {"topic": "linear equations", "score": 62, "confidence": 0.9},
    {"topic": "fractions", "score": 48, "confidence": 0.95}
  ]
}
```
