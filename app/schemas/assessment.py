from datetime import datetime

from pydantic import BaseModel, Field


class TopicScoreIn(BaseModel):
    topic: str
    score: float = Field(ge=0, le=100)
    confidence: float = Field(default=1.0, ge=0, le=1)


class AssessmentCreate(BaseModel):
    student_id: str
    grade_level: int = Field(ge=1, le=12)
    overall_score: float = Field(ge=0, le=100)
    topic_scores: list[TopicScoreIn]


class TopicScoreRead(TopicScoreIn):
    id: int

    model_config = {"from_attributes": True}


class AssessmentRead(BaseModel):
    id: int
    student_id: str
    grade_level: int
    overall_score: float
    created_at: datetime
    topic_scores: list[TopicScoreRead]

    model_config = {"from_attributes": True}

