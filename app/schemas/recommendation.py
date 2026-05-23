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


class RecommendedQuestion(BaseModel):
    problem_id: str
    skill: str
    grade_level: int
    difficulty: str
    empirical_accuracy: float


class RecommendationPlan(BaseModel):
    summary: str
    weak_topics: list[WeakTopic]
    activities: list[StudyActivity]
    recommended_questions: list[RecommendedQuestion] = Field(default_factory=list)
    next_assessment_focus: list[str]


class RecommendationRead(BaseModel):
    id: int
    assessment_id: int
    student_id: str
    weak_topics: list[WeakTopic]
    plan: RecommendationPlan
    created_at: datetime


class AdaptiveRecommendationItem(BaseModel):
    concept_name: str = Field(description="Name of the diagnosed weak concept")
    recommended_questions: list[RecommendedQuestion] = Field(description="Scored & selected questions from the precomputed question bank")
    difficulty: str = Field(description="Adapted question difficulty level (easy, medium, hard)")
    reasoning: str = Field(description="Pedagogy explanation combining student performance metrics and Gemini reasoning")
    topic_relevance_score: float = Field(description="Dynamically calculated recommendation score")


class AdaptiveRecommendationResponse(BaseModel):
    student_id: str
    personalized_learning_strategy: str
    recommendations: list[AdaptiveRecommendationItem]



