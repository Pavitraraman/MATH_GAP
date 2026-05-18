from collections import defaultdict

from data_pipeline.schemas import StandardizedAttempt


def summarize_student_performance(
    attempts: list[StandardizedAttempt],
    *,
    weak_threshold: float = 0.7,
    min_attempts: int = 3,
) -> dict:
    by_skill: dict[str, list[StandardizedAttempt]] = defaultdict(list)
    for attempt in attempts:
        by_skill[attempt.skill].append(attempt)

    topic_summaries = []
    for skill, records in by_skill.items():
        total = len(records)
        correct = sum(item.correct for item in records)
        accuracy = correct / total if total else 0.0
        topic_summaries.append(
            {
                "skill": skill,
                "attempts": total,
                "correct": correct,
                "accuracy": round(accuracy, 4),
                "average_attempt_time": round(sum(item.attempt_time for item in records) / total, 2),
                "is_weak": total >= min_attempts and accuracy < weak_threshold,
            }
        )

    topic_summaries.sort(key=lambda item: (item["accuracy"], -item["attempts"], item["skill"]))
    weak_topics = [item for item in topic_summaries if item["is_weak"]]
    overall_accuracy = sum(item.correct for item in attempts) / len(attempts) if attempts else 0.0
    return {
        "student_id": attempts[0].student_id if attempts else None,
        "total_attempts": len(attempts),
        "overall_accuracy": round(overall_accuracy, 4),
        "weak_topics": weak_topics,
        "topics": topic_summaries,
    }

