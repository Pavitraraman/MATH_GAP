from datetime import datetime

from pydantic import BaseModel, Field


class WeakTopic(BaseModel):
    topic: str
    score: float
    severity: str


class StudyActivity(BaseModel):
    topic: str
    action: str
    difficulty: str
    estimated_minutes: int = Field(ge=1)


class RecommendationPlan(BaseModel):
    summary: str
    weak_topics: list[WeakTopic]
    activities: list[StudyActivity]
    next_assessment_focus: list[str]


class RecommendationRead(BaseModel):
    id: int
    assessment_id: int
    student_id: str
    weak_topics: list[WeakTopic]
    plan: RecommendationPlan
    created_at: datetime

