# Dataset pipeline

## Detected source columns

The current CSV includes the fields needed for the core pipeline:

- `studentId` -> `student_id`
- `skill` -> `skill`
- `correct` -> `correct`
- `startTime` -> `timestamp`
- `timeTaken` -> `attempt_time`
- `problemId` -> `problem_id`

No explicit difficulty column is present. The recommendation layer therefore treats difficulty as optional in preprocessing and can infer question difficulty from empirical correctness rates across historical attempts.

## Standardized record

```json
{
  "student_id": "2841",
  "skill": "Linear Equations",
  "correct": 0,
  "attempt_time": 52,
  "timestamp": 1096470301,
  "difficulty": null,
  "problem_id": "1118"
}
```

## Flow

1. Stream the source CSV rather than loading the full dataset into memory.
2. Normalize field names and drop records missing required identifiers.
3. Emit standardized JSONL attempts.
4. Aggregate topic-wise accuracy and student summaries.
5. Send summaries to Gemini for higher-level interpretation.
6. Build question recommendations from weak topics and empirically inferred difficulty.

