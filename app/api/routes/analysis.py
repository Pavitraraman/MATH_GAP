from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.exceptions import LLMProviderError
from app.schemas.analysis import StudentLLMAnalysis
from app.services.student_analysis_service import StudentAnalysisService

router = APIRouter()


@router.post("/learning-gap", response_model=StudentLLMAnalysis)
async def analyze_learning_gap(
    summary: dict,
    db: AsyncSession = Depends(get_db),
) -> StudentLLMAnalysis:
    try:
        return await StudentAnalysisService(db).analyze_summary(summary)
    except LLMProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
