from pydantic import BaseModel, Field


class AnalyzeStudentRequest(BaseModel):
    student_id: str
    dataset_path: str = "students dataset.csv"
    weak_threshold: float = Field(default=0.7, ge=0, le=1)
    min_attempts: int = Field(default=3, ge=1)


class TopicAccuracy(BaseModel):
    skill: str
    accuracy: float
    attempts: int
    average_response_time: float


class AnalyzeStudentResponse(BaseModel):
    student_id: str
    weak_topics: list[dict]
    accuracy_per_topic: list[TopicAccuracy]
    average_response_time: float
    performance_summary: dict
    output_path: str | None
