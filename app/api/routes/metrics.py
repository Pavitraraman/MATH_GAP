from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schemas.metrics import DashboardMetrics, LLMCallLogRead
from app.services.metrics_service import MetricsService

router = APIRouter()


@router.get("/dashboard", response_model=DashboardMetrics)
async def dashboard(db: AsyncSession = Depends(get_db)) -> DashboardMetrics:
    return await MetricsService(db).dashboard()


@router.get("/llm-logs", response_model=list[LLMCallLogRead])
async def llm_logs(
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
) -> list[LLMCallLogRead]:
    return await MetricsService(db).recent_llm_logs(limit=limit)
