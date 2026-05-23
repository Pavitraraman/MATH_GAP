from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.exceptions import LLMProviderError
from app.schemas.recommendation import RecommendationRead, AdaptiveRecommendationResponse
from app.services.recommendation_service import RecommendationService

router = APIRouter()


@router.post("/{assessment_id}", response_model=RecommendationRead)
async def create_recommendation(
    assessment_id: int,
    db: AsyncSession = Depends(get_db),
) -> RecommendationRead:
    try:
        result = await RecommendationService(db).generate_for_assessment(assessment_id)
    except LLMProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment not found",
        )
    return result


@router.get("/{student_id}", response_model=AdaptiveRecommendationResponse)
async def get_student_recommendations(
    student_id: str,
    weak_threshold: float = 0.7,
    min_attempts: int = 3,
    db: AsyncSession = Depends(get_db),
) -> AdaptiveRecommendationResponse:
    try:
        service = RecommendationService(db)
        return await service.get_adaptive_recommendations(
            student_id=student_id,
            weak_threshold=weak_threshold,
            min_attempts=min_attempts,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while generating recommendations: {exc}",
        ) from exc

