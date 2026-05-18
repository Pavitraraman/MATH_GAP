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

## Quick start

```powershell
Copy-Item .env.example .env
docker compose up -d
python -m pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload
```

## Endpoints

- `GET /health`
- `POST /assessments`
- `POST /recommendations/{assessment_id}`
- `GET /metrics/dashboard`

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
