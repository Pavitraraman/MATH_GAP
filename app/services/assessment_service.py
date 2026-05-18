from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment import Assessment, TopicScore
from app.schemas.assessment import AssessmentCreate, AssessmentRead


class AssessmentService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_assessment(self, payload: AssessmentCreate) -> AssessmentRead:
        assessment = Assessment(
            student_id=payload.student_id,
            grade_level=payload.grade_level,
            overall_score=payload.overall_score,
            topic_scores=[
                TopicScore(topic=item.topic, score=item.score, confidence=item.confidence)
                for item in payload.topic_scores
            ],
        )
        self.db.add(assessment)
        await self.db.commit()
        await self.db.refresh(assessment)
        return AssessmentRead.model_validate(assessment)

