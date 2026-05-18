from pydantic import BaseModel


class StandardizedAttempt(BaseModel):
    student_id: str
    skill: str
    correct: int
    attempt_time: float
    timestamp: int | None = None
    difficulty: str | None = None
    problem_id: str | None = None

