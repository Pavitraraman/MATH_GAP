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

## Project structure

```text
app/                    # API, schemas, services, models, database access
prompts/                # versioned LLM prompts
evaluation/             # offline evaluation utilities
recommendation_engine/  # deterministic recommendation logic
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

## Gemini configuration

Configure Gemini via environment variables in `.env`:

```env
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-2.5-flash
DEFAULT_PROMPT_NAME=adaptive_recommendation
DEFAULT_PROMPT_VERSION=v1
```

The backend requests structured JSON responses, validates them against the recommendation schema, records latency/cost metadata for every call, and returns `502 Bad Gateway` when Gemini fails or produces invalid structured output.

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
