from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment import Assessment
from app.models.recommendation import Recommendation
from app.schemas.recommendation import RecommendationPlan, RecommendationRead, StudyActivity, WeakTopic
from app.services.llm_service import LLMService
from app.services.prompt_service import PromptService
from recommendation_engine.weak_topics import detect_weak_topics


class RecommendationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def generate_for_assessment(self, assessment_id: int) -> RecommendationRead | None:
        assessment = await self.db.scalar(
            select(Assessment).where(Assessment.id == assessment_id)
        )
        if assessment is None:
            return None

        weak_topics = detect_weak_topics(assessment.topic_scores)
        prompt = await PromptService(self.db).get_active_prompt()
        rendered_prompt = prompt.template.format(
            grade_level=assessment.grade_level,
            overall_score=assessment.overall_score,
            weak_topics=[item.model_dump() for item in weak_topics],
        )
        plan = await LLMService(self.db).generate_plan(
            prompt=prompt,
            rendered_prompt=rendered_prompt,
            fallback_plan=self._build_fallback_plan(weak_topics),
        )

        recommendation = Recommendation(
            assessment_id=assessment.id,
            student_id=assessment.student_id,
            weak_topics_json=[item.model_dump() for item in weak_topics],
            plan_json=plan.model_dump(),
        )
        self.db.add(recommendation)
        await self.db.commit()
        await self.db.refresh(recommendation)

        return RecommendationRead(
            id=recommendation.id,
            assessment_id=recommendation.assessment_id,
            student_id=recommendation.student_id,
            weak_topics=[WeakTopic.model_validate(item) for item in recommendation.weak_topics_json],
            plan=plan,
            created_at=recommendation.created_at,
        )

    @staticmethod
    def _build_fallback_plan(weak_topics: list[WeakTopic]) -> RecommendationPlan:
        return RecommendationPlan(
            summary="Rule-based fallback plan generated because Gemini is not configured.",
            weak_topics=weak_topics,
            activities=[
                StudyActivity(
                    topic=item.topic,
                    action=f"Review fundamentals and complete targeted practice for {item.topic}.",
                    difficulty="foundational" if item.severity == "high" else "intermediate",
                    estimated_minutes=30 if item.severity == "high" else 20,
                )
                for item in weak_topics
            ],
            next_assessment_focus=[item.topic for item in weak_topics],
        )
