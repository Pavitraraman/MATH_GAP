from pydantic import BaseModel, Field


class LLMWeakTopic(BaseModel):
    topic: str
    confidence: float = Field(ge=0, le=1)


class StudentLLMAnalysis(BaseModel):
    weak_topics: list[LLMWeakTopic]
    recommended_difficulty_progression: list[str]
    practice_focus_areas: list[str]

