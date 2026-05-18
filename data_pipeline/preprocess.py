import csv
import json
import re
from collections.abc import Iterator
from pathlib import Path

from data_pipeline.schemas import StandardizedAttempt

NULL_LIKE = {"", "na", "n/a", "null", "none"}


def normalize_column_name(name: str) -> str:
    name = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name)
    name = re.sub(r"[^a-zA-Z0-9]+", "_", name)
    return name.strip("_").lower()


def clean_value(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return None if stripped.lower() in NULL_LIKE else stripped


def iter_standardized_attempts(csv_path: str | Path) -> Iterator[StandardizedAttempt]:
    with Path(csv_path).open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for raw_row in reader:
            row = {normalize_column_name(key): clean_value(value) for key, value in raw_row.items()}
            student_id = row.get("student_id")
            skill = row.get("skill")
            correct = row.get("correct")
            attempt_time = row.get("time_taken")
            if not all([student_id, skill, correct, attempt_time]):
                continue
            yield StandardizedAttempt(
                student_id=student_id,
                skill=skill.replace("-", " ").title(),
                correct=int(float(correct)),
                attempt_time=float(attempt_time),
                timestamp=int(float(row["start_time"])) if row.get("start_time") else None,
                difficulty=row.get("difficulty"),
                problem_id=row.get("problem_id"),
            )


def write_jsonl(csv_path: str | Path, output_path: str | Path) -> int:
    count = 0
    with Path(output_path).open("w", encoding="utf-8") as handle:
        for attempt in iter_standardized_attempts(csv_path):
            handle.write(json.dumps(attempt.model_dump(), ensure_ascii=False) + "\n")
            count += 1
    return count

