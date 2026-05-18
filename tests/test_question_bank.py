from data_pipeline.schemas import StandardizedAttempt
from recommendation_engine.question_bank import build_question_index, recommend_questions


def test_question_bank_infers_difficulty_and_recommends() -> None:
    attempts = [
        StandardizedAttempt(student_id="1", skill="Fractions", correct=0, attempt_time=10, problem_id="p1"),
        StandardizedAttempt(student_id="2", skill="Fractions", correct=0, attempt_time=12, problem_id="p1"),
        StandardizedAttempt(student_id="3", skill="Fractions", correct=1, attempt_time=8, problem_id="p2"),
        StandardizedAttempt(student_id="4", skill="Fractions", correct=1, attempt_time=9, problem_id="p2"),
    ]
    index = build_question_index(attempts)
    recs = recommend_questions(
        weak_topic="Fractions",
        grade_level=6,
        target_difficulty="hard",
        question_index=index,
    )
    assert recs[0]["problem_id"] == "p1"
