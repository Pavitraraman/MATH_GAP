from pydantic import BaseModel, Field


class LLMWeakTopic(BaseModel):
    topic: str
    confidence: float = Field(ge=0, le=1)


class StudentLLMAnalysis(BaseModel):
    weak_concepts: list[LLMWeakTopic]
    recommended_difficulty_progression: list[str]
    suggested_practice_strategy: list[str]
