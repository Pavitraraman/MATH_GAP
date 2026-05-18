from collections import defaultdict

from data_pipeline.schemas import StandardizedAttempt


def infer_difficulty(accuracy: float) -> str:
    if accuracy >= 0.8:
        return "easy"
    if accuracy >= 0.5:
        return "medium"
    return "hard"


def build_question_index(attempts: list[StandardizedAttempt]) -> dict[str, list[dict]]:
    by_problem: dict[tuple[str, str], list[StandardizedAttempt]] = defaultdict(list)
    for attempt in attempts:
        if attempt.problem_id:
            by_problem[(attempt.skill, attempt.problem_id)].append(attempt)

    index: dict[str, list[dict]] = defaultdict(list)
    for (skill, problem_id), records in by_problem.items():
        accuracy = sum(item.correct for item in records) / len(records)
        index[skill].append(
            {
                "problem_id": problem_id,
                "empirical_accuracy": round(accuracy, 4),
                "difficulty": infer_difficulty(accuracy),
            }
        )

    for skill in index:
        index[skill].sort(key=lambda item: item["empirical_accuracy"])
    return dict(index)


def recommend_questions(
    *,
    weak_topic: str,
    grade_level: int,
    target_difficulty: str,
    question_index: dict[str, list[dict]],
    limit: int = 5,
) -> list[dict]:
    candidates = [
        item
        for item in question_index.get(weak_topic, [])
        if item["difficulty"] == target_difficulty
    ]
    if not candidates:
        candidates = question_index.get(weak_topic, [])
    return [
        {
            "problem_id": item["problem_id"],
            "skill": weak_topic,
            "grade_level": grade_level,
            "difficulty": item["difficulty"],
            "empirical_accuracy": item["empirical_accuracy"],
        }
        for item in candidates[:limit]
    ]

