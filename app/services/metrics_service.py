from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment import Assessment
from app.models.llm import LLMCallLog
from app.models.recommendation import Recommendation
from app.schemas.metrics import DashboardMetrics, LLMCallLogRead


class MetricsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def dashboard(self) -> DashboardMetrics:
        total_assessments = await self.db.scalar(select(func.count(Assessment.id))) or 0
        total_recommendations = await self.db.scalar(select(func.count(Recommendation.id))) or 0
        average_overall_score = await self.db.scalar(select(func.avg(Assessment.overall_score))) or 0.0
        average_llm_latency_ms = await self.db.scalar(select(func.avg(LLMCallLog.latency_ms))) or 0.0
        total_estimated_llm_cost_usd = await self.db.scalar(
            select(func.sum(LLMCallLog.estimated_cost_usd))
        ) or 0.0
        coverage = (total_recommendations / total_assessments) if total_assessments else 0.0
        return DashboardMetrics(
            total_assessments=total_assessments,
            total_recommendations=total_recommendations,
            average_overall_score=round(float(average_overall_score), 2),
            average_llm_latency_ms=round(float(average_llm_latency_ms), 2),
            total_estimated_llm_cost_usd=round(float(total_estimated_llm_cost_usd), 6),
            recommendation_coverage_rate=round(coverage, 4),
        )

    async def recent_llm_logs(self, limit: int = 20) -> list[LLMCallLogRead]:
        result = await self.db.scalars(
            select(LLMCallLog).order_by(LLMCallLog.created_at.desc()).limit(limit)
        )
        return [LLMCallLogRead.model_validate(item) for item in result.all()]
