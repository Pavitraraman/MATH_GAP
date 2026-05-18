from data_pipeline.schemas import StandardizedAttempt
from recommendation_engine.performance import summarize_student_performance


def test_summarize_student_performance_detects_weak_topics() -> None:
    attempts = [
        StandardizedAttempt(student_id="1", skill="Fractions", correct=0, attempt_time=10),
        StandardizedAttempt(student_id="1", skill="Fractions", correct=1, attempt_time=20),
        StandardizedAttempt(student_id="1", skill="Fractions", correct=0, attempt_time=30),
        StandardizedAttempt(student_id="1", skill="Geometry", correct=1, attempt_time=15),
        StandardizedAttempt(student_id="1", skill="Geometry", correct=1, attempt_time=15),
        StandardizedAttempt(student_id="1", skill="Geometry", correct=1, attempt_time=15),
    ]
    summary = summarize_student_performance(attempts)
    assert summary["student_id"] == "1"
    assert summary["weak_topics"][0]["skill"] == "Fractions"
    assert summary["overall_accuracy"] == 0.6667

