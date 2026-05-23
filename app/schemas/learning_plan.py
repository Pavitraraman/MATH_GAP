from pydantic import BaseModel, Field

class ConceptLearningGap(BaseModel):
    concept_name: str = Field(description="Name of the weak concept or mathematical skill")
    reasoning: str = Field(description="Diagnostic reasoning explaining specific error patterns, response times, and gaps")
    recommended_difficulty_progression: str = Field(description="Recommended progression path for question difficulties, e.g., 'easy -> medium'")
    recommended_question_types: list[str] = Field(description="Concrete practice suggestions and specific types of questions to solve")
    confidence_score: float = Field(ge=0.0, le=1.0, description="Confidence score in diagnosing this concept gap")

class StudentLearningPlan(BaseModel):
    student_id: str = Field(description="ID of the student")
    weak_concepts: list[ConceptLearningGap] = Field(description="Detailed gap analysis per diagnosed weak concept")
    personalized_learning_strategy: str = Field(description="Personalized pedagogical strategy to master the identified gaps")

class GenerateLearningPlanRequest(BaseModel):
    student_id: str
    weak_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    min_attempts: int = Field(default=3, ge=1)
