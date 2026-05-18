import argparse
import json
import logging
from collections import defaultdict
from pathlib import Path

from data_pipeline.preprocess import iter_standardized_attempts
from data_pipeline.schemas import StandardizedAttempt
from recommendation_engine.performance import summarize_student_performance

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    filename=LOG_DIR / "analytics.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


def load_attempts_by_student(source_csv: str | Path) -> dict[str, list[StandardizedAttempt]]:
    grouped: dict[str, list[StandardizedAttempt]] = defaultdict(list)
    for attempt in iter_standardized_attempts(source_csv):
        grouped[attempt.student_id].append(attempt)
    logger.info("Loaded attempts for %s students", len(grouped))
    return dict(grouped)


def build_gemini_input(summary: dict) -> dict:
    return {
        "student_id": summary["student_id"],
        "overall_accuracy": summary["overall_accuracy"],
        "weak_topics": [
            {
                "skill": topic["skill"],
                "accuracy": topic["accuracy"],
                "attempts": topic["attempts"],
                "average_attempt_time": topic["average_attempt_time"],
            }
            for topic in summary["weak_topics"]
        ],
        "total_attempts": summary["total_attempts"],
    }


def generate_student_outputs(
    source_csv: str | Path,
    output_dir: str | Path,
    *,
    weak_threshold: float = 0.7,
    min_attempts: int = 3,
    sample_student_id: str | None = None,
) -> dict[str, dict]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    grouped = load_attempts_by_student(source_csv)
    summaries: dict[str, dict] = {}

    for student_id, attempts in grouped.items():
        summary = summarize_student_performance(
            attempts,
            weak_threshold=weak_threshold,
            min_attempts=min_attempts,
        )
        summaries[student_id] = summary

    selected_student = sample_student_id or next(iter(summaries))
    selected_summary = summaries[selected_student]
    gemini_input = build_gemini_input(selected_summary)

    (output_path / f"student_{selected_student}_summary.json").write_text(
        json.dumps(selected_summary, indent=2),
        encoding="utf-8",
    )
    (output_path / f"student_{selected_student}_gemini_input.json").write_text(
        json.dumps(gemini_input, indent=2),
        encoding="utf-8",
    )
    logger.info("Generated analytics outputs for sample student %s", selected_student)
    return summaries


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute student topic analytics from the educational dataset.")
    parser.add_argument("--input", default="students dataset.csv")
    parser.add_argument("--output-dir", default="sample_outputs")
    parser.add_argument("--weak-threshold", type=float, default=0.7)
    parser.add_argument("--min-attempts", type=int, default=3)
    parser.add_argument("--student-id", default=None)
    args = parser.parse_args()

    summaries = generate_student_outputs(
        args.input,
        args.output_dir,
        weak_threshold=args.weak_threshold,
        min_attempts=args.min_attempts,
        sample_student_id=args.student_id,
    )
    print(f"Generated summaries for {len(summaries)} students")


if __name__ == "__main__":
    main()

