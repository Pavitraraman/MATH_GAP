from pydantic import BaseModel, Field


class LLMWeakConcept(BaseModel):
    concept_name: str = Field(description="Name of the weak concept/topic")
    reasoning: str = Field(description="Specific pattern of errors or gaps detected for this concept")
    confidence_score: float = Field(ge=0.0, le=1.0, description="Confidence in identifying this weak concept")


class StudentLLMAnalysis(BaseModel):
    weak_concepts: list[LLMWeakConcept] = Field(description="List of weak concepts with diagnostic reasoning and confidence")
    recommended_learning_strategy: str = Field(description="High-level learning strategy to master the detected gaps")
    personalized_practice_recommendations: list[str] = Field(description="Actionable practice and question types to study")

