import json
from pathlib import Path

import pandas as pd

from data_pipeline.preprocess import normalize_column_name, standardize_row
from data_pipeline.preprocess import iter_standardized_attempts
from data_pipeline.schemas import StandardizedAttempt
from recommendation_engine.performance import summarize_student_performance


def load_student_attempts(dataset_path: str | Path, student_id: str) -> list[StandardizedAttempt]:
    path = Path(dataset_path)
    target = str(student_id)
    if path.suffix.lower() == ".csv":
        header = pd.read_csv(path, nrows=0).columns.tolist()
        normalized_to_source = {normalize_column_name(str(column)): column for column in header}
        required_columns = [
            "student_id",
            "skill",
            "correct",
            "time_taken",
            "attempt_time",
            "start_time",
            "difficulty",
            "problem_id",
        ]
        usecols = [
            normalized_to_source[column]
            for column in required_columns
            if column in normalized_to_source
        ]
        attempts: list[StandardizedAttempt] = []
        for chunk in pd.read_csv(path, chunksize=100_000, usecols=usecols, dtype=str):
            chunk = chunk.rename(columns={column: normalize_column_name(str(column)) for column in chunk.columns})
            if "student_id" not in chunk.columns:
                continue
            filtered = chunk[chunk["student_id"].astype(str) == target]
            for raw_row in filtered.where(pd.notna(filtered), None).to_dict(orient="records"):
                attempt = standardize_row(raw_row)
                if attempt is not None:
                    attempts.append(attempt)
        return attempts

    if path.suffix.lower() in {".xlsx", ".xls"}:
        dataframe = pd.read_excel(path)
        dataframe = dataframe.rename(columns={column: normalize_column_name(str(column)) for column in dataframe.columns})
        if "student_id" not in dataframe.columns:
            return []
        filtered = dataframe[dataframe["student_id"].astype(str) == target]
        return [
            attempt
            for raw_row in filtered.where(pd.notna(filtered), None).to_dict(orient="records")
            if (attempt := standardize_row(raw_row)) is not None
        ]

    return [attempt for attempt in iter_standardized_attempts(path) if str(attempt.student_id) == target]


def analyze_student_dataset(
    *,
    dataset_path: str | Path,
    student_id: str,
    output_dir: str | Path = "processed_outputs",
    weak_threshold: float = 0.7,
    min_attempts: int = 3,
) -> dict:
    attempts = load_student_attempts(dataset_path, student_id)
    if not attempts:
        return {
            "student_id": str(student_id),
            "weak_topics": [],
            "accuracy_per_topic": [],
            "average_response_time": 0.0,
            "performance_summary": {
                "student_id": str(student_id),
                "total_attempts": 0,
                "overall_accuracy": 0.0,
                "weak_topics": [],
                "topics": [],
            },
            "output_path": None,
        }

    summary = summarize_student_performance(
        attempts,
        weak_threshold=weak_threshold,
        min_attempts=min_attempts,
    )
    average_response_time = round(sum(attempt.attempt_time for attempt in attempts) / len(attempts), 2)
    result = {
        "student_id": str(student_id),
        "weak_topics": summary["weak_topics"],
        "accuracy_per_topic": [
            {
                "skill": topic["skill"],
                "accuracy": topic["accuracy"],
                "attempts": topic["attempts"],
                "average_response_time": topic["average_attempt_time"],
            }
            for topic in summary["topics"]
        ],
        "average_response_time": average_response_time,
        "performance_summary": summary,
    }

    output_path = Path(output_dir) / f"student_{student_id}_analysis.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    result["output_path"] = str(output_path)
    return result
